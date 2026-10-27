"""
Pydantic Schemas for API Validation
=====================================
Data models for all API requests and WebSocket messages.
"""

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field


class Position(BaseModel):
    x: int
    y: int


class RobotSchema(BaseModel):
    robot_id: str
    position: List[int]
    color: str
    state: str
    task_id: Optional[str] = None
    package_id: Optional[str] = None
    pickup_target: Optional[List[int]] = None
    delivery_target: Optional[List[int]] = None
    has_package: bool = False
    path: List[List[int]] = []
    distance_traveled: int = 0
    tasks_completed: int = 0
    wait_steps: int = 0
    total_steps: int = 0
    replan_count: int = 0
    stuck_steps: int = 0
    backtrack_count: int = 0
    decision_stack: List[Dict] = []


class PackageSchema(BaseModel):
    package_id: str
    location: List[int]
    delivery_station: List[int]
    status: str  # WAITING, ASSIGNED, PICKED_UP, DELIVERED
    assigned_robot: Optional[str] = None


class TaskSchema(BaseModel):
    task_id: str
    package_id: str
    pickup_location: List[int]
    delivery_station: List[int]
    priority: int = 1
    status: str  # PENDING, ASSIGNED, IN_PROGRESS, COMPLETED
    assigned_robot: Optional[str] = None
    estimated_cost: float = 0.0
    creation_time: int = 0
    completion_time: Optional[int] = None


class StatisticsSchema(BaseModel):
    total_distance: int = 0
    completed_deliveries: int = 0
    pending_deliveries: int = 0
    total_planning_time_ms: float = 0.0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    average_delivery_steps: float = 0.0
    total_waiting_steps: int = 0
    nodes_explored: int = 0
    replan_count: int = 0
    simulation_step: int = 0
    search_nodes: int = 0
    branches_pruned: int = 0
    search_backtracks: int = 0
    allocation_cost_saved: float = 0.0
    ordering_resolutions: int = 0
    agent_backtracks: int = 0
    deadlocks_resolved: int = 0


class EventLogEntry(BaseModel):
    timestamp: str
    event_type: str
    message: str
    robot_id: Optional[str] = None
    package_id: Optional[str] = None
    rule_id: Optional[str] = None
    step: int = 0


class WarehouseStateSchema(BaseModel):
    grid_width: int
    grid_height: int
    obstacles: List[List[int]]
    shelves: List[List[int]]
    pickup_locations: List[List[int]]
    delivery_stations: List[List[int]]
    charging_stations: List[List[int]]
    robots: List[RobotSchema]
    packages: List[PackageSchema]
    tasks: List[TaskSchema]
    statistics: StatisticsSchema
    simulation_step: int
    is_running: bool
    speed: float
    active_algorithm: str
    event_logs: List[EventLogEntry]


class SimulationControlRequest(BaseModel):
    action: str  # start, pause, reset, step, speed
    speed: Optional[float] = None


class AddRobotRequest(BaseModel):
    position: List[int]


class AddPackageRequest(BaseModel):
    pickup_location: List[int]
    delivery_station: List[int]
    priority: int = 1


class AddObstacleRequest(BaseModel):
    position: List[int]


class RemoveObstacleRequest(BaseModel):
    position: List[int]


class RemoveRobotRequest(BaseModel):
    robot_id: str


class AStarRequest(BaseModel):
    start: List[int]
    goal: List[int]
    include_visualization: bool = False


class AStarResponse(BaseModel):
    success: bool
    path: List[List[int]]
    path_length: int
    nodes_explored: int
    planning_time_ms: float
    message: str = ""
    steps: Optional[List[Dict]] = None
    g_scores: Optional[Dict] = None
    h_scores: Optional[Dict] = None


class AlgorithmComparisonResponse(BaseModel):
    astar: AStarResponse
    bfs: AStarResponse
    comparison: Dict


class ScenarioRequest(BaseModel):
    scenario_id: str  # "basic_delivery", "collision_avoidance", "dynamic_obstacle"
