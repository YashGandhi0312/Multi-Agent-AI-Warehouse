"""
FastAPI Backend — Main Application Entry Point
================================================
Multi-Agent AI Warehouse Management System
Classical AI: A*, Cooperative A*, Rule-Based Reasoning, Task Allocation

Endpoints:
  GET  /api/state              — Get full simulation state
  POST /api/simulation/control — Start/pause/reset/step
  POST /api/simulation/speed   — Change speed
  POST /api/robot/add          — Add a robot
  POST /api/robot/remove       — Remove a robot
  POST /api/package/add        — Add a package
  POST /api/obstacle/add       — Add obstacle
  POST /api/obstacle/remove    — Remove obstacle
  POST /api/scenario/{id}      — Load a demo scenario
  POST /api/astar              — Run A* search (with optional visualization)
  POST /api/compare            — Compare A* vs BFS
  GET  /api/rules              — List all IF-THEN rules
  GET  /api/cost-matrix        — Task allocation cost matrix
  WS   /ws                     — WebSocket for real-time updates
"""

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from algorithms.astar import astar_search, astar_with_visualization, bfs_search
from algorithms.task_allocation import build_cost_matrix
from models.schemas import (
    AddObstacleRequest, AddPackageRequest, AddRobotRequest,
    RemoveObstacleRequest, RemoveRobotRequest,
    AStarRequest, SimulationControlRequest, ScenarioRequest,
)
from simulation.simulation_engine import SimulationEngine, get_engine
from simulation.warehouse import create_scenario_warehouse
from agents.robot import create_robot


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket Connection Manager
# ─────────────────────────────────────────────────────────────────────────────

class ConnectionManager:
    """Manages active WebSocket connections for real-time state broadcast."""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def broadcast(self, data: Dict):
        message = json.dumps(data, default=str)
        dead = []
        for ws in self.active_connections:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active_connections.remove(ws)


