"""
Backtracking Search for Multi-Robot Coordination
==================================================
Two classical backtracking searches that let the system revisit decisions
instead of committing to the first greedy choice.

1. Task Allocation as a CSP (Depth-First Branch & Bound)
   Variables:   the top-K pending tasks (K = min(#tasks, #robots))
   Domains:     available robots, plus SKIP (leave the task for next cycle)
   Constraints: each robot takes at most one task; forbidden (robot, task)
                pairs (agent nogoods) are excluded
   Objective:   minimise  Σ cost(robot, task) + Σ SKIP_PENALTY × priority
   Pruning:     lower bound = cost so far + Σ min remaining cost per task.
                If bound ≥ best complete solution, backtrack.

2. Priority-Order Backtracking for Cooperative A*
   Prioritised planning fails when an early robot's reservations wall off a
   later robot. Instead of marking the later robot BLOCKED, we search over
   planning orders:
     - plan robots one at a time, reserving each path
     - if robot r cannot be planned, the current prefix is a dead end
       (reservations only ever add constraints, so r would fail in every
       extension of the prefix too)
     - backtrack: undo the last reservation and try r earlier
   Robots whose goal is spatially unreachable (plain A*), or that fail with an
   empty prefix, are unsolvable by any ordering and are excluded up front.

Both searches are anytime: they respect a node / call budget and return the
best solution found so far.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from algorithms.astar import astar_search
from algorithms.cooperative_astar import (
    CAStarResult, ReservationTable, cooperative_astar
)
from algorithms.task_allocation import (
    AllocationResult, Task, estimate_task_cost
)

SKIP = None
SKIP_PENALTY = 1000.0
MAX_TRACE_NODES = 120


# ─────────────────────────────────────────────────────────────────────────────
# 1. Backtracking Task Allocation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class AllocationSearchReport:
    """Statistics and search-tree trace for one allocation search."""
    nodes_expanded: int = 0
    branches_pruned: int = 0
    backtracks: int = 0
    max_depth: int = 0
    solutions_found: int = 0
    optimal: bool = True          # False if the node budget was exhausted
    greedy_cost: float = 0.0
    best_cost: float = 0.0
    search_time_ms: float = 0.0
    assignment: Dict[str, Optional[str]] = field(default_factory=dict)
    trace: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "nodes_expanded": self.nodes_expanded,
            "branches_pruned": self.branches_pruned,
            "backtracks": self.backtracks,
            "max_depth": self.max_depth,
            "solutions_found": self.solutions_found,
            "optimal": self.optimal,
            "greedy_cost": round(self.greedy_cost, 1),
            "best_cost": round(self.best_cost, 1),
            "cost_saved": round(max(0.0, self.greedy_cost - self.best_cost), 1),
            "search_time_ms": round(self.search_time_ms, 2),
            "assignment": self.assignment,
            "trace": self.trace,
        }


def _greedy_cost(
    task_ids: List[str],
    robots: List[str],
    costs: Dict[Tuple[str, str], float],
    priorities: Dict[str, int],
) -> float:
    """Cost of the greedy allocation, for comparison with the search result."""
    remaining = set(robots)
    total = 0.0
    for tid in task_ids:
        options = [(costs[(r, tid)], r) for r in remaining if (r, tid) in costs]
        if options:
            c, r = min(options)
            total += c
            remaining.discard(r)
        else:
            total += SKIP_PENALTY * priorities[tid]
    return total


def backtracking_allocate(
    tasks: List[Task],
    robot_positions: Dict[str, Tuple[int, int]],
    available_robots: Set[str],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
    forbidden_pairs: Optional[Set[Tuple[str, str]]] = None,
    max_nodes: int = 20000,
) -> Tuple[List[AllocationResult], AllocationSearchReport]:
    """
    Optimal task allocation via depth-first branch & bound.

    Mutates assigned tasks exactly like allocate_tasks() so it is a drop-in
    replacement inside the simulation engine.
    """
    t0 = time.perf_counter()
    report = AllocationSearchReport()
    forbidden_pairs = forbidden_pairs or set()

    pending = [
        t for t in tasks
        if t.status == "PENDING" and t.assigned_robot is None
    ]
    pending.sort(key=lambda t: (-t.priority, t.creation_time))
    robots = sorted(r for r in available_robots if r in robot_positions)
    if not pending or not robots:
        return [], report

    selected = pending[:len(robots)]
    task_ids = [t.task_id for t in selected]
    task_by_id = {t.task_id: t for t in selected}
    priorities = {t.task_id: t.priority for t in selected}

    # Pre-compute the cost matrix (the expensive part: A* per pair)
    costs: Dict[Tuple[str, str], float] = {}
    breakdowns: Dict[Tuple[str, str], Dict[str, float]] = {}
    for tid in task_ids:
        task = task_by_id[tid]
        for rid in robots:
            if (rid, tid) in forbidden_pairs:
                continue
            cost, breakdown = estimate_task_cost(
                robot_positions[rid], task.pickup_location,
                task.delivery_station, grid_width, grid_height, obstacles,
            )
            costs[(rid, tid)] = cost
            breakdowns[(rid, tid)] = breakdown

    # Value ordering: cheapest robot first, SKIP last
    domains: Dict[str, List[Optional[str]]] = {
        tid: sorted(
            (r for r in robots if (r, tid) in costs),
            key=lambda r, tid=tid: costs[(r, tid)],
        ) + [SKIP]
        for tid in task_ids
    }

    report.greedy_cost = _greedy_cost(task_ids, robots, costs, priorities)
    best_cost = float("inf")
    best_assignment: Dict[str, Optional[str]] = {}
    assignment: Dict[str, Optional[str]] = {}
    used: Set[str] = set()
    budget_exhausted = False

    def lower_bound(depth: int, cost_so_far: float) -> float:
        """Admissible bound: each remaining task takes its cheapest free option."""
        bound = cost_so_far
        for tid in task_ids[depth:]:
            options = [costs[(r, tid)] for r in robots
                       if r not in used and (r, tid) in costs]
            options.append(SKIP_PENALTY * priorities[tid])
            bound += min(options)
        return bound

    def trace(parent: Optional[int], depth: int, tid: str,
              robot: Optional[str], cost: float, status: str) -> Optional[int]:
        if len(report.trace) >= MAX_TRACE_NODES:
            return None
        node_id = len(report.trace)
        report.trace.append({
            "id": node_id, "parent": parent, "depth": depth,
            "task_id": tid, "robot_id": robot,
            "cost": round(cost, 1), "status": status,
        })
        return node_id

    def search(depth: int, cost_so_far: float, parent: Optional[int]):
        nonlocal best_cost, best_assignment, budget_exhausted
        # The budget only applies once a complete solution exists, so the
        # search is anytime: the first (greedy-like) descent always finishes.
        if report.nodes_expanded >= max_nodes and best_cost < float("inf"):
            budget_exhausted = True
            return
        report.max_depth = max(report.max_depth, depth)

        if depth == len(task_ids):
            report.solutions_found += 1
            if cost_so_far < best_cost:
                best_cost = cost_so_far
                best_assignment = dict(assignment)
                if parent is not None and parent < len(report.trace):
                    report.trace[parent]["status"] = "best"
            return

        tid = task_ids[depth]
        for robot in domains[tid]:
            if robot is not SKIP and robot in used:
                continue
            step_cost = (SKIP_PENALTY * priorities[tid] if robot is SKIP
                         else costs[(robot, tid)])
            new_cost = cost_so_far + step_cost

            # Bound check before descending
            if robot is not SKIP:
                used.add(robot)
            bound = lower_bound(depth + 1, new_cost)
            if bound >= best_cost:
                report.branches_pruned += 1
                trace(parent, depth + 1, tid, robot, new_cost, "pruned")
                if robot is not SKIP:
                    used.discard(robot)
                continue

            report.nodes_expanded += 1
            node = trace(parent, depth + 1, tid, robot, new_cost, "expanded")
            assignment[tid] = robot
            search(depth + 1, new_cost, node)
            # ── Backtrack: undo this choice and try the next value ──
            del assignment[tid]
            if robot is not SKIP:
                used.discard(robot)
            report.backtracks += 1
            if budget_exhausted:
                return

    search(0, 0.0, None)

    report.optimal = not budget_exhausted
    report.best_cost = best_cost if best_cost < float("inf") else 0.0
    report.assignment = best_assignment

    allocations: List[AllocationResult] = []
    for tid in task_ids:
        robot = best_assignment.get(tid)
        if robot is SKIP:
            continue
        task = task_by_id[tid]
        cost = costs[(robot, tid)]
        breakdown = breakdowns[(robot, tid)]
        task.assigned_robot = robot
        task.status = "ASSIGNED"
        task.estimated_cost = cost
        allocations.append(AllocationResult(
            task_id=tid,
            robot_id=robot,
            package_location=task.pickup_location,
            delivery_station=task.delivery_station,
            estimated_cost=cost,
            cost_breakdown=breakdown,
            allocation_time_ms=(time.perf_counter() - t0) * 1000,
            reason=(
                f"Robot {robot} selected by branch & bound "
                f"({'optimal' if report.optimal else 'best found'} joint cost "
                f"{report.best_cost:.1f} vs greedy {report.greedy_cost:.1f})"
            ),
        ))

    report.search_time_ms = (time.perf_counter() - t0) * 1000
    return allocations, report


# ─────────────────────────────────────────────────────────────────────────────
# 2. Priority-Order Backtracking for Cooperative A*
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class OrderingSearchReport:
    """Statistics for one priority-ordering search."""
    ca_calls: int = 0
    backtracks: int = 0
    orderings_tried: int = 0
    resolved_by_backtracking: bool = False
    final_order: List[str] = field(default_factory=list)
    unsolvable: List[str] = field(default_factory=list)
    budget_exhausted: bool = False
    search_time_ms: float = 0.0

    def to_dict(self) -> Dict:
        return {
            "ca_calls": self.ca_calls,
            "backtracks": self.backtracks,
            "orderings_tried": self.orderings_tried,
            "resolved_by_backtracking": self.resolved_by_backtracking,
            "final_order": self.final_order,
            "unsolvable": self.unsolvable,
            "budget_exhausted": self.budget_exhausted,
            "search_time_ms": round(self.search_time_ms, 2),
        }


def _reserve_stationary(table: ReservationTable, robot_id: str,
                        pos: Tuple[int, int], current_time: int):
    """Reserve a failed robot's current cell so others route around it."""
    table.reserve_path(
        [(pos[0], pos[1], t) for t in range(current_time, current_time + 5)],
        robot_id,
    )


