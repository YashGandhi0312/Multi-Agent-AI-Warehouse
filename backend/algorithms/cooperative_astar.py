"""
Cooperative A* (CA*) Search Algorithm
=======================================
Multi-robot pathfinding with collision avoidance using time-space reservation.

Algorithm: Cooperative A* (Silver, 2005)
- Extends standard A* with a time dimension
- Each state is (x, y, time) instead of just (x, y)
- Uses a shared Reservation Table to prevent conflicts

Collision Types Prevented:
  1. Vertex collision: Two robots at same (x,y) at same time t
  2. Edge-swap collision: Robots swapping positions between t and t+1

Planning Strategy:
  - Robots plan sequentially in priority order
  - Earlier-priority robots reserve their full paths
  - Later-priority robots plan around existing reservations
  - Robots may wait (stay in place) to avoid conflicts
"""

import heapq
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from algorithms.astar import manhattan_distance


@dataclass
class CAStarResult:
    """Result of a Cooperative A* plan for one robot."""
    robot_id: str
    path: List[Tuple[int, int]]           # spatial path
    time_path: List[Tuple[int, int, int]] # (x, y, time) states
    path_length: int
    nodes_explored: int
    planning_time_ms: float
    wait_steps: int
    success: bool
    message: str = ""


class ReservationTable:
    """
    Shared time-space reservation table for multi-robot coordination.
    
    Stores:
      - vertex_reservations: {(x, y, t): robot_id}
      - edge_reservations: {(x1,y1,x2,y2,t): robot_id}  (for swap conflict)
    
    A vertex reservation means robot 'robot_id' will occupy cell (x,y) at time t.
    An edge reservation prevents two robots from swapping in one step.
    """
    
    def __init__(self):
        self.vertex_reservations: Dict[Tuple[int, int, int], str] = {}
        self.edge_reservations: Dict[Tuple[int, int, int, int, int], str] = {}
    
    def is_vertex_free(self, x: int, y: int, t: int, robot_id: str) -> bool:
        """Check if cell (x,y) at time t is unoccupied by any other robot."""
        key = (x, y, t)
        occupant = self.vertex_reservations.get(key)
        return occupant is None or occupant == robot_id
    
    def is_edge_free(self, x1: int, y1: int, x2: int, y2: int, t: int, robot_id: str) -> bool:
        """
        Check for edge-swap collision.
        An edge swap occurs when robot A moves from cell1 to cell2
        at the same time robot B moves from cell2 to cell1.
        We represent this as the undirected edge between the two positions.
        """
        key1 = (x1, y1, x2, y2, t)
        key2 = (x2, y2, x1, y1, t)
        occ1 = self.edge_reservations.get(key1)
        occ2 = self.edge_reservations.get(key2)
        return (occ1 is None or occ1 == robot_id) and (occ2 is None or occ2 == robot_id)
    
    def reserve_path(self, time_path: List[Tuple[int, int, int]], robot_id: str):
        """
        Reserve all vertex and edge positions for a planned path.
        
        Args:
            time_path: List of (x, y, t) states
            robot_id: Identifier of the robot claiming these cells
        """
        for state in time_path:
            x, y, t = state
            self.vertex_reservations[(x, y, t)] = robot_id
        
        # Reserve edges (to prevent swap collisions)
        for i in range(len(time_path) - 1):
            x1, y1, t1 = time_path[i]
            x2, y2, t2 = time_path[i + 1]
            if (x1, y1) != (x2, y2):  # only for actual moves (not waits)
                self.edge_reservations[(x1, y1, x2, y2, t1)] = robot_id
    
    def clear_robot_reservations(self, robot_id: str):
        """Remove all reservations for a specific robot (used during replanning)."""
        self.vertex_reservations = {
            k: v for k, v in self.vertex_reservations.items() if v != robot_id
        }
        self.edge_reservations = {
            k: v for k, v in self.edge_reservations.items() if v != robot_id
        }
    
    def clear_all(self):
        """Clear the entire reservation table."""
        self.vertex_reservations.clear()
        self.edge_reservations.clear()
    
    def get_snapshot(self) -> Dict:
        """Return a serializable snapshot for visualization."""
        vertex_snap = {}
        for (x, y, t), robot_id in self.vertex_reservations.items():
            key = f"{t}"
            if key not in vertex_snap:
                vertex_snap[key] = []
            vertex_snap[key].append({"x": x, "y": y, "robot_id": robot_id})
        return {"vertex_reservations": vertex_snap}