manager = ConnectionManager()
engine: Optional[SimulationEngine] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize the simulation engine on startup."""
    global engine
    engine = get_engine()
    
    async def broadcast_callback(state: Dict):
        await manager.broadcast(state)
    
    engine.set_broadcast_callback(broadcast_callback)
    yield
    # Cleanup
    if engine.is_running:
        await engine.pause()


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Application
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Multi-Agent AI Warehouse Management System",
    description="Classical AI: A*, Cooperative A*, Rule-Based Reasoning, Task Allocation",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────────────────
# REST API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/api/state")
async def get_state():
    """Return the full current simulation state."""
    return engine.get_full_state()


@app.post("/api/simulation/control")
async def control_simulation(request: SimulationControlRequest):
    """Control simulation playback: start, pause, reset, step."""
    action = request.action.lower()
    
    if action == "start":
        await engine.start()
        return {"status": "started", "step": engine.simulation_step}
    
    elif action == "pause":
        await engine.pause()
        return {"status": "paused", "step": engine.simulation_step}
    
    elif action == "reset":
        await engine.reset()
        return {"status": "reset", "step": 0}
    
    elif action == "step":
        was_running = engine.is_running
        if was_running:
            await engine.pause()
        await engine.step_once()
        return {"status": "stepped", "step": engine.simulation_step}
    
    raise HTTPException(status_code=400, detail=f"Unknown action: {action}")


@app.post("/api/simulation/speed")
async def set_speed(body: dict):
    """Set simulation speed."""
    speed = float(body.get("speed", 1.0))
    engine.set_speed(speed)
    return {"status": "ok", "speed": engine.speed}


@app.post("/api/robot/add")
async def add_robot(request: AddRobotRequest):
    """Add a robot at the specified position."""
    pos = tuple(request.position)
    robot_id = engine.add_robot(pos)
    if robot_id is None:
        raise HTTPException(status_code=400, detail="Invalid position or already occupied")
    state = engine.get_full_state()
    await manager.broadcast(state)
    return {"status": "ok", "robot_id": robot_id}


@app.post("/api/robot/remove")
async def remove_robot(request: RemoveRobotRequest):
    """Remove a robot from the simulation."""
    success = engine.remove_robot(request.robot_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Robot {request.robot_id} not found")
    state = engine.get_full_state()
    await manager.broadcast(state)
    return {"status": "ok"}


@app.post("/api/package/add")
async def add_package(request: AddPackageRequest):
    """Add a new package with a delivery task."""
    pickup = tuple(request.pickup_location)
    delivery = tuple(request.delivery_station)
    pkg_id = engine.add_package(pickup, delivery, request.priority)
    if pkg_id is None:
        raise HTTPException(status_code=400, detail="Invalid pickup or delivery position")
    
    # Create task for the package
    # Task creation happens inside add_package now
    state = engine.get_full_state()
    await manager.broadcast(state)
    return {"status": "ok", "package_id": pkg_id}


@app.post("/api/obstacle/add")
async def add_obstacle(request: AddObstacleRequest):
    """Add a dynamic obstacle and trigger replanning."""
    pos = tuple(request.position)
    success = engine.add_obstacle(pos)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot add obstacle at that position")
    state = engine.get_full_state()
    await manager.broadcast(state)
    return {"status": "ok", "position": request.position}


@app.post("/api/obstacle/remove")
async def remove_obstacle(request: RemoveObstacleRequest):
    """Remove a dynamic obstacle."""
    pos = tuple(request.position)
    success = engine.remove_obstacle(pos)
    if not success:
        raise HTTPException(status_code=400, detail="No obstacle at that position")
    state = engine.get_full_state()
    await manager.broadcast(state)
    return {"status": "ok"}


@app.post("/api/scenario/{scenario_id}")
async def load_scenario(scenario_id: str):
    """Load a predefined demonstration scenario."""
    valid_scenarios = ["basic_delivery", "collision_avoidance", "dynamic_obstacle", "default"]
    if scenario_id not in valid_scenarios:
        raise HTTPException(status_code=400, detail=f"Unknown scenario: {scenario_id}")
    
    # Pause first
    await engine.pause()
    
    # Build scenario warehouse
    from simulation.warehouse import create_scenario_warehouse, create_default_warehouse
    
    if scenario_id == "default":
        engine.warehouse = create_default_warehouse()
        robot_starts = [(1, 1), (1, 3), (18, 1), (18, 3), (9, 1)]
        robot_ids = ["R1", "R2", "R3", "R4", "R5"]
    else:
        w, robot_starts = create_scenario_warehouse(scenario_id)
        engine.warehouse = w
        n = len(robot_starts)
        robot_ids = [f"R{i+1}" for i in range(n)]
    
    # Reset robots and tasks
    engine.robots.clear()
    engine.tasks.clear()
    engine.statistics.__init__()
    engine.reservation_table.clear_all()
    engine.simulation_step = 0
    engine.event_log.clear()
    engine._task_start_steps.clear()
    engine.nogoods.clear()
    engine.deferred_tasks.clear()
    engine.last_allocation_search = None
    engine.last_ordering_search = None
    engine._robot_counter = len(robot_ids) + 1
    engine._task_counter = 1
    engine._package_counter = 20
    
    for i, (robot_id, pos) in enumerate(zip(robot_ids, robot_starts)):
        if engine.warehouse.is_traversable(pos):
            robot = create_robot(robot_id, pos, i)
            engine.robots[robot_id] = robot
    
    engine.load_initial_tasks()
    
    engine.event_log.log(
        "SCENARIO_LOADED",
        f"Scenario '{scenario_id}' loaded with {len(engine.robots)} robots "
        f"and {len(engine.tasks)} tasks.",
        step=0,
    )
    
    state = engine.get_full_state()
    await manager.broadcast(state)
    return {"status": "ok", "scenario": scenario_id}


@app.post("/api/astar")
async def run_astar(request: AStarRequest):
    """
    Run A* Search (or with step-by-step visualization).
    Used by the Algorithm Explorer tab.
    """
    start = tuple(request.start)
    goal = tuple(request.goal)
    obstacles = engine.warehouse.get_all_obstacles()
    
    if request.include_visualization:
        result = astar_with_visualization(
            start, goal,
            engine.warehouse.grid_width,
            engine.warehouse.grid_height,
            obstacles,
        )
        return result
    else:
        result = astar_search(
            start, goal,
            engine.warehouse.grid_width,
            engine.warehouse.grid_height,
            obstacles,
        )
        return {
            "success": result.success,
            "path": [list(p) for p in result.path],
            "path_length": result.path_length,
            "nodes_explored": result.nodes_explored,
            "planning_time_ms": result.planning_time_ms,
            "message": result.message,
        }


@app.post("/api/compare")
async def compare_algorithms(request: AStarRequest):
    """
    Compare A* vs BFS on the same query.
    Used by the Analytics dashboard for educational comparison.
    """
    start = tuple(request.start)
    goal = tuple(request.goal)
    obstacles = engine.warehouse.get_all_obstacles()
    
    astar_result = astar_search(
        start, goal,
        engine.warehouse.grid_width,
        engine.warehouse.grid_height,
        obstacles,
    )
    bfs_result = bfs_search(
        start, goal,
        engine.warehouse.grid_width,
        engine.warehouse.grid_height,
        obstacles,
    )
    
    comparison = {
        "astar_faster": astar_result.planning_time_ms < bfs_result.planning_time_ms,
        "same_path_length": astar_result.path_length == bfs_result.path_length,
        "astar_nodes_explored": astar_result.nodes_explored,
        "bfs_nodes_explored": bfs_result.nodes_explored,
        "note": (
            "On unweighted grids, both A* and BFS find optimal shortest paths. "
            "A* typically explores fewer nodes due to its heuristic guidance, "
            "making it faster for large grids or long paths."
        )
    }
    
    return {
        "astar": {
            "success": astar_result.success,
            "path": [list(p) for p in astar_result.path],
            "path_length": astar_result.path_length,
            "nodes_explored": astar_result.nodes_explored,
            "planning_time_ms": astar_result.planning_time_ms,
            "message": astar_result.message,
        },
        "bfs": {
            "success": bfs_result.success,
            "path": [list(p) for p in bfs_result.path],
            "path_length": bfs_result.path_length,
            "nodes_explored": bfs_result.nodes_explored,
            "planning_time_ms": bfs_result.planning_time_ms,
            "message": bfs_result.message,
        },
        "comparison": comparison,
    }


@app.get("/api/rules")
async def get_rules():
    """Return all rule-engine IF-THEN rules for the UI."""
    return engine.rule_engine.get_rules_summary()


@app.get("/api/cost-matrix")
async def get_cost_matrix():
    """
    Return the robot × task cost matrix for the task allocation visualization.
    Shows why each assignment was made.
    """
    robot_ids = list(engine.robots.keys())
    robot_positions = {rid: r.position for rid, r in engine.robots.items()}
    tasks = [t for t in engine.tasks.values() if t.status != "COMPLETED"]
    
    matrix = build_cost_matrix(
        tasks,
        robot_positions,
        robot_ids,
        engine.warehouse.grid_width,
        engine.warehouse.grid_height,
        engine.warehouse.get_all_obstacles(),
    )
    return {"cost_matrix": matrix, "tasks": [t.task_id for t in tasks]}


@app.get("/api/backtracking")
async def get_backtracking():
    """
    Return the latest backtracking search reports (allocation branch & bound
    with its search-tree trace, priority-order search), active nogoods and
    each robot's decision stack.
    """
    state = engine.get_backtracking_state(include_trace=True)
    state["agents"] = [
        {
            "robot_id": r.robot_id,
            "state": r.state.value,
            "stuck_steps": r.stuck_steps,
            "backtrack_count": r.backtrack_count,
            "decision_stack": r.to_dict()["decision_stack"],
        }
        for r in engine.robots.values()
    ]
    return state


@app.get("/api/reservation-table")
async def get_reservation_table():
    """Return the current time-space reservation table snapshot."""
    return engine.reservation_table.get_snapshot()


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket Endpoint
# ─────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket connection for real-time state synchronization.
    On connect: sends the full current state.
    Client can send JSON control messages.
    """
    await manager.connect(websocket)
    try:
        # Send initial state on connection
        state = engine.get_full_state()
        await websocket.send_text(json.dumps(state, default=str))
        
        # Listen for client messages
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action", "")
                
                if action == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif action == "get_state":
                    state = engine.get_full_state()
                    await websocket.send_text(json.dumps(state, default=str))
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ─────────────────────────────────────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
