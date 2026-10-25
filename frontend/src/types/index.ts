// ============================================================
// TypeScript Types for the Warehouse Management System
// ============================================================

export interface Position {
  x: number;
  y: number;
}

export type RobotState =
  | 'IDLE'
  | 'ASSIGNED'
  | 'MOVING_TO_PICKUP'
  | 'PICKING_UP'
  | 'MOVING_TO_DELIVERY'
  | 'DELIVERING'
  | 'WAITING'
  | 'REPLANNING'
  | 'BLOCKED';

export interface Robot {
  robot_id: string;
  position: [number, number];
  color: string;
  state: RobotState;
  task_id: string | null;
  package_id: string | null;
  pickup_target: [number, number] | null;
  delivery_target: [number, number] | null;
  has_package: boolean;
  path: [number, number][];
  distance_traveled: number;
  tasks_completed: number;
  wait_steps: number;
  total_steps: number;
  replan_count: number;
}

export interface Package {
  package_id: string;
  location: [number, number];
  delivery_station: [number, number];
  status: 'WAITING' | 'ASSIGNED' | 'PICKED_UP' | 'DELIVERED';
  assigned_robot: string | null;
}

export interface Task {
  task_id: string;
  package_id: string;
  pickup_location: [number, number];
  delivery_station: [number, number];
  priority: number;
  status: 'PENDING' | 'ASSIGNED' | 'IN_PROGRESS' | 'COMPLETED';
  assigned_robot: string | null;
  estimated_cost: number;
  creation_time: number;
  completion_time: number | null;
}

export interface Statistics {
  total_distance: number;
  completed_deliveries: number;
  pending_deliveries: number;
  total_planning_time_ms: number;
  conflicts_detected: number;
  conflicts_resolved: number;
  average_delivery_steps: number;
  total_waiting_steps: number;
  nodes_explored: number;
  replan_count: number;
  simulation_step: number;
}

export interface EventLog {
  timestamp: string;
  event_type: string;
  message: string;
  robot_id: string | null;
  package_id: string | null;
  rule_id: string | null;
  step: number;
}

export interface RuleInfo {
  rule_id: string;
  name: string;
  priority: number;
  description: string;
  category: string;
}

export interface WarehouseState {
  grid_width: number;
  grid_height: number;
  obstacles: [number, number][];
  shelves: [number, number][];
  dynamic_obstacles: [number, number][];
  pickup_locations: [number, number][];
  delivery_stations: [number, number][];
  charging_stations: [number, number][];
  robots: Robot[];
  packages: Package[];
  tasks: Task[];
  statistics: Statistics;
  simulation_step: number;
  is_running: boolean;
  speed: number;
  active_algorithm: string;
  event_logs: EventLog[];
  reservation_table: ReservationTableSnapshot;
  rules: RuleInfo[];
}

export interface ReservationTableSnapshot {
  vertex_reservations: Record<string, Array<{ x: number; y: number; robot_id: string }>>;
}

export interface AStarStep {
  step: number;
  current: [number, number];
  open: [number, number][];
  closed: [number, number][];
  g: number;
  h: number;
  f: number;
}

export interface AStarResult {
  success: boolean;
  path: [number, number][];
  path_length: number;
  nodes_explored: number;
  planning_time_ms: number;
  message: string;
  steps?: AStarStep[];
  g_scores?: Record<string, number>;
  h_scores?: Record<string, number>;
}

export interface CompareResult {
  astar: AStarResult;
  bfs: AStarResult;
  comparison: {
    astar_faster: boolean;
    same_path_length: boolean;
    astar_nodes_explored: number;
    bfs_nodes_explored: number;
    note: string;
  };
}

export type InteractionMode =
  | 'SELECT'
  | 'ADD_ROBOT'
  | 'ADD_PACKAGE_PICKUP'
  | 'ADD_PACKAGE_DELIVERY'
  | 'ADD_OBSTACLE'
  | 'REMOVE_OBSTACLE'
  | 'ASTAR_START'
  | 'ASTAR_GOAL';

export type AppPage = 'dashboard' | 'algorithm_explorer' | 'analytics' | 'about';
