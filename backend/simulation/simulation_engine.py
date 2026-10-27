"""
Main Simulation Engine
========================
Orchestrates all classical AI components to run the warehouse simulation.

Each simulation step follows this sequence:
  1. Process pending environment changes (new obstacles, packages, etc.)
  2. Evaluate applicable robot rules (rule-based reasoning)
  3. Allocate tasks to available robots (backtracking branch & bound)
  4. Plan or replan routes (Cooperative A* with priority-order backtracking)
  5. Validate all planned movements against shared constraints
  6. Execute robot movements simultaneously
  7. Update package states
  8. Update robot states
  8b. Agent monitoring: detect stuck robots / wait-for deadlocks and
      backtrack to the most recent choice point (route → task)
  9. Update statistics
  10. Broadcast the resulting state to the frontend (via callback)
"""

import asyncio
import copy
import time
import uuid
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from agents.robot import Robot, RobotState, create_robot
from algorithms.astar import astar_search, AStarResult
from algorithms.cooperative_astar import (
    ReservationTable, cooperative_astar
)
from algorithms.backtracking import (
    backtracking_allocate, plan_with_order_backtracking
)
from algorithms.rule_engine import RuleEngine, get_rule_engine
from algorithms.task_allocation import Task
from simulation.warehouse import Warehouse, Package, create_default_warehouse


class Statistics:
    """Tracks real simulation statistics."""
    
    def __init__(self):
        self.total_distance: int = 0
        self.completed_deliveries: int = 0
        self.total_planning_time_ms: float = 0.0
        self.conflicts_detected: int = 0
        self.conflicts_resolved: int = 0
        self.total_waiting_steps: int = 0
        self.nodes_explored: int = 0
        self.replan_count: int = 0
        self.delivery_step_totals: List[int] = []
        self.simulation_step: int = 0
        # Backtracking search
        self.search_nodes: int = 0
        self.branches_pruned: int = 0
        self.search_backtracks: int = 0
        self.allocation_cost_saved: float = 0.0
        self.ordering_resolutions: int = 0
        self.agent_backtracks: int = 0
        self.deadlocks_resolved: int = 0
    
    @property
    def pending_deliveries(self) -> int:
        return 0  # Set dynamically from task list
    
    @property
    def average_delivery_steps(self) -> float:
        if not self.delivery_step_totals:
            return 0.0
        return sum(self.delivery_step_totals) / len(self.delivery_step_totals)
    
    def to_dict(self) -> Dict:
        return {
            "total_distance": self.total_distance,
            "completed_deliveries": self.completed_deliveries,
            "pending_deliveries": 0,
            "total_planning_time_ms": round(self.total_planning_time_ms, 2),
            "conflicts_detected": self.conflicts_detected,
            "conflicts_resolved": self.conflicts_resolved,
            "average_delivery_steps": round(self.average_delivery_steps, 1),
            "total_waiting_steps": self.total_waiting_steps,
            "nodes_explored": self.nodes_explored,
            "replan_count": self.replan_count,
            "simulation_step": self.simulation_step,
            "search_nodes": self.search_nodes,
            "branches_pruned": self.branches_pruned,
            "search_backtracks": self.search_backtracks,
            "allocation_cost_saved": round(self.allocation_cost_saved, 1),
            "ordering_resolutions": self.ordering_resolutions,
            "agent_backtracks": self.agent_backtracks,
            "deadlocks_resolved": self.deadlocks_resolved,
        }


class EventLog:
    """Real-time event log with timestamped entries."""
    
    MAX_ENTRIES = 500
    
    def __init__(self):
        self.entries: List[Dict] = []
    
    def log(self, event_type: str, message: str,
            robot_id: str = None, package_id: str = None,
            rule_id: str = None, step: int = 0):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = {
            "timestamp": ts,
            "event_type": event_type,
            "message": message,
            "robot_id": robot_id,
            "package_id": package_id,
            "rule_id": rule_id,
            "step": step,
        }
        self.entries.append(entry)
        # Keep only the most recent entries
        if len(self.entries) > self.MAX_ENTRIES:
            self.entries = self.entries[-self.MAX_ENTRIES:]
    
    def recent(self, n: int = 50) -> List[Dict]:
        return self.entries[-n:]
    
    def clear(self):
        self.entries.clear()


# Agent backtracking parameters
STUCK_THRESHOLD = 5          # steps without progress before backtracking
MAX_ROUTE_ALTERNATIVES = 2   # alternative routes tried before dropping the task
NOGOOD_TTL = 30              # steps a (robot, task) pair stays forbidden
BACKTRACK_COOLDOWN = 3       # steps between two backtracks of the same robot
ACTIVE_STATES = (
    RobotState.MOVING_TO_PICKUP, RobotState.MOVING_TO_DELIVERY,
    RobotState.WAITING, RobotState.REPLANNING, RobotState.BLOCKED,
)


