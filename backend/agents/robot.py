"""
Robot Agent and State Machine
================================
Autonomous robot agent with finite-state machine (FSM) control.

State Machine Transitions:
  IDLE → ASSIGNED → MOVING_TO_PICKUP → PICKING_UP → MOVING_TO_DELIVERY → DELIVERING → IDLE
  
  Any state → WAITING (when blocked by another robot)
  Any state → REPLANNING (when path is invalidated)
  Any state → BLOCKED (when no path can be found)

Each robot is a goal-based autonomous agent:
  - It has sensors (reads world state)
  - It has actuators (moves, picks up, delivers)
  - It has goals (complete assigned delivery tasks)
  - It uses classical AI (A*, rule engine) to select actions
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class RobotState(str, Enum):
    """Valid states in the robot finite-state machine."""
    IDLE = "IDLE"
    ASSIGNED = "ASSIGNED"
    MOVING_TO_PICKUP = "MOVING_TO_PICKUP"
    PICKING_UP = "PICKING_UP"
    MOVING_TO_DELIVERY = "MOVING_TO_DELIVERY"
    DELIVERING = "DELIVERING"
    WAITING = "WAITING"
    REPLANNING = "REPLANNING"
    BLOCKED = "BLOCKED"


# Valid state transitions (FSM transition table)
VALID_TRANSITIONS: Dict[RobotState, List[RobotState]] = {
    RobotState.IDLE: [RobotState.ASSIGNED],
    RobotState.ASSIGNED: [RobotState.MOVING_TO_PICKUP, RobotState.IDLE],
    RobotState.MOVING_TO_PICKUP: [
        RobotState.PICKING_UP,
        RobotState.WAITING,
        RobotState.REPLANNING,
        RobotState.BLOCKED,
        RobotState.IDLE,
    ],
    RobotState.PICKING_UP: [RobotState.MOVING_TO_DELIVERY, RobotState.WAITING],
    RobotState.MOVING_TO_DELIVERY: [
        RobotState.DELIVERING,
        RobotState.WAITING,
        RobotState.REPLANNING,
        RobotState.BLOCKED,
        RobotState.IDLE,
    ],
    RobotState.DELIVERING: [RobotState.IDLE],
    RobotState.WAITING: [
        RobotState.MOVING_TO_PICKUP,
        RobotState.MOVING_TO_DELIVERY,
        RobotState.REPLANNING,
        RobotState.IDLE,
    ],
    RobotState.REPLANNING: [
        RobotState.MOVING_TO_PICKUP,
        RobotState.MOVING_TO_DELIVERY,
        RobotState.BLOCKED,
        RobotState.IDLE,
    ],
    RobotState.BLOCKED: [RobotState.REPLANNING, RobotState.IDLE],
}

# Robot colors for visualization (R1=blue, R2=orange, R3=green, R4=purple, R5=red)
ROBOT_COLORS = [
    "#3B82F6",  # Blue  (R1)
    "#F97316",  # Orange (R2)
    "#22C55E",  # Green  (R3)
    "#A855F7",  # Purple (R4)
    "#EF4444",  # Red    (R5)
    "#06B6D4",  # Cyan   (R6)
    "#EAB308",  # Yellow (R7)
    "#EC4899",  # Pink   (R8)
]


@dataclass
class Robot:
    """
    Autonomous warehouse robot agent.
    
    Implements goal-based agent architecture:
    - Perception: reads grid state
    - Goal: deliver assigned package
    - Planning: A* + Cooperative A*
    - Action: move, pick up, deliver
    """
    robot_id: str
    position: Tuple[int, int]          # Current (col, row) position
    color: str = "#3B82F6"
    
    # FSM state
    state: RobotState = RobotState.IDLE
    
    # Task information
    task_id: Optional[str] = None
    package_id: Optional[str] = None
    pickup_target: Optional[Tuple[int, int]] = None
    delivery_target: Optional[Tuple[int, int]] = None
    has_package: bool = False
    
    # Navigation
    path: List[Tuple[int, int]] = field(default_factory=list)
    time_path: List[Tuple[int, int, int]] = field(default_factory=list)
    
    # Statistics
    distance_traveled: int = 0
    tasks_completed: int = 0
    wait_steps: int = 0
    total_steps: int = 0
    replan_count: int = 0
    
    # Metadata
    color_index: int = 0
    
    def transition_to(self, new_state: RobotState) -> bool:
        """
        Attempt a state transition. Returns True if valid, False if invalid.
        Enforces the FSM transition rules.
        """
        allowed = VALID_TRANSITIONS.get(self.state, [])
        if new_state in allowed:
            self.state = new_state
            return True
        return False
    
    def force_state(self, new_state: RobotState):
        """Force a state change (used during resets and initialization)."""
        self.state = new_state
    
    def assign_task(self, task_id: str, package_id: str,
                    pickup: Tuple[int, int], delivery: Tuple[int, int]) -> bool:
        """Assign a delivery task to this robot."""
        if self.state != RobotState.IDLE:
            return False
        self.task_id = task_id
        self.package_id = package_id
        self.pickup_target = pickup
        self.delivery_target = delivery
        self.has_package = False
        self.path = []
        self.time_path = []
        self.transition_to(RobotState.ASSIGNED)
        return True
    
    def set_path(self, path: List[Tuple[int, int]],
                 time_path: List[Tuple[int, int, int]] = None):
        """Update the robot's planned navigation path."""
        self.path = path[1:] if path and path[0] == self.position else path
        self.time_path = time_path or []
    
    def get_next_position(self) -> Optional[Tuple[int, int]]:
        """Get the next step in the planned path, if any."""
        if self.path:
            return self.path[0]
        return None
    
    def advance_position(self) -> bool:
        """
        Move robot to the next cell in the path.
        Returns True if moved, False if no path.
        """
        if self.path:
            next_pos = self.path.pop(0)
            self.position = next_pos
            self.distance_traveled += 1
            self.total_steps += 1
            return True
        self.total_steps += 1
        return False
    
    def pick_up_package(self) -> bool:
        """Robot picks up a package at its current position."""
        if self.position == self.pickup_target and not self.has_package:
            self.has_package = True
            self.path = []
            self.time_path = []
            return True
        return False
    
    def deliver_package(self) -> Optional[str]:
        """
        Robot delivers the package at the current position.
        Returns the package_id if successful, None otherwise.
        """
        if (self.position == self.delivery_target and
                self.has_package and self.package_id):
            delivered_pkg = self.package_id
            self.has_package = False
            self.package_id = None
            self.task_id = None
            self.pickup_target = None
            self.delivery_target = None
            self.path = []
            self.time_path = []
            self.tasks_completed += 1
            self.transition_to(RobotState.IDLE)
            return delivered_pkg
        return None
    
    def clear_task(self):
        """Reset all task-related fields."""
        self.task_id = None
        self.package_id = None
        self.pickup_target = None
        self.delivery_target = None
        self.has_package = False
        self.path = []
        self.time_path = []
    
    def build_rule_state(self, pending_tasks_exist: bool, package_available: bool,
                         next_cell_blocked: bool = False,
                         blocking_robot: Optional[str] = None,
                         obstacle_in_path: bool = False,
                         obstacle_position: Optional[Tuple[int, int]] = None) -> Dict:
        """
        Build the state dictionary used by the rule engine.
        This is the robot's "percept" — what it can observe.
        """
        return {
            "robot_id": self.robot_id,
            "state": self.state.value,
            "position": self.position,
            "has_package": self.has_package,
            "path": list(self.path),
            "task_id": self.task_id,
            "package_id": self.package_id,
            "pickup_target": self.pickup_target,
            "delivery_target": self.delivery_target,
            "pending_tasks_exist": pending_tasks_exist,
            "package_available": package_available,
            "next_cell_blocked": next_cell_blocked,
            "blocking_robot": blocking_robot,
            "obstacle_in_path": obstacle_in_path,
            "obstacle_position": obstacle_position,
        }
    
    def to_dict(self) -> Dict:
        """Serialize robot state for WebSocket broadcast."""
        return {
            "robot_id": self.robot_id,
            "position": list(self.position),
            "color": self.color,
            "state": self.state.value,
            "task_id": self.task_id,
            "package_id": self.package_id,
            "pickup_target": list(self.pickup_target) if self.pickup_target else None,
            "delivery_target": list(self.delivery_target) if self.delivery_target else None,
            "has_package": self.has_package,
            "path": [list(p) for p in self.path],
            "distance_traveled": self.distance_traveled,
            "tasks_completed": self.tasks_completed,
            "wait_steps": self.wait_steps,
            "total_steps": self.total_steps,
            "replan_count": self.replan_count,
        }


def create_robot(robot_id: str, position: Tuple[int, int], color_index: int = 0) -> Robot:
    """Factory function to create a new robot with the correct color."""
    color = ROBOT_COLORS[color_index % len(ROBOT_COLORS)]
    return Robot(
        robot_id=robot_id,
        position=position,
        color=color,
        color_index=color_index,
    )
