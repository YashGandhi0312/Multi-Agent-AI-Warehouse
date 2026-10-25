"""
A* Search Algorithm Implementation
===================================
Classical AI pathfinding for warehouse robot navigation.

Algorithm: A* Search
Time Complexity: O(b^d) where b is branching factor, d is depth
Space Complexity: O(b^d)
Heuristic: Manhattan Distance (admissible for 4-directional grid movement)

f(n) = g(n) + h(n)
  g(n) = actual cost from start to node n
  h(n) = estimated cost from node n to goal (Manhattan distance)
  f(n) = estimated total path cost through n
"""

import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class AStarResult:
    """Result of an A* search."""
    path: List[Tuple[int, int]]
    path_length: int
    nodes_explored: int
    planning_time_ms: float
    success: bool
    message: str = ""


def manhattan_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """
    Manhattan distance heuristic.
    Admissible for 4-directional grid movement (never overestimates).
    h(n) = |x_goal - x_current| + |y_goal - y_current|
    """
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def astar_search(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
    reserved_cells: Optional[Set[Tuple[int, int]]] = None,
) -> AStarResult:
    """
    A* Search from scratch for single-robot pathfinding.
    
    Args:
        start: Starting position (col, row)
        goal: Target position (col, row)
        grid_width: Width of the warehouse grid
        grid_height: Height of the warehouse grid
        obstacles: Set of blocked cell positions
        reserved_cells: Optional additional cells to treat as blocked
    
    Returns:
        AStarResult containing path, statistics, and success status
    """
    start_time = time.perf_counter()
    blocked = obstacles | (reserved_cells or set())
    
    if start == goal:
        elapsed = (time.perf_counter() - start_time) * 1000
        return AStarResult(
            path=[start],
            path_length=0,
            nodes_explored=0,
            planning_time_ms=elapsed,
            success=True,
            message="Already at goal"
        )
    
    if start in blocked:
        elapsed = (time.perf_counter() - start_time) * 1000
        return AStarResult(
            path=[],
            path_length=0,
            nodes_explored=0,
            planning_time_ms=elapsed,
            success=False,
            message="Start position is blocked"
        )
    
    if goal in blocked:
        elapsed = (time.perf_counter() - start_time) * 1000
        return AStarResult(
            path=[],
            path_length=0,
            nodes_explored=0,
            planning_time_ms=elapsed,
            success=False,
            message="Goal position is blocked"
        )
    
    # Priority queue: (f_score, tie_breaker, node)
    open_heap: List[Tuple[int, int, Tuple[int, int]]] = []
    counter = 0  # tie-breaker for equal f-scores
    
    # g_score[n] = cost of cheapest known path from start to n
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    
    # f_score[n] = g_score[n] + h(n)
    h_start = manhattan_distance(start, goal)
    heapq.heappush(open_heap, (h_start, counter, start))
    counter += 1
    
    # For path reconstruction: came_from[n] = predecessor of n on cheapest path
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    
    # Closed set: nodes already evaluated
    closed_set: Set[Tuple[int, int]] = set()
    
    # 4-directional movement: up, down, left, right
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    nodes_explored = 0
    
    while open_heap:
        f_current, _, current = heapq.heappop(open_heap)
        
        if current in closed_set:
            continue
        
        closed_set.add(current)
        nodes_explored += 1
        
        # Goal check
        if current == goal:
            path = _reconstruct_path(came_from, current)
            elapsed = (time.perf_counter() - start_time) * 1000
            return AStarResult(
                path=path,
                path_length=len(path) - 1,
                nodes_explored=nodes_explored,
                planning_time_ms=elapsed,
                success=True,
                message=f"Path found: {len(path)-1} steps"
            )
        
        # Expand neighbors
        cx, cy = current
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            neighbor = (nx, ny)
            
            # Bounds check
            if not (0 <= nx < grid_width and 0 <= ny < grid_height):
                continue
            
            # Obstacle check
            if neighbor in blocked:
                continue
            
            if neighbor in closed_set:
                continue
            
            # g_score for path through current to neighbor
            tentative_g = g_score[current] + 1
            
            if tentative_g < g_score.get(neighbor, float('inf')):
                # This path to neighbor is better than any previous one
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h_neighbor = manhattan_distance(neighbor, goal)
                f_neighbor = tentative_g + h_neighbor
                heapq.heappush(open_heap, (f_neighbor, counter, neighbor))
                counter += 1
    
    # No path found
    elapsed = (time.perf_counter() - start_time) * 1000
    return AStarResult(
        path=[],
        path_length=0,
        nodes_explored=nodes_explored,
        planning_time_ms=elapsed,
        success=False,
        message="No path exists — destination unreachable"
    )