def cooperative_astar(
    robot_id: str,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    start_time: int,
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
    reservation_table: ReservationTable,
    max_time: int = 200,
) -> CAStarResult:
    """
    Cooperative A* for a single robot, respecting existing reservations.
    
    State space: (x, y, t) — time-aware nodes
    This allows the algorithm to find paths where waiting is optimal.
    
    Args:
        robot_id: Unique robot identifier
        start: Starting (x, y) position
        goal: Target (x, y) position
        start_time: Current simulation time step
        grid_width, grid_height: Warehouse dimensions
        obstacles: Fixed obstacle positions
        reservation_table: Shared table of reserved cells
        max_time: Maximum time horizon for planning
    
    Returns:
        CAStarResult with time-annotated path
    """
    t0 = time.perf_counter()
    
    if start == goal:
        elapsed = (time.perf_counter() - t0) * 1000
        time_path = [(start[0], start[1], start_time)]
        return CAStarResult(
            robot_id=robot_id, path=[start], time_path=time_path,
            path_length=0, nodes_explored=0, planning_time_ms=elapsed,
            wait_steps=0, success=True, message="Already at goal"
        )
    
    # Priority queue: (f_score, tie_break, state=(x,y,t))
    open_heap: List[Tuple[int, int, Tuple[int, int, int]]] = []
    counter = 0
    
    start_state = (start[0], start[1], start_time)
    
    # g_score for time-space states
    g_score: Dict[Tuple[int, int, int], int] = {start_state: 0}
    h_start = manhattan_distance(start, goal)
    heapq.heappush(open_heap, (h_start, counter, start_state))
    counter += 1
    
    came_from: Dict[Tuple[int, int, int], Optional[Tuple[int, int, int]]] = {
        start_state: None
    }
    closed_set: Set[Tuple[int, int, int]] = set()
    
    # 4 directions + wait (stay in place)
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0), (0, 0)]  # last = wait
    nodes_explored = 0
    wait_steps = 0
    
    while open_heap:
        f_cur, _, current_state = heapq.heappop(open_heap)
        
        if current_state in closed_set:
            continue
        
        closed_set.add(current_state)
        nodes_explored += 1
        
        cx, cy, ct = current_state
        
        # Goal check: reached goal position (any time step)
        if (cx, cy) == goal:
            path_states = _reconstruct_time_path(came_from, current_state)
            # Count wait steps (where position didn't change)
            waits = sum(
                1 for i in range(1, len(path_states))
                if (path_states[i][0], path_states[i][1]) == (path_states[i-1][0], path_states[i-1][1])
            )
            spatial_path = [(s[0], s[1]) for s in path_states]
            # Deduplicate consecutive same positions for display
            display_path = [spatial_path[0]]
            for pos in spatial_path[1:]:
                if pos != display_path[-1]:
                    display_path.append(pos)
            
            elapsed = (time.perf_counter() - t0) * 1000
            return CAStarResult(
                robot_id=robot_id,
                path=display_path,
                time_path=path_states,
                path_length=len(display_path) - 1,
                nodes_explored=nodes_explored,
                planning_time_ms=elapsed,
                wait_steps=waits,
                success=True,
                message=f"CA* path found: {len(display_path)-1} steps, {waits} waits"
            )
        
        # Time horizon guard
        if ct >= start_time + max_time:
            continue
        
        for dx, dy in directions:
            nx, ny, nt = cx + dx, cy + dy, ct + 1
            next_state = (nx, ny, nt)
            
            # Bounds check (waits are always in bounds)
            if dx != 0 or dy != 0:
                if not (0 <= nx < grid_width and 0 <= ny < grid_height):
                    continue
                # Obstacle check
                if (nx, ny) in obstacles:
                    continue
            
            if next_state in closed_set:
                continue
            
            # Reservation table: vertex conflict check
            if not reservation_table.is_vertex_free(nx, ny, nt, robot_id):
                continue
            
            # Reservation table: edge-swap conflict check
            if (dx != 0 or dy != 0):
                if not reservation_table.is_edge_free(cx, cy, nx, ny, ct, robot_id):
                    continue
            
            tentative_g = g_score[current_state] + 1
            if tentative_g < g_score.get(next_state, float('inf')):
                came_from[next_state] = current_state
                g_score[next_state] = tentative_g
                h_n = manhattan_distance((nx, ny), goal)
                f_n = tentative_g + h_n
                heapq.heappush(open_heap, (f_n, counter, next_state))
                counter += 1
    
    elapsed = (time.perf_counter() - t0) * 1000
    return CAStarResult(
        robot_id=robot_id, path=[], time_path=[],
        path_length=0, nodes_explored=nodes_explored,
        planning_time_ms=elapsed, wait_steps=0,
        success=False,
        message="No collision-free path found within time horizon"
    )


def _reconstruct_time_path(
    came_from: Dict[Tuple[int, int, int], Optional[Tuple[int, int, int]]],
    current: Tuple[int, int, int]
) -> List[Tuple[int, int, int]]:
    """Reconstruct the time-space path from goal back to start."""
    path = []
    node: Optional[Tuple[int, int, int]] = current
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path


def plan_all_robots(
    robot_plans: List[Dict],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
    reservation_table: ReservationTable,
    current_time: int = 0,
) -> List[CAStarResult]:
    """
    Plan paths for all robots cooperatively using priority-based CA*.
    
    Robots are planned in order. Each robot's plan is reserved before
    the next robot plans, ensuring conflict-free coordination.
    
    Args:
        robot_plans: List of dicts with keys: robot_id, start, goal
        grid_width, grid_height: Grid dimensions
        obstacles: Fixed obstacle set
        reservation_table: Shared reservation table
        current_time: Current simulation time step
    
    Returns:
        List of CAStarResult, one per robot
    """
    results = []
    
    for plan_info in robot_plans:
        robot_id = plan_info["robot_id"]
        start = tuple(plan_info["start"])
        goal = tuple(plan_info["goal"])
        
        # Clear this robot's old reservations before replanning
        reservation_table.clear_robot_reservations(robot_id)
        
        result = cooperative_astar(
            robot_id=robot_id,
            start=start,
            goal=goal,
            start_time=current_time,
            grid_width=grid_width,
            grid_height=grid_height,
            obstacles=obstacles,
            reservation_table=reservation_table,
        )
        
        # Reserve the planned path (even if it's just the current position)
        if result.success and result.time_path:
            reservation_table.reserve_path(result.time_path, robot_id)
        elif not result.success:
            # Reserve current position to block others from occupying it
            reservation_table.reserve_path(
                [(start[0], start[1], t) for t in range(current_time, current_time + 5)],
                robot_id
            )
        
        results.append(result)
    
    return results
