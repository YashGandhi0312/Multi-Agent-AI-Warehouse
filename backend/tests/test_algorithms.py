"""
Automated Tests for Classical AI Algorithms
==============================================
Tests for: A*, Cooperative A*, Task Allocation, Robot State Machine

Run with: python -m pytest tests/test_algorithms.py -v
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from algorithms.astar import astar_search, bfs_search
from algorithms.cooperative_astar import (
    ReservationTable, cooperative_astar, plan_all_robots
)
from algorithms.task_allocation import Task, allocate_tasks
from agents.robot import Robot, RobotState, create_robot


# ─────────────────────────────────────────────────────────────────────────────
# A* Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAStarSearch:
    """Test suite for the A* search algorithm."""
    
    def test_finds_shortest_path_on_open_grid(self):
        """A* finds a valid path on an open grid."""
        result = astar_search((0, 0), (5, 5), 10, 10, set())
        assert result.success
        assert result.path_length == 10  # Manhattan distance (optimal)
        assert result.path[0] == (0, 0)
        assert result.path[-1] == (5, 5)
    
    def test_handles_unreachable_destination(self):
        """A* returns failure when goal is completely surrounded by obstacles."""
        # Surround the goal at (5, 5)
        obstacles = {(4, 5), (6, 5), (5, 4), (5, 6)}
        result = astar_search((0, 0), (5, 5), 10, 10, obstacles)
        assert not result.success
        assert result.path == []
    
    def test_never_crosses_obstacles(self):
        """A* path never passes through obstacle cells."""
        obstacles = {(3, 0), (3, 1), (3, 2), (3, 3), (3, 4)}
        result = astar_search((0, 2), (6, 2), 10, 10, obstacles)
        assert result.success
        for pos in result.path:
            assert pos not in obstacles, f"Path crosses obstacle at {pos}"
    
    def test_reaches_goal_with_obstacles_around(self):
        """A* navigates around a wall obstacle."""
        # Vertical wall at x=3, with a gap at y=4
        obstacles = {(3, 0), (3, 1), (3, 2), (3, 3)}
        result = astar_search((0, 0), (6, 0), 10, 10, obstacles)
        assert result.success
        assert result.path[-1] == (6, 0)
    
    def test_start_equals_goal(self):
        """A* immediately returns when start equals goal."""
        result = astar_search((3, 3), (3, 3), 10, 10, set())
        assert result.success
        assert result.path_length == 0
        assert result.path == [(3, 3)]
    
    def test_path_is_connected(self):
        """Each consecutive pair in the A* path is adjacent (distance 1)."""
        result = astar_search((0, 0), (9, 9), 15, 15, set())
        assert result.success
        for i in range(len(result.path) - 1):
            x1, y1 = result.path[i]
            x2, y2 = result.path[i + 1]
            manhattan = abs(x2 - x1) + abs(y2 - y1)
            assert manhattan == 1, f"Non-adjacent steps in path: {result.path[i]} → {result.path[i+1]}"
    
    def test_blocked_start_returns_failure(self):
        """A* fails if start is in obstacles."""
        obstacles = {(0, 0)}
        result = astar_search((0, 0), (5, 5), 10, 10, obstacles)
        assert not result.success
    
    def test_blocked_goal_returns_failure(self):
        """A* fails if goal is in obstacles."""
        obstacles = {(5, 5)}
        result = astar_search((0, 0), (5, 5), 10, 10, obstacles)
        assert not result.success
    
    def test_nodes_explored_count_is_positive(self):
        """A* tracks the number of nodes explored."""
        result = astar_search((0, 0), (5, 5), 10, 10, set())
        assert result.nodes_explored > 0
    
    def test_planning_time_is_positive(self):
        """A* records planning time in milliseconds."""
        result = astar_search((0, 0), (5, 5), 10, 10, set())
        assert result.planning_time_ms >= 0


# ─────────────────────────────────────────────────────────────────────────────
# Cooperative A* Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCooperativeAStar:
    """Test suite for Cooperative A* multi-robot pathfinding."""
    
    def test_prevents_vertex_collision(self):
        """Two robots must not occupy the same cell at the same time step."""
        obstacles = set()
        rtable = ReservationTable()
        
        # Robot 1 plans from (0,0) to (4,0)
        r1 = cooperative_astar("R1", (0, 0), (4, 0), 0, 10, 10, obstacles, rtable)
        assert r1.success
        rtable.reserve_path(r1.time_path, "R1")
        
        # Robot 2 plans from (4,0) to (0,0) — same corridor
        r2 = cooperative_astar("R2", (4, 0), (0, 0), 0, 10, 10, obstacles, rtable)
        assert r2.success
        
        # Check no vertex collision
        r1_cells = {(x, y, t) for x, y, t in r1.time_path}
        r2_cells = {(x, y, t) for x, y, t in r2.time_path}
        overlap = r1_cells & r2_cells
        assert len(overlap) == 0, f"Vertex collision detected: {overlap}"
    
    def test_prevents_edge_swap_collision(self):
        """Two robots must not exchange positions in the same time step."""
        obstacles = set()
        rtable = ReservationTable()
        
        # R1 at (2,0) going to (3,0), R2 at (3,0) going to (2,0)
        r1 = cooperative_astar("R1", (0, 0), (5, 0), 0, 10, 5, obstacles, rtable)
        assert r1.success
        rtable.reserve_path(r1.time_path, "R1")
        
        r2 = cooperative_astar("R2", (5, 0), (0, 0), 0, 10, 5, obstacles, rtable)
        assert r2.success
        
        # Check no edge-swap: if R1 moves A→B at time t, R2 cannot move B→A at time t
        r1_moves = set()
        for i in range(len(r1.time_path) - 1):
            x1, y1, t = r1.time_path[i]
            x2, y2, _ = r1.time_path[i + 1]
            if (x1, y1) != (x2, y2):
                r1_moves.add((x1, y1, x2, y2, t))
        
        for i in range(len(r2.time_path) - 1):
            x1, y1, t = r2.time_path[i]
            x2, y2, _ = r2.time_path[i + 1]
            if (x1, y1) != (x2, y2):
                # Check reverse edge in same time step
                assert (x2, y2, x1, y1, t) not in r1_moves, \
                    f"Edge-swap collision: R2 swaps with R1 at time {t}"
    
    def test_robots_can_wait(self):
        """A robot can wait (stay in place) when path is blocked."""
        obstacles = set()
        rtable = ReservationTable()
        
        # Reserve the only path through a bottleneck for R1
        r1 = cooperative_astar("R1", (0, 0), (3, 0), 0, 5, 3, obstacles, rtable)
        assert r1.success
        rtable.reserve_path(r1.time_path, "R1")
        
        # R2 starts in a position that forces it to wait
        r2 = cooperative_astar("R2", (1, 0), (4, 0), 0, 5, 3, obstacles, rtable)
        # R2 may succeed with waits or take a different route
        # Either way, it should not collide with R1
        if r2.success:
            r1_cells = {(x, y, t) for x, y, t in r1.time_path}
            r2_cells = {(x, y, t) for x, y, t in r2.time_path}
            assert len(r1_cells & r2_cells) == 0
    
    def test_single_robot_finds_correct_path(self):
        """CA* with single robot finds the same path as A*."""
        from algorithms.astar import astar_search
        obstacles = set()
        rtable = ReservationTable()
        
        ca_result = cooperative_astar("R1", (0, 0), (4, 4), 0, 10, 10, obstacles, rtable)
        a_result = astar_search((0, 0), (4, 4), 10, 10, obstacles)
        
        assert ca_result.success
        assert a_result.success
        # Both should find path of length 8
        assert ca_result.path_length == a_result.path_length


# ─────────────────────────────────────────────────────────────────────────────
# Task Allocation Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestTaskAllocation:
    """Test suite for greedy minimum-cost task allocation."""
    
    def _make_task(self, task_id, pkg_id, pickup, delivery):
        return Task(
            task_id=task_id, package_id=pkg_id,
            pickup_location=pickup, delivery_station=delivery,
        )
    
    def test_assigns_only_to_available_robots(self):
        """Task allocation only assigns tasks to robots in the available set."""
        tasks = [self._make_task("T1", "P1", (0, 0), (9, 9))]
        positions = {"R1": (0, 1), "R2": (5, 5)}
        available = {"R1"}  # Only R1 is available
        
        results = allocate_tasks(tasks, positions, available, 10, 10, set())
        assert len(results) == 1
        assert results[0].robot_id == "R1"
    
    def test_does_not_assign_unavailable_robots(self):
        """Busy robots (not in available set) are never assigned."""
        tasks = [self._make_task("T1", "P1", (0, 0), (9, 9))]
        positions = {"R1": (0, 1)}
        available = set()  # No robots available
        
        results = allocate_tasks(tasks, positions, available, 10, 10, set())
        assert len(results) == 0
    
    def test_assigns_nearest_robot_to_package(self):
        """Nearest robot to the pickup location is preferred."""
        tasks = [self._make_task("T1", "P1", (5, 0), (5, 9))]
        positions = {"R1": (0, 0), "R2": (4, 0)}  # R2 is closer to pickup (5,0)
        available = {"R1", "R2"}
        
        results = allocate_tasks(tasks, positions, available, 10, 10, set())
        assert len(results) == 1
        assert results[0].robot_id == "R2"
    
    def test_no_double_assignment_per_cycle(self):
        """Each robot is assigned at most one task per allocation cycle."""
        tasks = [
            self._make_task("T1", "P1", (0, 0), (9, 9)),
            self._make_task("T2", "P2", (1, 0), (8, 9)),
        ]
        positions = {"R1": (0, 1)}
        available = {"R1"}
        
        results = allocate_tasks(tasks, positions, available, 10, 10, set())
        # R1 can only be assigned once
        robot_assignments = [r.robot_id for r in results]
        assert robot_assignments.count("R1") <= 1


# ─────────────────────────────────────────────────────────────────────────────
# Robot State Machine Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestRobotStateMachine:
    """Test suite for the robot finite-state machine."""
    
    def test_initial_state_is_idle(self):
        """A newly created robot starts in IDLE state."""
        robot = create_robot("R1", (0, 0))
        assert robot.state == RobotState.IDLE
    
    def test_valid_transition_idle_to_assigned(self):
        """IDLE → ASSIGNED is a valid transition."""
        robot = create_robot("R1", (0, 0))
        success = robot.transition_to(RobotState.ASSIGNED)
        assert success
        assert robot.state == RobotState.ASSIGNED
    
    def test_invalid_transition_idle_to_delivering(self):
        """IDLE → DELIVERING is not a valid transition."""
        robot = create_robot("R1", (0, 0))
        success = robot.transition_to(RobotState.DELIVERING)
        assert not success
        assert robot.state == RobotState.IDLE  # State unchanged
    
    def test_package_cannot_be_picked_up_twice(self):
        """A robot already carrying a package cannot pick up another."""
        robot = create_robot("R1", (2, 2))
        robot.has_package = True
        robot.force_state(RobotState.MOVING_TO_DELIVERY)
        # Attempt pick up (should fail)
        result = robot.pick_up_package()
        assert not result
    
    def test_delivery_only_at_correct_station(self):
        """Package delivery only completes at the designated station."""
        robot = create_robot("R1", (5, 5))
        robot.has_package = True
        robot.package_id = "P1"
        robot.task_id = "T1"
        robot.delivery_target = (9, 9)
        robot.force_state(RobotState.MOVING_TO_DELIVERY)
        
        # Not at delivery station yet
        result = robot.deliver_package()
        assert result is None
        assert robot.has_package
        
        # Move to delivery station
        robot.position = (9, 9)
        result = robot.deliver_package()
        assert result == "P1"
        assert not robot.has_package
        assert robot.state == RobotState.IDLE
    
    def test_distance_tracked_correctly(self):
        """Robot correctly tracks distance traveled."""
        robot = create_robot("R1", (0, 0))
        robot.path = [(1, 0), (2, 0), (3, 0)]
        
        robot.advance_position()
        robot.advance_position()
        assert robot.distance_traveled == 2
        assert robot.position == (2, 0)
    
    def test_task_reset_on_clear(self):
        """Clearing a task resets all task-related fields."""
        robot = create_robot("R1", (0, 0))
        robot.task_id = "T1"
        robot.package_id = "P1"
        robot.pickup_target = (3, 3)
        robot.delivery_target = (7, 7)
        robot.has_package = True
        
        robot.clear_task()
        
        assert robot.task_id is None
        assert robot.package_id is None
        assert robot.pickup_target is None
        assert robot.delivery_target is None
        assert not robot.has_package
    
    def test_full_delivery_lifecycle(self):
        """Test complete IDLE → ASSIGNED → ... → DELIVERING → IDLE lifecycle."""
        robot = create_robot("R1", (0, 0))
        
        # Assign task
        robot.assign_task("T1", "P1", (2, 2), (8, 8))
        assert robot.state == RobotState.ASSIGNED
        assert robot.task_id == "T1"
        
        # Transition to moving to pickup
        robot.transition_to(RobotState.MOVING_TO_PICKUP)
        assert robot.state == RobotState.MOVING_TO_PICKUP
        
        # Move to pickup
        robot.position = (2, 2)
        robot.transition_to(RobotState.PICKING_UP)
        robot.has_package = True
        robot.transition_to(RobotState.MOVING_TO_DELIVERY)
        assert robot.state == RobotState.MOVING_TO_DELIVERY
        
        # Deliver
        robot.position = (8, 8)
        result = robot.deliver_package()
        assert result == "P1"
        assert robot.state == RobotState.IDLE
        assert robot.tasks_completed == 1


# ─────────────────────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_dynamic_obstacle_invalidates_path(self):
        """Adding an obstacle mid-path should be detected."""
        from simulation.warehouse import Warehouse
        
        w = Warehouse(10, 10)
        
        # Plan a path through x=5
        obstacles = w.get_all_obstacles()
        result = astar_search((0, 0), (9, 0), 10, 10, obstacles)
        assert result.success
        
        # Add obstacle in the path
        w.add_obstacle((4, 0))
        new_obstacles = w.get_all_obstacles()
        
        # Old path is now invalid
        old_path_valid = all(pos not in new_obstacles for pos in result.path)
        assert not old_path_valid  # Path is now blocked
        
        # Replan succeeds
        new_result = astar_search((0, 0), (9, 0), 10, 10, new_obstacles)
        assert new_result.success
        for pos in new_result.path:
            assert pos not in new_obstacles
    
    def test_astar_vs_bfs_same_path_length(self):
        """On unweighted grids, A* and BFS find paths of equal length."""
        obstacles = {(3, 0), (3, 1), (3, 2)}
        
        a_result = astar_search((0, 0), (6, 0), 10, 5, obstacles)
        b_result = bfs_search((0, 0), (6, 0), 10, 5, obstacles)
        
        assert a_result.success and b_result.success
        assert a_result.path_length == b_result.path_length, \
            "A* and BFS should find the same optimal path length"
    
    def test_plan_all_robots_no_conflicts(self):
        """Planning all robots cooperatively produces conflict-free paths."""
        obstacles = set()
        rtable = ReservationTable()
        
        plans = [
            {"robot_id": "R1", "start": (0, 0), "goal": (9, 9)},
            {"robot_id": "R2", "start": (9, 0), "goal": (0, 9)},
            {"robot_id": "R3", "start": (0, 9), "goal": (9, 0)},
        ]
        
        results = plan_all_robots(plans, 10, 10, obstacles, rtable)
        
        successful = [r for r in results if r.success]
        assert len(successful) >= 2  # At least 2 should succeed
        
        # Check no vertex conflicts among all time paths
        all_cells: set = set()
        for r in successful:
            for state in r.time_path:
                assert state not in all_cells, f"Vertex conflict at {state}"
                all_cells.add(state)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
