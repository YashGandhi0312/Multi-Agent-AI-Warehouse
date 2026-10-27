"""
Tests for Backtracking Search and Agent Deliberation
======================================================
Tests for: branch & bound allocation, priority-order backtracking,
robot decision stack, engine-level agent backtracking.

Run with: python -m pytest tests/test_backtracking.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import itertools

import pytest
from algorithms.backtracking import (
    SKIP_PENALTY, backtracking_allocate, plan_with_order_backtracking
)
from algorithms.cooperative_astar import ReservationTable, plan_all_robots
from algorithms.task_allocation import Task, allocate_tasks
from agents.robot import RobotState, create_robot
from simulation.simulation_engine import (
    MAX_ROUTE_ALTERNATIVES, SimulationEngine
)


def make_task(tid, pickup, delivery, priority=1):
    return Task(tid, f"P{tid}", pickup, delivery, priority=priority)


# ─────────────────────────────────────────────────────────────────────────────
# Branch & Bound Allocation
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktrackingAllocation:

    def test_beats_greedy_on_classic_counterexample(self):
        """Greedy gives T1 to the nearest robot and strands T2; B&B does not."""
        positions = {"R1": (0, 0), "R2": (5, 0)}
        greedy_tasks = [make_task("T1", (4, 0), (4, 0)), make_task("T2", (6, 0), (6, 0))]
        bb_tasks = [make_task("T1", (4, 0), (4, 0)), make_task("T2", (6, 0), (6, 0))]

        greedy = allocate_tasks(greedy_tasks, positions, {"R1", "R2"}, 10, 10, set())
        allocs, report = backtracking_allocate(bb_tasks, positions, {"R1", "R2"}, 10, 10, set())

        greedy_total = sum(a.estimated_cost for a in greedy)
        bb_total = sum(a.estimated_cost for a in allocs)
        assert greedy_total == 7
        assert bb_total == 5
        assert report.optimal
        assert report.to_dict()["cost_saved"] == 2
        assert {a.task_id: a.robot_id for a in allocs} == {"T1": "R1", "T2": "R2"}

    def test_matches_brute_force_optimum(self):
        """B&B finds the same joint cost as exhaustive enumeration."""
        positions = {"R1": (0, 0), "R2": (9, 9), "R3": (0, 9), "R4": (5, 5)}
        specs = [((2, 2), (8, 1)), ((7, 7), (1, 1)), ((1, 8), (9, 0)), ((4, 6), (4, 0))]
        tasks = [make_task(f"T{i}", p, d) for i, (p, d) in enumerate(specs)]
        allocs, report = backtracking_allocate(tasks, positions, set(positions), 10, 10, set())

        def cost(r, p, d):
            rx, ry = positions[r]
            return abs(rx - p[0]) + abs(ry - p[1]) + abs(p[0] - d[0]) + abs(p[1] - d[1])

        brute = min(
            sum(cost(r, *specs[i]) for i, r in enumerate(perm))
            for perm in itertools.permutations(positions)
        )
        assert sum(a.estimated_cost for a in allocs) == brute
        assert report.optimal
        assert report.branches_pruned > 0

    def test_respects_forbidden_pairs(self):
        """Agent nogoods remove a (robot, task) pair from the domain."""
        positions = {"R1": (0, 0), "R2": (9, 0)}
        tasks = [make_task("T1", (1, 0), (1, 0))]
        allocs, _ = backtracking_allocate(
            tasks, positions, {"R1", "R2"}, 10, 10, set(),
            forbidden_pairs={("R1", "T1")},
        )
        assert allocs[0].robot_id == "R2"

    def test_skips_task_with_no_allowed_robot(self):
        positions = {"R1": (0, 0)}
        tasks = [make_task("T1", (1, 0), (1, 0))]
        allocs, report = backtracking_allocate(
            tasks, positions, {"R1"}, 10, 10, set(),
            forbidden_pairs={("R1", "T1")},
        )
        assert allocs == []
        assert tasks[0].status == "PENDING"
        assert report.best_cost == SKIP_PENALTY

    def test_priority_tasks_considered_first(self):
        """Only the top-K tasks by priority are allocated when robots are scarce."""
        positions = {"R1": (0, 0)}
        tasks = [
            make_task("T1", (1, 0), (1, 0), priority=1),
            make_task("T2", (9, 9), (9, 9), priority=5),
        ]
        allocs, _ = backtracking_allocate(tasks, positions, {"R1"}, 10, 10, set())
        assert [a.task_id for a in allocs] == ["T2"]

    def test_node_budget_returns_best_found(self):
        # Every task's cheapest robot is R0, so the bound is loose and the
        # full search needs hundreds of nodes.
        positions = {f"R{i}": (0, i) for i in range(6)}
        tasks = [make_task(f"T{i}", (1 + i, 0), (9, 9 - i)) for i in range(6)]
        allocs, report = backtracking_allocate(
            tasks, positions, set(positions), 10, 10, set(), max_nodes=1,
        )
        assert not report.optimal
        assert len(allocs) == 6  # first descent always completes a solution

    def test_trace_records_search_tree(self):
        positions = {"R1": (0, 0), "R2": (5, 0)}
        tasks = [make_task("T1", (4, 0), (4, 0)), make_task("T2", (6, 0), (6, 0))]
        _, report = backtracking_allocate(tasks, positions, {"R1", "R2"}, 10, 10, set())
        statuses = {n["status"] for n in report.trace}
        assert "best" in statuses
        assert all(n["parent"] is None or n["parent"] < n["id"] for n in report.trace)


# ─────────────────────────────────────────────────────────────────────────────
# Priority-Order Backtracking
# ─────────────────────────────────────────────────────────────────────────────

class TestOrderBacktracking:

    # 1×4 corridor: A at 0 → 3 runs over B at 2. If A is planned first,
    # B is trapped in the dead end and cannot get out of A's way.
    CORRIDOR = dict(grid_width=4, grid_height=1, obstacles=set())
    PLANS = [
        {"robot_id": "A", "start": (0, 0), "goal": (3, 0)},
        {"robot_id": "B", "start": (2, 0), "goal": (1, 0)},
    ]

    def test_fixed_order_fails_in_corridor(self):
        results = plan_all_robots(self.PLANS, **self.CORRIDOR,
                                  reservation_table=ReservationTable())
        assert results[0].success and not results[1].success

    def test_backtracking_finds_working_order(self):
        table = ReservationTable()
        results, report = plan_with_order_backtracking(
            self.PLANS, **self.CORRIDOR, reservation_table=table,
        )
        assert all(r.success for r in results)
        assert report.resolved_by_backtracking
        assert report.final_order == ["B", "A"]
        # Reservation table holds exactly the final plans
        owners = set(table.vertex_reservations.values())
        assert owners == {"A", "B"}

    def test_unsolvable_robot_is_not_searched(self):
        """A robot whose goal is walled off fails under every order."""
        plans = [
            {"robot_id": "A", "start": (0, 0), "goal": (4, 0)},
            {"robot_id": "B", "start": (0, 2), "goal": (4, 2)},
        ]
        walls = {(3, 0), (4, 1)}  # (4,0) unreachable
        results, report = plan_with_order_backtracking(
            plans, 5, 3, walls, ReservationTable(),
        )
        assert not results[0].success and results[1].success
        assert report.unsolvable == ["A"]
        assert report.backtracks == 0

    def test_avoid_cells_force_alternative_route(self):
        plans = [{"robot_id": "A", "start": (0, 0), "goal": (2, 0), "avoid": {(1, 0)}}]
        results, _ = plan_with_order_backtracking(plans, 3, 2, set(), ReservationTable())
        assert results[0].success
        assert (1, 0) not in results[0].path


# ─────────────────────────────────────────────────────────────────────────────
# Agent Decision Stack
# ─────────────────────────────────────────────────────────────────────────────

class TestAgentDeliberation:

    def test_commit_task_pops_route_and_marks_task(self):
        r = create_robot("R1", (0, 0))
        r.push_choice("TASK", task_id="T1")
        r.push_choice("ROUTE")
        r.commit_task()
        assert len(r.decision_stack) == 1
        assert r.top_choice()["committed"]

    def test_stack_cleared_on_delivery(self):
        r = create_robot("R1", (0, 0))
        r.assign_task("T1", "P1", (0, 0), (0, 0))
        r.push_choice("TASK", task_id="T1")
        r.has_package = True
        r.force_state(RobotState.MOVING_TO_DELIVERY)
        r.transition_to(RobotState.DELIVERING)
        assert r.deliver_package() == "P1"
        assert r.decision_stack == []

    def _engine_with_stuck_robot(self):
        engine = SimulationEngine()
        engine.load_initial_tasks()
        robot = engine.robots["R1"]
        task = next(iter(engine.tasks.values()))
        robot.assign_task(task.task_id, task.package_id,
                          task.pickup_location, task.delivery_station)
        task.status, task.assigned_robot = "ASSIGNED", "R1"
        robot.push_choice("TASK", task_id=task.task_id)
        robot.push_choice("ROUTE")
        robot.force_state(RobotState.BLOCKED)
        return engine, robot, task

    def test_route_alternatives_then_task_release(self):
        engine, robot, task = self._engine_with_stuck_robot()
        step = 10
        for attempt in range(1, MAX_ROUTE_ALTERNATIVES + 1):
            engine._agent_backtrack(robot, step)
            assert robot.state == RobotState.REPLANNING
            assert robot.top_choice()["attempts"] == attempt
            robot.force_state(RobotState.BLOCKED)
            step += 10
        engine._agent_backtrack(robot, step)
        assert robot.state == RobotState.IDLE
        assert robot.task_id is None
        assert task.status == "PENDING" and task.assigned_robot is None
        assert ("R1", task.task_id) in engine.nogoods
        assert engine.statistics.agent_backtracks == MAX_ROUTE_ALTERNATIVES + 1

    def test_cooldown_limits_backtracks(self):
        engine, robot, _ = self._engine_with_stuck_robot()
        engine._agent_backtrack(robot, 5)
        engine._agent_backtrack(robot, 6)
        assert robot.backtrack_count == 1

    def test_committed_robot_yields_instead_of_abandoning(self):
        engine, robot, task = self._engine_with_stuck_robot()
        robot.pop_choice()
        robot.has_package = True
        robot.commit_task()
        engine._agent_backtrack(robot, 10)
        assert robot.task_id == task.task_id
        assert robot.state == RobotState.MOVING_TO_DELIVERY
        assert len(robot.path) == 1

    def test_simulation_runs_with_backtracking(self):
        engine = SimulationEngine()
        engine.load_initial_tasks()

        async def run():
            for _ in range(80):
                await engine._execute_step()

        asyncio.run(run())
        stats = engine.statistics
        assert stats.completed_deliveries > 0
        assert stats.search_nodes > 0
        state = engine.get_full_state()
        assert "backtracking" in state
        assert state["backtracking"]["allocation_search"] is not None

    def test_unreachable_pickup_deferred_for_all_robots(self):
        engine, robot, task = self._engine_with_stuck_robot()
        px, py = task.pickup_location
        for cell in [(px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)]:
            if engine.warehouse.is_traversable(cell):
                engine.warehouse.add_obstacle(cell)
        engine._agent_backtrack(robot, 10)
        # No route retries for a walled-off goal: straight to the TASK choice
        assert robot.state == RobotState.IDLE
        assert task.task_id in engine.deferred_tasks
        assert ("R1", task.task_id) not in engine.nogoods

    def test_removing_obstacle_invalidates_nogoods(self):
        engine, _, task = self._engine_with_stuck_robot()
        engine.add_obstacle((0, 0))
        engine.nogoods[("R1", task.task_id)] = 99
        engine.deferred_tasks[task.task_id] = 99
        engine.remove_obstacle((0, 0))
        assert not engine.nogoods and not engine.deferred_tasks

    def test_wait_for_cycle_breaks_deadlock(self):
        engine, r1, _ = self._engine_with_stuck_robot()
        r1.force_state(RobotState.MOVING_TO_PICKUP)
        r1.path = [(5, 5)]
        r2 = engine.robots["R2"]
        r2.has_package = True
        r2.force_state(RobotState.MOVING_TO_DELIVERY)
        actions = {
            "R1": {"action": {"type": "WAIT", "blocked_by": "R2"}},
            "R2": {"action": {"type": "WAIT", "blocked_by": "R1"}},
        }
        positions = {rid: r.position for rid, r in engine.robots.items()}
        engine._monitor_agents(actions, positions, step=10)
        assert engine.statistics.deadlocks_resolved == 1
        # R1 has no package, so it is the one that backs off
        assert r1.backtrack_count == 1 and r2.backtrack_count == 0
        assert (5, 5) in r1.avoid_cells