def _reconstruct_path(
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]],
    current: Tuple[int, int]
) -> List[Tuple[int, int]]:
    """
    Reconstruct the path by backtracking from goal to start.
    Returns path from start to goal (inclusive).
    """
    path = []
    node: Optional[Tuple[int, int]] = current
    while node is not None:
        path.append(node)
        node = came_from[node]
    path.reverse()
    return path


def astar_with_visualization(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
) -> Dict:
    """
    A* Search with step-by-step visualization data.
    Returns each expansion step for the Algorithm Explorer UI.
    """
    start_time = time.perf_counter()
    
    open_heap: List[Tuple[int, int, int, Tuple[int, int]]] = []
    counter = 0
    g_score: Dict[Tuple[int, int], int] = {start: 0}
    h_start = manhattan_distance(start, goal)
    heapq.heappush(open_heap, (h_start, 0, counter, start))
    counter += 1
    
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    closed_set: Set[Tuple[int, int]] = set()
    
    steps = []
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    nodes_explored = 0
    
    # Track f, g, h scores for visualization
    f_scores: Dict[Tuple[int, int], float] = {start: float(h_start)}
    h_scores: Dict[Tuple[int, int], float] = {start: float(h_start)}
    
    open_set_nodes = {start}
    
    while open_heap:
        f_current, _, _, current = heapq.heappop(open_heap)
        
        if current in closed_set:
            continue
        
        open_set_nodes.discard(current)
        closed_set.add(current)
        nodes_explored += 1
        
        # Capture visualization step
        step_data = {
            "step": nodes_explored,
            "current": list(current),
            "open": [list(n) for n in open_set_nodes],
            "closed": [list(n) for n in closed_set],
            "g": g_score.get(current, 0),
            "h": h_scores.get(current, 0),
            "f": f_scores.get(current, 0),
        }
        steps.append(step_data)
        
        if current == goal:
            path = _reconstruct_path(came_from, current)
            elapsed = (time.perf_counter() - start_time) * 1000
            return {
                "success": True,
                "path": [list(p) for p in path],
                "path_length": len(path) - 1,
                "nodes_explored": nodes_explored,
                "planning_time_ms": elapsed,
                "steps": steps,
                "g_scores": {str(k): v for k, v in g_score.items()},
                "h_scores": {str(k): v for k, v in h_scores.items()},
            }
        
        cx, cy = current
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            neighbor = (nx, ny)
            
            if not (0 <= nx < grid_width and 0 <= ny < grid_height):
                continue
            if neighbor in obstacles or neighbor in closed_set:
                continue
            
            tentative_g = g_score[current] + 1
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h_n = manhattan_distance(neighbor, goal)
                f_n = tentative_g + h_n
                f_scores[neighbor] = float(f_n)
                h_scores[neighbor] = float(h_n)
                heapq.heappush(open_heap, (f_n, 0, counter, neighbor))
                counter += 1
                open_set_nodes.add(neighbor)
    
    elapsed = (time.perf_counter() - start_time) * 1000
    return {
        "success": False,
        "path": [],
        "path_length": 0,
        "nodes_explored": nodes_explored,
        "planning_time_ms": elapsed,
        "steps": steps,
        "g_scores": {},
        "h_scores": {},
    }


def bfs_search(
    start: Tuple[int, int],
    goal: Tuple[int, int],
    grid_width: int,
    grid_height: int,
    obstacles: Set[Tuple[int, int]],
) -> AStarResult:
    """
    Breadth-First Search for comparison with A* in analytics.
    BFS finds shortest path on unweighted graphs (like A* with h=0).
    Used for educational comparison only.
    """
    from collections import deque
    
    start_time = time.perf_counter()
    
    if start == goal:
        elapsed = (time.perf_counter() - start_time) * 1000
        return AStarResult(path=[start], path_length=0, nodes_explored=0,
                           planning_time_ms=elapsed, success=True)
    
    queue = deque([start])
    came_from: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    nodes_explored = 0
    
    while queue:
        current = queue.popleft()
        nodes_explored += 1
        
        if current == goal:
            path = _reconstruct_path(came_from, current)
            elapsed = (time.perf_counter() - start_time) * 1000
            return AStarResult(
                path=path, path_length=len(path) - 1,
                nodes_explored=nodes_explored,
                planning_time_ms=elapsed, success=True,
                message=f"BFS path found: {len(path)-1} steps"
            )
        
        cx, cy = current
        for dx, dy in directions:
            nx, ny = cx + dx, cy + dy
            neighbor = (nx, ny)
            if not (0 <= nx < grid_width and 0 <= ny < grid_height):
                continue
            if neighbor in obstacles or neighbor in came_from:
                continue
            came_from[neighbor] = current
            queue.append(neighbor)
    
    elapsed = (time.perf_counter() - start_time) * 1000
    return AStarResult(path=[], path_length=0, nodes_explored=nodes_explored,
                       planning_time_ms=elapsed, success=False,
                       message="BFS: No path found")
