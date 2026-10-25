"""
Warehouse Environment Model
==============================
Represents the physical warehouse: grid layout, obstacles, shelves,
pickup locations, delivery stations, and package positions.

The warehouse is a discrete 2D grid where each cell can be:
  - Empty (traversable)
  - Shelf (obstacle)
  - Obstacle (dynamic or static)
  - Pickup Location
  - Delivery Station
  - Charging Station
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple
import copy


@dataclass
class Package:
    """A package waiting for delivery."""
    package_id: str
    location: Tuple[int, int]          # Current location (pickup point initially)
    delivery_station: Tuple[int, int]  # Where it must be delivered
    status: str = "WAITING"            # WAITING, ASSIGNED, PICKED_UP, DELIVERED
    assigned_robot: Optional[str] = None


@dataclass
class Warehouse:
    """
    The warehouse environment model.
    
    Grid coordinate system: (col, row) where (0,0) is top-left.
    col increases left to right, row increases top to bottom.
    """
    grid_width: int = 20
    grid_height: int = 15
    
    # Fixed structural elements
    shelves: Set[Tuple[int, int]] = field(default_factory=set)
    pickup_locations: List[Tuple[int, int]] = field(default_factory=list)
    delivery_stations: List[Tuple[int, int]] = field(default_factory=list)
    charging_stations: List[Tuple[int, int]] = field(default_factory=list)
    
    # Dynamic elements
    dynamic_obstacles: Set[Tuple[int, int]] = field(default_factory=set)
    packages: Dict[str, Package] = field(default_factory=dict)
    
    def get_all_obstacles(self) -> Set[Tuple[int, int]]:
        """Get all blocked cells (shelves + dynamic obstacles)."""
        return self.shelves | self.dynamic_obstacles
    
    def is_traversable(self, pos: Tuple[int, int]) -> bool:
        """Check if a cell is within bounds and not blocked."""
        x, y = pos
        if not (0 <= x < self.grid_width and 0 <= y < self.grid_height):
            return False
        return pos not in self.get_all_obstacles()
    
    def is_valid_robot_position(self, pos: Tuple[int, int]) -> bool:
        """Valid for robot placement: traversable and not already special."""
        return self.is_traversable(pos)
    
    def add_obstacle(self, pos: Tuple[int, int]) -> bool:
        """Add a dynamic obstacle. Returns True if successful."""
        if not (0 <= pos[0] < self.grid_width and 0 <= pos[1] < self.grid_height):
            return False
        if pos in self.shelves:
            return False  # Already a shelf
        if pos in self.pickup_locations or pos in self.delivery_stations:
            return False  # Cannot block critical locations
        self.dynamic_obstacles.add(pos)
        return True
    
    def remove_obstacle(self, pos: Tuple[int, int]) -> bool:
        """Remove a dynamic obstacle."""
        if pos in self.dynamic_obstacles:
            self.dynamic_obstacles.discard(pos)
            return True
        return False
    
    def add_package(self, package: Package) -> bool:
        """Add a package to the warehouse."""
        if not self.is_traversable(package.location):
            return False
        self.packages[package.package_id] = package
        return True
    
    def get_package(self, package_id: str) -> Optional[Package]:
        return self.packages.get(package_id)
    
    def get_waiting_packages(self) -> List[Package]:
        return [p for p in self.packages.values() if p.status == "WAITING"]
    
    def to_dict(self) -> Dict:
        return {
            "grid_width": self.grid_width,
            "grid_height": self.grid_height,
            "shelves": [list(s) for s in self.shelves],
            "dynamic_obstacles": [list(o) for o in self.dynamic_obstacles],
            "pickup_locations": [list(p) for p in self.pickup_locations],
            "delivery_stations": [list(d) for d in self.delivery_stations],
            "charging_stations": [list(c) for c in self.charging_stations],
            "packages": {
                pid: {
                    "package_id": p.package_id,
                    "location": list(p.location),
                    "delivery_station": list(p.delivery_station),
                    "status": p.status,
                    "assigned_robot": p.assigned_robot,
                }
                for pid, p in self.packages.items()
            },
        }


def create_default_warehouse() -> Warehouse:
    """
    Create the default 20×15 warehouse layout.
    
    Layout design:
    - Shelves arranged in rows to form aisles
    - 2 pickup locations (top area)
    - 2 delivery stations (bottom area)
    - 2 charging stations (corners)
    - Clear traversable aisles between shelves
    """
    warehouse = Warehouse(grid_width=20, grid_height=15)
    
    # ── SHELF LAYOUT ──────────────────────────────────────────────────────
    # Row 1 shelves (y=2): columns 2-5 and 8-11 and 14-17
    shelf_rows = [
        # (x_start, x_end, y) — horizontal shelf segments
        (2, 4, 2), (6, 8, 2), (11, 13, 2), (15, 17, 2),
        (2, 4, 4), (6, 8, 4), (11, 13, 4), (15, 17, 4),
        (2, 4, 7), (6, 8, 7), (11, 13, 7), (15, 17, 7),
        (2, 4, 9), (6, 8, 9), (11, 13, 9), (15, 17, 9),
    ]
    
    for x_start, x_end, y in shelf_rows:
        for x in range(x_start, x_end + 1):
            warehouse.shelves.add((x, y))
    
    # ── PICKUP LOCATIONS ──────────────────────────────────────────────────
    warehouse.pickup_locations = [
        (4, 1),   # Pickup A (top-left area)
        (15, 1),  # Pickup B (top-right area)
        (9, 6),   # Pickup C (center)
    ]
    
    # ── DELIVERY STATIONS ─────────────────────────────────────────────────
    warehouse.delivery_stations = [
        (1, 13),  # Delivery Station 1 (bottom-left)
        (18, 13), # Delivery Station 2 (bottom-right)
    ]
    
    # ── CHARGING STATIONS ─────────────────────────────────────────────────
    warehouse.charging_stations = [
        (0, 0),   # Charging Station A (top-left corner)
        (19, 0),  # Charging Station B (top-right corner)
    ]
    
    # ── INITIAL PACKAGES ──────────────────────────────────────────────────
    initial_packages = [
        Package("P1", (4, 1),  (1, 13),  "WAITING"),
        Package("P2", (15, 1), (18, 13), "WAITING"),
        Package("P3", (9, 6),  (1, 13),  "WAITING"),
        Package("P4", (4, 1),  (18, 13), "WAITING"),
        Package("P5", (15, 1), (1, 13),  "WAITING"),
        Package("P6", (9, 6),  (18, 13), "WAITING"),
        Package("P7", (4, 1),  (1, 13),  "WAITING"),
        Package("P8", (15, 1), (18, 13), "WAITING"),
        Package("P9", (9, 6),  (1, 13),  "WAITING"),
        Package("P10",(4, 1),  (18, 13), "WAITING"),
    ]
    
    for pkg in initial_packages:
        warehouse.packages[pkg.package_id] = pkg
    
    return warehouse


def create_scenario_warehouse(scenario_id: str) -> "tuple[Warehouse, list]":
    """
    Create warehouse configurations for the three demonstration scenarios.
    Returns (warehouse, robot_start_positions).
    """
    
    if scenario_id == "basic_delivery":
        # Scenario A: 3 robots, open layout, simple deliveries
        w = Warehouse(grid_width=15, grid_height=10)
        
        # Simple shelf rows
        for x in range(2, 5):
            w.shelves.add((x, 3))
            w.shelves.add((x, 6))
        for x in range(8, 11):
            w.shelves.add((x, 3))
            w.shelves.add((x, 6))
        
        w.pickup_locations = [(0, 1), (7, 1), (14, 1)]
        w.delivery_stations = [(0, 8), (14, 8)]
        w.charging_stations = [(0, 0), (14, 0)]
        
        pkgs = [
            Package("PA1", (0, 1),  (0, 8),  "WAITING"),
            Package("PA2", (7, 1),  (14, 8), "WAITING"),
            Package("PA3", (14, 1), (0, 8),  "WAITING"),
        ]
        for p in pkgs:
            w.packages[p.package_id] = p
        
        robot_starts = [(0, 4), (7, 4), (14, 4)]
        return w, robot_starts
    
    elif scenario_id == "collision_avoidance":
        # Scenario B: 2 robots on a narrow shared path
        w = Warehouse(grid_width=12, grid_height=8)
        
        # Narrow corridor — shelves on both sides of center row
        for x in range(0, 12):
            w.shelves.add((x, 2))  # Top wall
            w.shelves.add((x, 5))  # Bottom wall
        
        # Remove cells to create a single-width corridor
        for x in [0, 11]:
            w.shelves.discard((x, 2))
            w.shelves.discard((x, 5))
        
        # Create gaps at specific points so there IS a path
        for x in [5, 6]:
            w.shelves.discard((x, 2))
            w.shelves.discard((x, 5))
        
        w.pickup_locations = [(0, 3), (11, 3)]
        w.delivery_stations = [(11, 4), (0, 4)]
        w.charging_stations = []
        
        pkgs = [
            Package("PB1", (0, 3), (11, 4), "WAITING"),
            Package("PB2", (11, 3), (0, 4), "WAITING"),
        ]
        for p in pkgs:
            w.packages[p.package_id] = p
        
        robot_starts = [(0, 3), (11, 3)]
        return w, robot_starts
    
    elif scenario_id == "dynamic_obstacle":
        # Scenario C: Robot path will be blocked mid-delivery
        w = Warehouse(grid_width=15, grid_height=10)
        
        # Simple layout
        for x in range(3, 6):
            w.shelves.add((x, 4))
        for x in range(9, 12):
            w.shelves.add((x, 4))
        
        w.pickup_locations = [(1, 1), (13, 1)]
        w.delivery_stations = [(1, 8), (13, 8)]
        w.charging_stations = []
        
        pkgs = [
            Package("PC1", (1, 1),  (1, 8),  "WAITING"),
            Package("PC2", (13, 1), (13, 8), "WAITING"),
        ]
        for p in pkgs:
            w.packages[p.package_id] = p
        
        robot_starts = [(1, 1), (13, 1)]
        return w, robot_starts
    
    else:
        w = create_default_warehouse()
        return w, [(1, 1), (1, 3), (18, 1), (18, 3), (9, 1)]