def plan_with_order_backtracking(
    robot_plans: List[Dict],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
    reservation_table: ReservationTable,
    current_time: int = 0,
    max_ca_calls: int = 30,
    max_time_ms: float = 250.0,
) -> Tuple[List[CAStarResult], OrderingSearchReport]:
    """
    Plan all robots cooperatively, backtracking over the priority order when
    a robot cannot find a collision-free path.

    Each plan dict has: robot_id, start, goal, and optionally `avoid` — a set
    of extra cells this robot must not enter (used for alternative routes).
    """
    t0 = time.perf_counter()
    report = OrderingSearchReport()
    plans = {p["robot_id"]: p for p in robot_plans}
    input_order = [p["robot_id"] for p in robot_plans]

    def start_of(rid: str) -> Tuple[int, int]:
        return tuple(plans[rid]["start"])

    def out_of_budget() -> bool:
        if (report.ca_calls >= max_ca_calls or
                (time.perf_counter() - t0) * 1000 >= max_time_ms):
            report.budget_exhausted = True
        return report.budget_exhausted

    def plan_one(rid: str) -> CAStarResult:
        report.ca_calls += 1
        p = plans[rid]
        return cooperative_astar(
            robot_id=rid,
            start=start_of(rid),
            goal=tuple(p["goal"]),
            start_time=current_time,
            grid_width=grid_width,
            grid_height=grid_height,
            obstacles=obstacles | set(p.get("avoid", ())),
            reservation_table=reservation_table,
        )

    def clear_all():
        for rid in input_order:
            reservation_table.clear_robot_reservations(rid)

    clear_all()
    results: Dict[str, CAStarResult] = {}

    # Cheap static check: a failing CA* search exhausts its whole time
    # horizon, so skip it for goals plain A* already proves unreachable.
    for rid in input_order:
        p = plans[rid]
        static = astar_search(start_of(rid), tuple(p["goal"]), grid_width,
                              grid_height, obstacles | set(p.get("avoid", ())))
        if not static.success:
            report.unsolvable.append(rid)
            results[rid] = CAStarResult(
                robot_id=rid, path=[], time_path=[], path_length=0,
                nodes_explored=static.nodes_explored, planning_time_ms=0.0,
                wait_steps=0, success=False,
                message="Goal unreachable: no path exists even ignoring other robots",
            )
            _reserve_stationary(reservation_table, rid, start_of(rid), current_time)

    # Fast path: the classic fixed order. Most steps succeed here.
    for rid in input_order:
        if rid in report.unsolvable:
            continue
        res = plan_one(rid)
        results[rid] = res
        if res.success:
            reservation_table.reserve_path(res.time_path, rid)
        else:
            _reserve_stationary(reservation_table, rid, start_of(rid), current_time)

    report.orderings_tried = 1
    if all(results[r].success for r in input_order if r not in report.unsolvable):
        report.final_order = [r for r in input_order if r not in report.unsolvable]
        report.search_time_ms = (time.perf_counter() - t0) * 1000
        return [results[rid] for rid in input_order], report

    # Robots that fail even with no other planned robot reserved cannot be
    # helped by any ordering: exclude them and keep them reserved in place.
    clear_all()
    searchable: List[str] = []
    for rid in input_order:
        if rid in report.unsolvable:
            continue
        if results[rid].success:
            searchable.append(rid)
            continue
        alone = plan_one(rid)
        if alone.success:
            searchable.append(rid)
        else:
            results[rid] = alone
            report.unsolvable.append(rid)
    for rid in report.unsolvable:
        _reserve_stationary(reservation_table, rid, start_of(rid), current_time)

    fixable_failure = any(not results[r].success for r in searchable)
    if not fixable_failure:
        # Only unsolvable robots failed: keep the fixed order, no search needed
        for rid in searchable:
            res = plan_one(rid)
            results[rid] = res
            if res.success:
                reservation_table.reserve_path(res.time_path, rid)
            else:
                _reserve_stationary(reservation_table, rid, start_of(rid), current_time)
        report.final_order = [r for r in searchable if results[r].success]
        report.search_time_ms = (time.perf_counter() - t0) * 1000
        return [results[rid] for rid in input_order], report

    # Depth-first search over orderings with conflict-directed reordering
    best_prefix: List[Tuple[str, CAStarResult]] = []
    prefix: List[Tuple[str, CAStarResult]] = []
    promoted: List[str] = [r for r in searchable if not results[r].success]

    def next_candidate(remaining: List[str], tried: Set[str]) -> Optional[str]:
        for rid in promoted + remaining:
            if rid in remaining and rid not in tried:
                return rid
        return None

    def search(remaining: List[str]) -> bool:
        nonlocal best_prefix
        if not remaining:
            return True
        tried: Set[str] = set()
        while True:
            rid = next_candidate(remaining, tried)
            if rid is None or out_of_budget():
                return False
            tried.add(rid)
            res = plan_one(rid)
            if not res.success:
                # Monotonicity: rid fails under this prefix and every
                # extension of it, so the whole subtree is dead. Promote rid
                # so the parent level tries it earlier.
                if rid in promoted:
                    promoted.remove(rid)
                promoted.insert(0, rid)
                return False
            reservation_table.reserve_path(res.time_path, rid)
            prefix.append((rid, res))
            if len(prefix) > len(best_prefix):
                best_prefix = list(prefix)
            if search([r for r in remaining if r != rid]):
                return True
            # ── Backtrack: release this robot's reservations ──
            prefix.pop()
            reservation_table.clear_robot_reservations(rid)
            report.backtracks += 1
            report.orderings_tried += 1

    solved = search(list(searchable))
    chosen = prefix if solved else best_prefix

    # Rebuild the reservation table to reflect exactly the chosen plans
    clear_all()
    for rid in report.unsolvable:
        _reserve_stationary(reservation_table, rid, start_of(rid), current_time)
    chosen_ids = set()
    for rid, res in chosen:
        reservation_table.reserve_path(res.time_path, rid)
        results[rid] = res
        chosen_ids.add(rid)
    for rid in searchable:
        if rid in chosen_ids:
            continue
        results[rid] = CAStarResult(
            robot_id=rid, path=[], time_path=[], path_length=0,
            nodes_explored=results[rid].nodes_explored,
            planning_time_ms=0.0, wait_steps=0, success=False,
            message="No conflict-free planning order found within search budget",
        )
        _reserve_stationary(reservation_table, rid, start_of(rid), current_time)

    report.final_order = [rid for rid, _ in chosen]
    report.resolved_by_backtracking = solved
    report.search_time_ms = (time.perf_counter() - t0) * 1000
    return [results[rid] for rid in input_order], report
