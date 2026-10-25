"""
Rule-Based Reasoning Engine
=============================
Classical AI decision-making using explicit IF-THEN rules.

This implements a simple forward-chaining rule engine. Rules are evaluated
in priority order. The first matching rule for each robot fires.

This is a classic symbolic AI approach — no learning, no probabilistic
inference. All decisions are deterministic and explainable.

Rule Structure:
  - Condition: A function that checks the current robot/world state
  - Action: What the robot should do when the condition is true
  - Priority: Determines evaluation order (higher = checked first)
  - Description: Human-readable explanation for the UI log
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


@dataclass
class Rule:
    """A single IF-THEN rule in the rule engine."""
    rule_id: str
    name: str
    condition: Callable[[Dict], bool]     # (world_state) → bool
    action: Callable[[Dict], Dict]        # (world_state) → action_dict
    priority: int = 0
    description: str = ""
    category: str = "GENERAL"


@dataclass  
class RuleFiringEvent:
    """Records when a rule fired for a robot — used in UI logs."""
    rule_id: str
    rule_name: str
    robot_id: str
    fired_at_time: int
    action: Dict
    description: str


class RuleEngine:
    """
    Forward-chaining rule engine for autonomous robot decision-making.
    
    Each simulation step, the engine evaluates all rules for each robot
    in priority order. The first matching rule fires its action.
    
    This is the "reasoning component" of each robot agent — it embodies
    the agent's goals and behavioral policies.
    """
    
    def __init__(self):
        self.rules: List[Rule] = []
        self._register_warehouse_rules()
    
    def _register_warehouse_rules(self):
        """Register all warehouse management rules in priority order."""
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 1 (Priority 100): Robot has package → go deliver it
        # IF robot is carrying package AND robot state is MOVING_TO_DELIVERY
        # THEN continue navigating toward delivery station
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R001",
            name="Continue Delivery Navigation",
            condition=lambda s: (
                s.get("state") == "MOVING_TO_DELIVERY" and
                s.get("has_package") and
                s.get("path") and len(s.get("path", [])) > 0
            ),
            action=lambda s: {
                "type": "MOVE",
                "next_position": s["path"][0] if s["path"] else s["position"],
                "reason": "Continuing delivery navigation"
            },
            priority=100,
            description="IF robot is carrying package THEN navigate to delivery station",
            category="NAVIGATION"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 2 (Priority 95): Robot reached delivery station
        # IF robot is at delivery station AND has package
        # THEN deliver the package
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R002",
            name="Deliver Package at Station",
            condition=lambda s: (
                s.get("has_package") and
                s.get("state") in ("MOVING_TO_DELIVERY", "DELIVERING") and
                s.get("position") == s.get("delivery_target")
            ),
            action=lambda s: {
                "type": "DELIVER",
                "package_id": s.get("package_id"),
                "station": s.get("position"),
                "reason": "Robot reached delivery station — delivering package"
            },
            priority=95,
            description="IF robot reaches delivery station THEN deliver package and complete task",
            category="DELIVERY"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 3 (Priority 90): Robot at pickup location
        # IF robot is at package location AND package is still there
        # THEN pick up the package
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R003",
            name="Pick Up Package",
            condition=lambda s: (
                not s.get("has_package") and
                s.get("state") in ("MOVING_TO_PICKUP", "PICKING_UP") and
                s.get("position") == s.get("pickup_target") and
                s.get("package_available", False)
            ),
            action=lambda s: {
                "type": "PICKUP",
                "package_id": s.get("package_id"),
                "location": s.get("position"),
                "reason": "Robot reached package location — picking up"
            },
            priority=90,
            description="IF robot reaches package location THEN pick up the package",
            category="PICKUP"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 4 (Priority 85): Navigate to pickup
        # IF robot is assigned task AND not at pickup yet AND has path
        # THEN move along path to pickup
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R004",
            name="Navigate to Pickup",
            condition=lambda s: (
                not s.get("has_package") and
                s.get("state") == "MOVING_TO_PICKUP" and
                s.get("path") and len(s.get("path", [])) > 0 and
                s.get("position") != s.get("pickup_target")
            ),
            action=lambda s: {
                "type": "MOVE",
                "next_position": s["path"][0],
                "reason": "Moving to package pickup location"
            },
            priority=85,
            description="IF robot assigned task THEN navigate toward pickup location",
            category="NAVIGATION"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 5 (Priority 80): Replan when path is blocked/exhausted
        # IF robot has task AND has no valid path
        # THEN request replanning
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R005",
            name="Request Route Replanning",
            condition=lambda s: (
                s.get("state") in ("MOVING_TO_PICKUP", "MOVING_TO_DELIVERY", "REPLANNING") and
                (not s.get("path") or len(s.get("path", [])) == 0) and
                s.get("task_id") is not None
            ),
            action=lambda s: {
                "type": "REPLAN",
                "robot_id": s.get("robot_id"),
                "from": s.get("position"),
                "to": s.get("delivery_target") if s.get("has_package") else s.get("pickup_target"),
                "reason": "Path exhausted or blocked — requesting route replanning"
            },
            priority=80,
            description="IF planned route becomes blocked THEN request route replanning",
            category="REPLANNING"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 6 (Priority 75): Wait when next cell is reserved
        # IF robot has task AND next cell in path is occupied this step
        # THEN wait (do not move)
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R006",
            name="Wait for Conflict Resolution",
            condition=lambda s: (
                s.get("state") in ("MOVING_TO_PICKUP", "MOVING_TO_DELIVERY") and
                s.get("path") and len(s.get("path", [])) > 0 and
                s.get("next_cell_blocked", False)
            ),
            action=lambda s: {
                "type": "WAIT",
                "reason": "Next cell occupied — waiting for conflict resolution",
                "blocked_by": s.get("blocking_robot")
            },
            priority=75,
            description="IF potential collision detected THEN apply time-aware coordination",
            category="COLLISION_AVOIDANCE"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 7 (Priority 70): Idle robot requests a task
        # IF robot is IDLE AND pending tasks exist
        # THEN request task assignment
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R007",
            name="Request Task Assignment",
            condition=lambda s: (
                s.get("state") == "IDLE" and
                s.get("pending_tasks_exist", False)
            ),
            action=lambda s: {
                "type": "REQUEST_TASK",
                "robot_id": s.get("robot_id"),
                "reason": "Robot idle — requesting task assignment"
            },
            priority=70,
            description="IF robot is idle AND pending task exists THEN request task assignment",
            category="TASK_MANAGEMENT"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 8 (Priority 60): Completion → become idle
        # IF robot just delivered package
        # THEN reset to IDLE state
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R008",
            name="Complete Task and Become Idle",
            condition=lambda s: (
                s.get("state") == "DELIVERING" and
                s.get("position") == s.get("delivery_target") and
                not s.get("has_package")
            ),
            action=lambda s: {
                "type": "COMPLETE_TASK",
                "task_id": s.get("task_id"),
                "reason": "Delivery complete — robot becoming idle"
            },
            priority=60,
            description="IF robot completes delivery THEN become available for another task",
            category="TASK_MANAGEMENT"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 9 (Priority 50): Obstacle detected mid-path
        # IF robot detects obstacle in planned path
        # THEN trigger emergency replan
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R009",
            name="Obstacle Detected — Emergency Replan",
            condition=lambda s: (
                s.get("obstacle_in_path", False) and
                s.get("state") not in ("IDLE", "REPLANNING")
            ),
            action=lambda s: {
                "type": "EMERGENCY_REPLAN",
                "reason": "Dynamic obstacle detected in planned path",
                "obstacle_pos": s.get("obstacle_position")
            },
            priority=50,
            description="IF dynamic obstacle detected in path THEN emergency replan triggered",
            category="REPLANNING"
        ))
        
        # ──────────────────────────────────────────────────────────────────
        # RULE 10 (Priority 10): Default — stay idle
        # IF no other rule matches
        # THEN remain idle
        # ──────────────────────────────────────────────────────────────────
        self.add_rule(Rule(
            rule_id="R010",
            name="Default Idle",
            condition=lambda s: True,  # Always matches (lowest priority)
            action=lambda s: {
                "type": "IDLE",
                "reason": "No applicable rule — robot remains idle"
            },
            priority=10,
            description="Default: robot remains in idle state",
            category="DEFAULT"
        ))
    
    def add_rule(self, rule: Rule):
        """Add a rule and re-sort by priority (descending)."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: -r.priority)
    
    def evaluate(self, robot_state: Dict) -> Tuple[Optional[Rule], Dict]:
        """
        Evaluate all rules against the robot's current state.
        Returns the first matching rule and its resulting action.
        
        This is the forward-chaining inference step.
        """
        for rule in self.rules:
            try:
                if rule.condition(robot_state):
                    action = rule.action(robot_state)
                    return rule, action
            except Exception:
                continue  # Skip rules that error due to missing state keys
        
        # Should never reach here due to R010 always matching
        return None, {"type": "IDLE", "reason": "No rule matched"}
    
    def get_rules_summary(self) -> List[Dict]:
        """Return a human-readable list of all rules for the UI."""
        return [
            {
                "rule_id": r.rule_id,
                "name": r.name,
                "priority": r.priority,
                "description": r.description,
                "category": r.category,
            }
            for r in self.rules
        ]
    
    def evaluate_all_robots(
        self,
        robot_states: List[Dict],
        current_time: int,
    ) -> List[RuleFiringEvent]:
        """
        Evaluate rules for all robots and return a list of firing events.
        Used to populate the real-time decision log in the UI.
        """
        events = []
        for state in robot_states:
            rule, action = self.evaluate(state)
            if rule and action.get("type") not in ("IDLE", "DEFAULT"):
                events.append(RuleFiringEvent(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    robot_id=state.get("robot_id", "unknown"),
                    fired_at_time=current_time,
                    action=action,
                    description=(
                        f"Rule {rule.rule_id}: {rule.description}\n"
                        f"Robot {state.get('robot_id')} → {action.get('reason', '')}"
                    )
                ))
        return events


# Singleton rule engine instance
_rule_engine: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """Get or create the singleton rule engine."""
    global _rule_engine
    if _rule_engine is None:
        _rule_engine = RuleEngine()
    return _rule_engine
