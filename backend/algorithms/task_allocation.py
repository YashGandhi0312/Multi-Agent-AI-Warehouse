"""
Minimum-Cost Greedy Task Allocation
=====================================
Classical AI task assignment for multi-robot warehouse management.

Algorithm: Greedy Minimum-Cost Assignment
This is a heuristic task allocator. For each unassigned task,
it selects the robot with the minimum estimated travel cost.

Cost Function:
  cost(robot, task) = dist(robot_pos → package_pos) + dist(package_pos → delivery_station)

This greedy heuristic does NOT guarantee globally optimal assignment
(which would require the Hungarian Algorithm for true optimality),
but it is computationally efficient and produces good results for
real-time warehouse management scenarios.

Time Complexity: O(T × R) per allocation cycle, where T = tasks, R = robots
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from algorithms.astar import astar_search


@dataclass
class Task:
    """Represents a delivery task in the warehouse."""
    task_id: str
    package_id: str
    pickup_location: Tuple[int, int]
    delivery_station: Tuple[int, int]
    priority: int = 1           # Higher = more important
    status: str = "PENDING"     # PENDING, ASSIGNED, IN_PROGRESS, COMPLETED
    assigned_robot: Optional[str] = None
    estimated_cost: float = 0.0
    actual_cost: int = 0
    creation_time: int = 0
    completion_time: Optional[int] = None


@dataclass
class AllocationResult:
    """Result of a single task allocation decision."""
    task_id: str
    robot_id: str
    package_location: Tuple[int, int]
    delivery_station: Tuple[int, int]
    estimated_cost: float
    cost_breakdown: Dict[str, float]
    allocation_time_ms: float
    reason: str


def estimate_task_cost(
    robot_pos: Tuple[int, int],
    pickup: Tuple[int, int],
    delivery: Tuple[int, int],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
) -> Tuple[float, Dict[str, float]]:
    """
    Estimate the total cost for a robot to complete a task.
    
    Uses A* to calculate realistic path distances (not just straight-line).
    Falls back to Manhattan distance if A* fails.
    
    Returns:
        (total_cost, breakdown_dict)
    """
    # Cost leg 1: Robot's current position → Package pickup
    leg1_result = astar_search(robot_pos, pickup, grid_width, grid_height, obstacles)
    
    if leg1_result.success:
        leg1_cost = float(leg1_result.path_length)
    else:
        # Manhattan distance fallback (admissible lower bound)
        leg1_cost = float(abs(pickup[0] - robot_pos[0]) + abs(pickup[1] - robot_pos[1]))
        leg1_cost *= 1.5  # Penalty for potentially blocked path
    
    # Cost leg 2: Package pickup → Delivery station
    leg2_result = astar_search(pickup, delivery, grid_width, grid_height, obstacles)
    
    if leg2_result.success:
        leg2_cost = float(leg2_result.path_length)
    else:
        leg2_cost = float(abs(delivery[0] - pickup[0]) + abs(delivery[1] - pickup[1]))
        leg2_cost *= 1.5
    
    total_cost = leg1_cost + leg2_cost
    breakdown = {
        "robot_to_package": leg1_cost,
        "package_to_delivery": leg2_cost,
        "total": total_cost
    }
    return total_cost, breakdown


def allocate_tasks(
    tasks: List[Task],
    robot_positions: Dict[str, Tuple[int, int]],
    available_robots: Set[str],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
) -> List[AllocationResult]:
    """
    Greedy minimum-cost task allocation.
    
    For each PENDING task (sorted by priority descending):
      1. Calculate cost for every available robot
      2. Assign to the robot with minimum cost
      3. Remove assigned robot from available pool for this cycle
    
    Args:
        tasks: List of all tasks
        robot_positions: Current positions of all robots
        available_robots: Set of robot IDs that can be assigned a new task
        grid_width, grid_height: Grid dimensions
        obstacles: Obstacle positions
    
    Returns:
        List of AllocationResult for each new assignment made
    """
    allocations = []
    t0 = time.perf_counter()
    
    # Sort pending tasks by priority (descending), then creation time
    pending_tasks = [
        t for t in tasks
        if t.status == "PENDING" and t.assigned_robot is None
    ]
    pending_tasks.sort(key=lambda t: (-t.priority, t.creation_time))
    
    # Work with a mutable copy of available robots
    remaining_available = set(available_robots)
    
    for task in pending_tasks:
        if not remaining_available:
            break  # No more robots available
        
        best_robot: Optional[str] = None
        best_cost = float('inf')
        best_breakdown: Dict[str, float] = {}
        
        # Evaluate cost for each available robot
        for robot_id in remaining_available:
            if robot_id not in robot_positions:
                continue
            
            robot_pos = robot_positions[robot_id]
            cost, breakdown = estimate_task_cost(
                robot_pos,
                task.pickup_location,
                task.delivery_station,
                grid_width,
                grid_height,
                obstacles,
            )
            
            # Select robot with minimum cost
            if cost < best_cost:
                best_cost = cost
                best_robot = robot_id
                best_breakdown = breakdown
        
        if best_robot is not None:
            # Assign the task
            task.assigned_robot = best_robot
            task.status = "ASSIGNED"
            task.estimated_cost = best_cost
            
            # Remove robot from available pool for this allocation cycle
            remaining_available.discard(best_robot)
            
            elapsed = (time.perf_counter() - t0) * 1000
            allocation = AllocationResult(
                task_id=task.task_id,
                robot_id=best_robot,
                package_location=task.pickup_location,
                delivery_station=task.delivery_station,
                estimated_cost=best_cost,
                cost_breakdown=best_breakdown,
                allocation_time_ms=elapsed,
                reason=(
                    f"Robot {best_robot} selected: min cost {best_cost:.1f} "
                    f"(to_pkg={best_breakdown.get('robot_to_package', 0):.1f}, "
                    f"to_delivery={best_breakdown.get('package_to_delivery', 0):.1f})"
                )
            )
            allocations.append(allocation)
    
    return allocations


def build_cost_matrix(
    tasks: List[Task],
    robot_positions: Dict[str, Tuple[int, int]],
    robot_ids: List[str],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
) -> Dict:
    """
    Build a robot × task cost matrix for visualization in the UI.
    Shows why each assignment was made.
    """
    matrix = {}
    for robot_id in robot_ids:
        if robot_id not in robot_positions:
            continue
        matrix[robot_id] = {}
        for task in tasks:
            if task.status in ("COMPLETED",):
                continue
            cost, breakdown = estimate_task_cost(
                robot_positions[robot_id],
                task.pickup_location,
                task.delivery_station,
                grid_width, grid_height, obstacles,
            )
            matrix[robot_id][task.task_id] = {
                "cost": round(cost, 1),
                "to_package": round(breakdown["robot_to_package"], 1),
                "to_delivery": round(breakdown["package_to_delivery"], 1),
            }
    return matrix