class SimulationEngine:
    """
    The main simulation orchestrator.
    
    Implements the 10-step discrete time simulation loop.
    All classical AI algorithms are invoked from here.
    """
    
    def __init__(self):
        self.warehouse: Warehouse = create_default_warehouse()
        self.robots: Dict[str, Robot] = {}
        self.tasks: Dict[str, Task] = {}
        self.statistics: Statistics = Statistics()
        self.event_log: EventLog = EventLog()
        self.reservation_table: ReservationTable = ReservationTable()
        self.rule_engine: RuleEngine = get_rule_engine()
        
        self.is_running: bool = False
        self.speed: float = 1.0  # Steps per second multiplier
        self.simulation_step: int = 0
        self.active_algorithm: str = "Cooperative A* + Backtracking"
        
        self._broadcast_callback: Optional[Callable] = None
        self._step_task: Optional[asyncio.Task] = None
        self._package_counter: int = 11
        self._task_counter: int = 1
        self._robot_counter: int = 6
        
        # Track tasks that were active at the start of delivery for step counting
        self._task_start_steps: Dict[str, int] = {}
        
        # Backtracking state: (robot_id, task_id) → step until which forbidden
        self.nogoods: Dict[Tuple[str, str], int] = {}
        # Tasks no robot can currently reach: task_id → step until deferred
        self.deferred_tasks: Dict[str, int] = {}
        self.last_allocation_search: Optional[Dict] = None
        self.last_ordering_search: Optional[Dict] = None
        
        # Initialize default robots
        self._initialize_default_robots()
        
        self.event_log.log(
            "SYSTEM", "Warehouse Management System initialized.",
            step=0
        )
    
    def _initialize_default_robots(self):
        """Create 5 default robots at spawn positions."""
        spawn_positions = [(1, 1), (1, 3), (18, 1), (18, 3), (9, 1)]
        robot_ids = ["R1", "R2", "R3", "R4", "R5"]
        
        for i, (robot_id, pos) in enumerate(zip(robot_ids, spawn_positions)):
            if self.warehouse.is_traversable(pos):
                robot = create_robot(robot_id, pos, i)
                self.robots[robot_id] = robot
    
    # ──────────────────────────────────────────────────────────────────────
    # SIMULATION CONTROL
    # ──────────────────────────────────────────────────────────────────────
    
    async def start(self):
        """Start or resume the simulation loop."""
        if self.is_running:
            return
        self.is_running = True
        self.event_log.log("SYSTEM", "Simulation started.", step=self.simulation_step)
        self._step_task = asyncio.create_task(self._run_loop())
    
    async def pause(self):
        """Pause the simulation without losing state."""
        self.is_running = False
        if self._step_task:
            self._step_task.cancel()
            self._step_task = None
        self.event_log.log("SYSTEM", "Simulation paused.", step=self.simulation_step)
    
    async def reset(self, scenario_id: Optional[str] = None):
        """Reset to initial state."""
        was_running = self.is_running
        await self.pause()
        
        self.warehouse = create_default_warehouse()
        self.robots.clear()
        self.tasks.clear()
        self.statistics = Statistics()
        self.reservation_table = ReservationTable()
        self.simulation_step = 0
        self._package_counter = 11
        self._task_counter = 1
        self._robot_counter = 6
        self._task_start_steps.clear()
        self.nogoods.clear()
        self.deferred_tasks.clear()
        self.last_allocation_search = None
        self.last_ordering_search = None
        self.event_log.clear()
        
        self._initialize_default_robots()
        
        self.event_log.log("SYSTEM", "Simulation reset to initial state.", step=0)
        await self._broadcast_state()
    
    async def step_once(self):
        """Advance exactly one simulation step."""
        await self._execute_step()
        await self._broadcast_state()
    
    def set_speed(self, speed: float):
        """Set simulation playback speed (0.5x, 1x, 2x, 4x)."""
        valid_speeds = {0.5, 1.0, 2.0, 4.0}
        if speed not in valid_speeds:
            speed = 1.0
        self.speed = speed
    
    def set_broadcast_callback(self, callback: Callable):
        """Register the WebSocket broadcast function."""
        self._broadcast_callback = callback
    
    # ──────────────────────────────────────────────────────────────────────
    # MAIN SIMULATION LOOP
    # ──────────────────────────────────────────────────────────────────────
    
    async def _run_loop(self):
        """Continuous simulation loop."""
        try:
            while self.is_running:
                step_start = time.perf_counter()
                await self._execute_step()
                await self._broadcast_state()
                
                # Calculate sleep time based on speed
                step_duration = 1.0 / self.speed  # seconds per step
                elapsed = time.perf_counter() - step_start
                sleep_time = max(0, step_duration - elapsed)
                await asyncio.sleep(sleep_time)
        except asyncio.CancelledError:
            pass
    
    async def _execute_step(self):
        """
        Execute one complete simulation step.
        Follows the 10-step discrete simulation protocol.
        """
        self.simulation_step += 1
        self.statistics.simulation_step = self.simulation_step
        step = self.simulation_step
        
        # ── STEP 1: Environment changes already applied via API ──────────────
        # (add_obstacle, add_package, etc. are immediate)
        
        # ── STEP 2: Rule engine evaluates each robot ─────────────────────────
        pending_tasks_exist = any(
            t.status == "PENDING" for t in self.tasks.values()
        )
        
        robot_rule_actions: Dict[str, Dict] = {}
        
        for robot_id, robot in self.robots.items():
            # Check if next cell in path would be blocked
            next_pos = robot.get_next_position()
            next_blocked = False
            blocking_robot = None
            if next_pos:
                for other_id, other in self.robots.items():
                    if other_id != robot_id and other.position == next_pos:
                        next_blocked = True
                        blocking_robot = other_id
                        break
            
            # Check if current path passes through new obstacle
            obstacles = self.warehouse.get_all_obstacles()
            obstacle_in_path = any(pos in obstacles for pos in robot.path)
            obstacle_pos = next(
                (pos for pos in robot.path if pos in obstacles), None
            )
            
            # Check package availability
            pkg_available = False
            if robot.package_id and robot.pickup_target:
                pkg = self.warehouse.get_package(robot.package_id)
                if pkg and pkg.status in ("WAITING", "ASSIGNED"):
                    pkg_available = True
            
            state_dict = robot.build_rule_state(
                pending_tasks_exist=pending_tasks_exist,
                package_available=pkg_available,
                next_cell_blocked=next_blocked,
                blocking_robot=blocking_robot,
                obstacle_in_path=obstacle_in_path,
                obstacle_position=obstacle_pos,
            )
            
            rule, action = self.rule_engine.evaluate(state_dict)
            if rule:
                robot_rule_actions[robot_id] = {
                    "rule": rule,
                    "action": action,
                }
        
        # ── STEP 3: Task allocation ───────────────────────────────────────────
        available_robots = {
            rid for rid, r in self.robots.items()
            if r.state == RobotState.IDLE
        }
        robot_positions = {rid: r.position for rid, r in self.robots.items()}
        
        if available_robots and pending_tasks_exist:
            tasks_list = list(self.tasks.values())
            self.nogoods = {k: v for k, v in self.nogoods.items() if v > step}
            self.deferred_tasks = {k: v for k, v in self.deferred_tasks.items() if v > step}
            forbidden = set(self.nogoods) | {
                (rid, tid) for tid in self.deferred_tasks for rid in available_robots
            }
            allocations, search = backtracking_allocate(
                tasks_list,
                robot_positions,
                available_robots,
                self.warehouse.grid_width,
                self.warehouse.grid_height,
                self.warehouse.get_all_obstacles(),
                forbidden_pairs=forbidden,
            )
            self._record_allocation_search(search, step)
            
            for alloc in allocations:
                robot = self.robots.get(alloc.robot_id)
                task = self.tasks.get(alloc.task_id)
                if robot and task:
                    robot.assign_task(
                        task.task_id,
                        task.package_id,
                        task.pickup_location,
                        task.delivery_station,
                    )
                    pkg = self.warehouse.get_package(task.package_id)
                    if pkg:
                        pkg.assigned_robot = alloc.robot_id
                    task.status = "ASSIGNED"
                    self._task_start_steps[task.task_id] = step
                    robot.push_choice("TASK", task_id=task.task_id)
                    
                    self.event_log.log(
                        "TASK_ASSIGNED",
                        f"Package {task.package_id} assigned to Robot {alloc.robot_id}. "
                        f"Estimated cost: {alloc.estimated_cost:.1f} steps.",
                        robot_id=alloc.robot_id,
                        package_id=task.package_id,
                        step=step,
                    )
        
        # ── STEP 4: Path planning / replanning ───────────────────────────────
        robots_needing_paths = []
        obstacles = self.warehouse.get_all_obstacles()
        
        for robot_id, robot in self.robots.items():
            action_info = robot_rule_actions.get(robot_id, {})
            action = action_info.get("action", {})
            action_type = action.get("type", "")
            
            if robot.state == RobotState.ASSIGNED and not robot.path:
                robots_needing_paths.append(robot_id)
            elif action_type in ("REPLAN", "EMERGENCY_REPLAN"):
                robot.force_state(RobotState.REPLANNING)
                robot.path = []
                robot.time_path = []
                self.statistics.replan_count += 1
                robots_needing_paths.append(robot_id)
                self.event_log.log(
                    "REPLAN",
                    f"Robot {robot_id} replanning route: {action.get('reason', '')}",
                    robot_id=robot_id, step=step,
                )
        
        # Plan paths using Cooperative A*
        if robots_needing_paths:
            plan_inputs = []
            for robot_id in robots_needing_paths:
                robot = self.robots[robot_id]
                target = robot.pickup_target if not robot.has_package else robot.delivery_target
                if target:
                    plan_inputs.append({
                        "robot_id": robot_id,
                        "start": robot.position,
                        "goal": target,
                        "avoid": robot.avoid_cells - {target},
                    })
            
            if plan_inputs:
                t_plan_start = time.perf_counter()
                results, ordering = plan_with_order_backtracking(
                    plan_inputs,
                    self.warehouse.grid_width,
                    self.warehouse.grid_height,
                    obstacles,
                    self.reservation_table,
                    self.simulation_step,
                )
                plan_time = (time.perf_counter() - t_plan_start) * 1000
                self.statistics.total_planning_time_ms += plan_time
                self._record_ordering_search(ordering, step)
                
                for result in results:
                    robot = self.robots.get(result.robot_id)
                    if not robot:
                        continue
                    
                    self.statistics.nodes_explored += result.nodes_explored
                    
                    if result.success:
                        robot.set_path(result.path, result.time_path)
                        top = robot.top_choice()
                        if top is None or top["level"] != "ROUTE":
                            robot.push_choice("ROUTE")
                        if robot.state == RobotState.ASSIGNED:
                            robot.transition_to(RobotState.MOVING_TO_PICKUP)
                        elif robot.state == RobotState.REPLANNING:
                            new_state = (RobotState.MOVING_TO_DELIVERY
                                         if robot.has_package
                                         else RobotState.MOVING_TO_PICKUP)
                            robot.force_state(new_state)
                        
                        self.event_log.log(
                            "PATH_PLANNED",
                            f"Cooperative A* planned path for {result.robot_id}: "
                            f"{result.path_length} steps, {result.wait_steps} waits, "
                            f"{result.nodes_explored} nodes explored.",
                            robot_id=result.robot_id, step=step,
                        )
                    else:
                        robot.force_state(RobotState.BLOCKED)
                        # A failed plan is still a route choice: the agent
                        # retries it before backtracking further to the task
                        top = robot.top_choice()
                        if top is None or top["level"] != "ROUTE":
                            robot.push_choice("ROUTE")
                        self.event_log.log(
                            "BLOCKED",
                            f"Robot {result.robot_id} has no valid path: {result.message}",
                            robot_id=result.robot_id, step=step,
                        )
        
        # ── STEP 5 & 6: Validate and execute movements ───────────────────────
        positions_before = {rid: r.position for rid, r in self.robots.items()}
        planned_moves: Dict[str, Tuple[int, int]] = {}
        
        # Collect all intended moves
        for robot_id, robot in self.robots.items():
            action_info = robot_rule_actions.get(robot_id, {})
            action = action_info.get("action", {})
            action_type = action.get("type", "")
            
            if action_type == "WAIT":
                robot.wait_steps += 1
                self.statistics.total_waiting_steps += 1
                self.event_log.log(
                    "WAIT",
                    f"Robot {robot_id} waiting: {action.get('reason', '')}",
                    robot_id=robot_id, step=step,
                )
                continue
            
            if robot.state in (RobotState.MOVING_TO_PICKUP, RobotState.MOVING_TO_DELIVERY):
                next_pos = robot.get_next_position()
                if next_pos and next_pos not in obstacles:
                    planned_moves[robot_id] = next_pos
        
        # Conflict detection: vertex collisions
        position_claims: Dict[Tuple[int, int], List[str]] = {}
        for robot_id, pos in planned_moves.items():
            position_claims.setdefault(pos, []).append(robot_id)
        
        # Resolve vertex conflicts: only allow one robot per cell
        allowed_moves: Set[str] = set()
        for pos, claimants in position_claims.items():
            if len(claimants) == 1:
                allowed_moves.add(claimants[0])
            else:
                # Conflict: let the first robot (by priority) move, others wait
                self.statistics.conflicts_detected += 1
                allowed_moves.add(claimants[0])
                for loser in claimants[1:]:
                    robot = self.robots[loser]
                    robot.wait_steps += 1
                    self.statistics.total_waiting_steps += 1
                    self.statistics.conflicts_resolved += 1
                    self.event_log.log(
                        "COLLISION_AVOIDED",
                        f"Vertex conflict at {pos}: Robot {loser} waits for {claimants[0]}",
                        robot_id=loser, step=step,
                    )
        
        # Edge-swap conflict detection
        current_positions = {rid: r.position for rid, r in self.robots.items()}
        swap_conflicts = set()
        
        robot_list = list(allowed_moves)
        for i, r1 in enumerate(robot_list):
            for r2 in robot_list[i+1:]:
                if (planned_moves.get(r1) == current_positions.get(r2) and
                        planned_moves.get(r2) == current_positions.get(r1)):
                    # Swap conflict detected
                    self.statistics.conflicts_detected += 1
                    self.statistics.conflicts_resolved += 1
                    swap_conflicts.add(r2)
                    self.event_log.log(
                        "SWAP_CONFLICT",
                        f"Edge-swap conflict between {r1} and {r2}: {r2} waits",
                        robot_id=r2, step=step,
                    )
        
        allowed_moves -= swap_conflicts
        
        # Execute moves
        for robot_id in allowed_moves:
            robot = self.robots[robot_id]
            if robot_id in planned_moves:
                robot.path.pop(0) if robot.path and robot.path[0] == planned_moves[robot_id] else None
                robot.position = planned_moves[robot_id]
                robot.distance_traveled += 1
                robot.total_steps += 1
                self.statistics.total_distance += 1
        
        # ── STEP 7 & 8: Update package and robot states ───────────────────────
        for robot_id, robot in self.robots.items():
            action_info = robot_rule_actions.get(robot_id, {})
            action = action_info.get("action", {})
            action_type = action.get("type", "")
            
            # PICKUP action
            if action_type == "PICKUP" or (
                robot.state == RobotState.MOVING_TO_PICKUP and
                robot.position == robot.pickup_target and
                not robot.has_package
            ):
                pkg = self.warehouse.get_package(robot.package_id)
                if pkg and pkg.status in ("WAITING", "ASSIGNED"):
                    pkg.status = "PICKED_UP"
                    pkg.assigned_robot = robot_id
                    robot.has_package = True
                    robot.path = []
                    robot.time_path = []
                    robot.commit_task()
                    task = self.tasks.get(robot.task_id)
                    if task:
                        task.status = "IN_PROGRESS"
                    robot.transition_to(RobotState.MOVING_TO_DELIVERY)
                    self.event_log.log(
                        "PICKUP",
                        f"Robot {robot_id} picked up Package {robot.package_id} at {robot.position}",
                        robot_id=robot_id,
                        package_id=robot.package_id,
                        step=step,
                    )
            
            # DELIVER action
            elif (robot.has_package and robot.state == RobotState.MOVING_TO_DELIVERY and
                  robot.position == robot.delivery_target):
                pkg = self.warehouse.get_package(robot.package_id)
                if pkg:
                    pkg.status = "DELIVERED"
                pkg_id = robot.package_id
                task_id = robot.task_id
                robot.deliver_package()
                
                task = self.tasks.get(task_id)
                if task:
                    task.status = "COMPLETED"
                    task.completion_time = step
                    start = self._task_start_steps.get(task_id, step)
                    self.statistics.delivery_step_totals.append(step - start)
                
                self.statistics.completed_deliveries += 1
                self.event_log.log(
                    "DELIVERY",
                    f"Robot {robot_id} delivered Package {pkg_id} at {robot.position}. "
                    f"Total deliveries: {self.statistics.completed_deliveries}",
                    robot_id=robot_id,
                    package_id=pkg_id,
                    step=step,
                )
        
        # ── STEP 8b: Agent monitoring and backtracking ────────────────────────
        self._monitor_agents(robot_rule_actions, positions_before, step)
        
        # ── STEP 9: Update aggregate statistics ───────────────────────────────
        # (Already updated inline above)
    
    # ──────────────────────────────────────────────────────────────────────
    # BACKTRACKING: SEARCH REPORTS AND AGENT DELIBERATION
    # ──────────────────────────────────────────────────────────────────────
    
    def _record_allocation_search(self, search, step: int):
        """Fold one branch & bound allocation search into stats and logs."""
        report = search.to_dict()
        report["step"] = step
        self.last_allocation_search = report
        self.statistics.search_nodes += search.nodes_expanded
        self.statistics.branches_pruned += search.branches_pruned
        self.statistics.search_backtracks += search.backtracks
        if not search.assignment:
            return
        saved = report["cost_saved"]
        self.statistics.allocation_cost_saved += saved
        self.event_log.log(
            "ALLOCATION_SEARCH",
            f"Branch & bound allocation: {search.nodes_expanded} nodes, "
            f"{search.branches_pruned} pruned, {search.backtracks} backtracks. "
            f"Joint cost {report['best_cost']} vs greedy {report['greedy_cost']}"
            + (f" (saved {saved})." if saved > 0 else "."),
            step=step,
        )
    
    def _record_ordering_search(self, ordering, step: int):
        """Log priority-order backtracking when the fixed order failed."""
        if ordering.orderings_tried <= 1 and not ordering.unsolvable:
            return
        report = ordering.to_dict()
        report["step"] = step
        self.last_ordering_search = report
        self.statistics.search_backtracks += ordering.backtracks
        if ordering.resolved_by_backtracking:
            self.statistics.ordering_resolutions += 1
            self.event_log.log(
                "PRIORITY_BACKTRACK",
                f"Fixed planning order failed; backtracking found order "
                f"{' → '.join(ordering.final_order)} after {ordering.orderings_tried} "
                f"orderings ({ordering.ca_calls} CA* calls).",
                step=step,
            )
    
    def _monitor_agents(self, robot_rule_actions: Dict[str, Dict],
                        positions_before: Dict[str, Tuple[int, int]], step: int):
        """
        Agent self-monitoring. Each robot checks its own progress; when it is
        stuck (or part of a wait-for cycle) it backtracks to its most recent
        choice point instead of waiting forever.
        """
        for robot_id, robot in self.robots.items():
            moved = positions_before.get(robot_id) != robot.position
            if robot.state in ACTIVE_STATES and not moved:
                robot.stuck_steps += 1
            else:
                robot.stuck_steps = 0
        
        # Deadlock detection: cycles in the wait-for graph
        wait_for: Dict[str, str] = {}
        for robot_id, info in robot_rule_actions.items():
            action = info.get("action", {})
            if action.get("type") == "WAIT" and action.get("blocked_by"):
                wait_for[robot_id] = action["blocked_by"]
        
        handled: Set[str] = set()
        for start in wait_for:
            chain, node = [], start
            while node in wait_for and node not in chain:
                chain.append(node)
                node = wait_for[node]
            if node not in chain:
                continue
            cycle = chain[chain.index(node):]
            if handled & set(cycle):
                continue
            handled |= set(cycle)
            # The robot without a package (cheapest to back off) yields first
            victim = min(
                cycle,
                key=lambda rid: (self.robots[rid].has_package, rid),
            )
            self.statistics.deadlocks_resolved += 1
            self.event_log.log(
                "DEADLOCK_DETECTED",
                f"Wait-for cycle {' → '.join(cycle + [cycle[0]])}. "
                f"Robot {victim} backtracks to break it.",
                robot_id=victim, step=step,
            )
            self._agent_backtrack(self.robots[victim], step, force=True)
        
        for robot in list(self.robots.values()):
            if robot.robot_id in handled:
                continue
            if robot.state == RobotState.BLOCKED or robot.stuck_steps >= STUCK_THRESHOLD:
                self._agent_backtrack(robot, step)
    
    def _agent_backtrack(self, robot: Robot, step: int, force: bool = False):
        """
        Chronological backtracking over the robot's choice points:
          ROUTE → try an alternative route avoiding the blocked cell
          TASK  → abandon the task (nogood) or, if carrying, step aside
        """
        if not force and step < robot.backtrack_cooldown_until:
            return
        robot.backtrack_cooldown_until = step + BACKTRACK_COOLDOWN
        robot.stuck_steps = 0
        robot.backtrack_count += 1
        self.statistics.agent_backtracks += 1
        
        while True:
            choice = robot.top_choice()
            if choice is None:
                if robot.task_id is None and robot.state != RobotState.IDLE:
                    robot.clear_task()
                    robot.force_state(RobotState.IDLE)
                return
            
            if choice["level"] == "ROUTE":
                # Alternative routes cannot help if the goal is walled off
                if (choice["attempts"] < MAX_ROUTE_ALTERNATIVES
                        and self._target_reachable(robot)):
                    choice["attempts"] += 1
                    blocked_cell = robot.path[0] if robot.path else None
                    if blocked_cell:
                        robot.avoid_cells.add(blocked_cell)
                    self._request_replan(robot)
                    self.event_log.log(
                        "BACKTRACK",
                        f"Robot {robot.robot_id} backtracks to ROUTE choice: "
                        f"alternative route #{choice['attempts']}"
                        + (f" avoiding {blocked_cell}." if blocked_cell else "."),
                        robot_id=robot.robot_id, step=step,
                    )
                    return
                robot.pop_choice()
                robot.avoid_cells.clear()
                continue
            
            # TASK choice point
            if not robot.has_package:
                self._abandon_task(robot, step)
            else:
                self._yield_cell(robot, step)
            return
    
    def _target_reachable(self, robot: Robot) -> bool:
        """Static reachability of the robot's current goal, ignoring other robots."""
        target = robot.delivery_target if robot.has_package else robot.pickup_target
        if target is None:
            return False
        return astar_search(
            robot.position, target, self.warehouse.grid_width,
            self.warehouse.grid_height, self.warehouse.get_all_obstacles(),
        ).success
    
    def _request_replan(self, robot: Robot):
        robot.path = []
        robot.time_path = []
        self.reservation_table.clear_robot_reservations(robot.robot_id)
        robot.force_state(RobotState.REPLANNING)
        robot.replan_count += 1
        self.statistics.replan_count += 1
    
    def _abandon_task(self, robot: Robot, step: int):
        """Undo the task assignment and forbid this (robot, task) pair for a while."""
        task_id = robot.task_id
        task = self.tasks.get(task_id) if task_id else None
        unreachable = not self._target_reachable(robot)
        if task:
            task.status = "PENDING"
            task.assigned_robot = None
            if unreachable:
                # Nobody can reach it: defer the task for every robot
                self.deferred_tasks[task_id] = step + NOGOOD_TTL
            else:
                self.nogoods[(robot.robot_id, task_id)] = step + NOGOOD_TTL
            self._task_start_steps.pop(task_id, None)
        pkg = self.warehouse.get_package(robot.package_id) if robot.package_id else None
        if pkg and pkg.status in ("WAITING", "ASSIGNED"):
            pkg.status = "WAITING"
            pkg.assigned_robot = None
        self.reservation_table.clear_robot_reservations(robot.robot_id)
        robot.clear_task()
        robot.force_state(RobotState.IDLE)
        reason = ("pickup is unreachable, deferring it for all robots"
                  if unreachable else
                  "route alternatives exhausted, releasing it back to the pool")
        self.event_log.log(
            "BACKTRACK",
            f"Robot {robot.robot_id} backtracks to TASK choice for {task_id}: "
            f"{reason} (nogood for {NOGOOD_TTL} steps).",
            robot_id=robot.robot_id, step=step,
        )
    
    def _yield_cell(self, robot: Robot, step: int):
        """A committed (carrying) robot steps aside to let traffic clear."""
        occupied = {r.position for r in self.robots.values() if r is not robot}
        x, y = robot.position
        for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            cell = (x + dx, y + dy)
            if (self.warehouse.is_traversable(cell) and cell not in occupied
                    and cell not in robot.avoid_cells):
                top = robot.top_choice()
                if top and top["level"] == "ROUTE":
                    robot.pop_choice()
                self.reservation_table.clear_robot_reservations(robot.robot_id)
                robot.path = [cell]
                robot.time_path = []
                robot.force_state(RobotState.MOVING_TO_DELIVERY)
                self.event_log.log(
                    "BACKTRACK",
                    f"Robot {robot.robot_id} is committed to {robot.task_id}; "
                    f"stepping aside to {cell} before replanning.",
                    robot_id=robot.robot_id, step=step,
                )
                return
        self.event_log.log(
            "BACKTRACK",
            f"Robot {robot.robot_id} is committed to {robot.task_id} and boxed in; holding position.",
            robot_id=robot.robot_id, step=step,
        )
    
    # ──────────────────────────────────────────────────────────────────────
    # ENVIRONMENT MODIFICATION METHODS
    # ──────────────────────────────────────────────────────────────────────
    
    def add_robot(self, position: Tuple[int, int]) -> Optional[str]:
        """Add a new robot at a valid position."""
        if not self.warehouse.is_traversable(position):
            return None
        # Check no robot is already there
        for r in self.robots.values():
            if r.position == position:
                return None
        
        robot_id = f"R{self._robot_counter}"
        self._robot_counter += 1
        color_idx = len(self.robots)
        robot = create_robot(robot_id, position, color_idx)
        self.robots[robot_id] = robot
        
        self.event_log.log(
            "ROBOT_ADDED",
            f"Robot {robot_id} added at position {position}.",
            robot_id=robot_id, step=self.simulation_step,
        )
        return robot_id
    
    def remove_robot(self, robot_id: str) -> bool:
        """Remove a robot from the simulation."""
        robot = self.robots.get(robot_id)
        if not robot:
            return False
        
        # Free any assigned task
        if robot.task_id:
            task = self.tasks.get(robot.task_id)
            if task:
                task.status = "PENDING"
                task.assigned_robot = None
        
        self.reservation_table.clear_robot_reservations(robot_id)
        del self.robots[robot_id]
        self.event_log.log(
            "ROBOT_REMOVED",
            f"Robot {robot_id} removed from simulation.",
            robot_id=robot_id, step=self.simulation_step,
        )
        return True
    
    def add_package(self, pickup: Tuple[int, int], delivery: Tuple[int, int],
                    priority: int = 1) -> Optional[str]:
        """Add a new package and create a corresponding task."""
        if (not self.warehouse.is_traversable(pickup) or
                not self.warehouse.is_traversable(delivery)):
            return None
        
        pkg_id = f"P{self._package_counter}"
        self._package_counter += 1
        task_id = f"T{self._task_counter}"
        self._task_counter += 1
        
        pkg = Package(pkg_id, pickup, delivery, "WAITING")
        self.warehouse.packages[pkg_id] = pkg
        
        task = Task(
            task_id=task_id,
            package_id=pkg_id,
            pickup_location=pickup,
            delivery_station=delivery,
            priority=priority,
            creation_time=self.simulation_step,
        )
        self.tasks[task_id] = task
        
        self.event_log.log(
            "PACKAGE_ADDED",
            f"Package {pkg_id} added at {pickup} → {delivery}.",
            package_id=pkg_id, step=self.simulation_step,
        )
        return pkg_id
    
    def add_obstacle(self, position: Tuple[int, int]) -> bool:
        """Add a dynamic obstacle and trigger replanning for affected robots."""
        result = self.warehouse.add_obstacle(position)
        if result:
            self._trigger_replan_for_blocked_robots(position)
            self.event_log.log(
                "OBSTACLE_ADDED",
                f"Dynamic obstacle added at {position}. Affected robots replanning.",
                step=self.simulation_step,
            )
        return result
    
    def remove_obstacle(self, position: Tuple[int, int]) -> bool:
        """Remove a dynamic obstacle."""
        result = self.warehouse.remove_obstacle(position)
        if result:
            # The world changed: learned nogoods may no longer hold
            self.nogoods.clear()
            self.deferred_tasks.clear()
            self.event_log.log(
                "OBSTACLE_REMOVED",
                f"Obstacle at {position} removed.",
                step=self.simulation_step,
            )
        return result
    
    def _trigger_replan_for_blocked_robots(self, new_obstacle: Tuple[int, int]):
        """Force replanning for any robot whose path passes through the new obstacle."""
        for robot in self.robots.values():
            if new_obstacle in robot.path:
                robot.path = []
                robot.time_path = []
                if robot.state in (RobotState.MOVING_TO_PICKUP, RobotState.MOVING_TO_DELIVERY):
                    robot.force_state(RobotState.REPLANNING)
                    self.statistics.replan_count += 1
                    self.event_log.log(
                        "REPLAN_TRIGGERED",
                        f"Robot {robot.robot_id} path blocked by new obstacle at {new_obstacle}. "
                        f"Replanning required.",
                        robot_id=robot.robot_id,
                        step=self.simulation_step,
                    )
    
    def load_initial_tasks(self):
        """Create initial tasks from warehouse packages."""
        task_num = 1
        for pkg_id, pkg in self.warehouse.packages.items():
            task_id = f"T{task_num}"
            task = Task(
                task_id=task_id,
                package_id=pkg_id,
                pickup_location=pkg.location,
                delivery_station=pkg.delivery_station,
                priority=1,
                creation_time=0,
            )
            self.tasks[task_id] = task
            task_num += 1
        self._task_counter = task_num
    
    # ──────────────────────────────────────────────────────────────────────
    # STATE SERIALIZATION
    # ──────────────────────────────────────────────────────────────────────
    
    def get_full_state(self) -> Dict:
        """Serialize the complete simulation state for frontend consumption."""
        pending_count = sum(
            1 for t in self.tasks.values() if t.status in ("PENDING", "ASSIGNED", "IN_PROGRESS")
        )
        stats = self.statistics.to_dict()
        stats["pending_deliveries"] = pending_count
        
        packages_list = []
        for pkg in self.warehouse.packages.values():
            packages_list.append({
                "package_id": pkg.package_id,
                "location": list(pkg.location),
                "delivery_station": list(pkg.delivery_station),
                "status": pkg.status,
                "assigned_robot": pkg.assigned_robot,
            })
        
        tasks_list = []
        for task in self.tasks.values():
            tasks_list.append({
                "task_id": task.task_id,
                "package_id": task.package_id,
                "pickup_location": list(task.pickup_location),
                "delivery_station": list(task.delivery_station),
                "priority": task.priority,
                "status": task.status,
                "assigned_robot": task.assigned_robot,
                "estimated_cost": 0.0 if (task.estimated_cost == float('inf') or task.estimated_cost is None) else round(float(task.estimated_cost), 1),
                "creation_time": task.creation_time,
                "completion_time": task.completion_time,
            })
        
        reservation_snap = self.reservation_table.get_snapshot()
        
        return {
            "grid_width": self.warehouse.grid_width,
            "grid_height": self.warehouse.grid_height,
            "obstacles": [list(o) for o in self.warehouse.get_all_obstacles()],
            "shelves": [list(s) for s in self.warehouse.shelves],
            "dynamic_obstacles": [list(o) for o in self.warehouse.dynamic_obstacles],
            "pickup_locations": [list(p) for p in self.warehouse.pickup_locations],
            "delivery_stations": [list(d) for d in self.warehouse.delivery_stations],
            "charging_stations": [list(c) for c in self.warehouse.charging_stations],
            "robots": [r.to_dict() for r in self.robots.values()],
            "packages": packages_list,
            "tasks": tasks_list,
            "statistics": stats,
            "simulation_step": self.simulation_step,
            "is_running": self.is_running,
            "speed": self.speed,
            "active_algorithm": self.active_algorithm,
            "event_logs": self.event_log.recent(100),
            "reservation_table": reservation_snap,
            "rules": self.rule_engine.get_rules_summary(),
            "backtracking": self.get_backtracking_state(include_trace=False),
        }
    
    def get_backtracking_state(self, include_trace: bool = True) -> Dict:
        """Latest search reports and active nogoods for the UI."""
        allocation = self.last_allocation_search
        if allocation and not include_trace:
            allocation = {k: v for k, v in allocation.items() if k != "trace"}
        return {
            "allocation_search": allocation,
            "ordering_search": self.last_ordering_search,
            "nogoods": [
                {"robot_id": r, "task_id": t, "expires_at": exp}
                for (r, t), exp in self.nogoods.items()
                if exp > self.simulation_step
            ] + [
                {"robot_id": None, "task_id": t, "expires_at": exp}
                for t, exp in self.deferred_tasks.items()
                if exp > self.simulation_step
            ],
        }
    
    async def _broadcast_state(self):
        """Send the current state to all connected WebSocket clients."""
        if self._broadcast_callback:
            try:
                state = self.get_full_state()
                await self._broadcast_callback(state)
            except Exception as e:
                pass  # Don't crash simulation on broadcast failure


# Singleton simulation engine
_engine: Optional[SimulationEngine] = None


def get_engine() -> SimulationEngine:
    """Get or create the singleton simulation engine."""
    global _engine
    if _engine is None:
        _engine = SimulationEngine()
        _engine.load_initial_tasks()
    return _engine
