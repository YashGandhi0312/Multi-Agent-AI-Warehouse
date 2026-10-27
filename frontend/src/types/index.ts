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
  stuck_steps: number;
  backtrack_count: number;
  decision_stack: DecisionPoint[];
}

export interface DecisionPoint {
  level: 'TASK' | 'ROUTE';
  label: string | null;
  attempts: number;
  committed: boolean;
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
  search_nodes: number;
  branches_pruned: number;
  search_backtracks: number;
  allocation_cost_saved: number;
  ordering_resolutions: number;
  agent_backtracks: number;
  deadlocks_resolved: number;
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
  backtracking: BacktrackingState;
}

export interface SearchTreeNode {
  id: number;
  parent: number | null;
  depth: number;
  task_id: string;
  robot_id: string | null;   // null = SKIP
  cost: number;
  status: 'expanded' | 'pruned' | 'best';
}

export interface AllocationSearch {
  step: number;
  nodes_expanded: number;
  branches_pruned: number;
  backtracks: number;
  max_depth: number;
  solutions_found: number;
  optimal: boolean;
  greedy_cost: number;
  best_cost: number;
  cost_saved: number;
  search_time_ms: number;
  assignment: Record<string, string | null>;
  trace?: SearchTreeNode[];
}

export interface OrderingSearch {
  step: number;
  ca_calls: number;
  backtracks: number;
  orderings_tried: number;
  resolved_by_backtracking: boolean;
  final_order: string[];
  unsolvable: string[];
  budget_exhausted: boolean;
  search_time_ms: number;
}

export interface Nogood {
  robot_id: string | null;   // null = deferred for every robot
  task_id: string;
  expires_at: number;
}

export interface BacktrackingState {
  allocation_search: AllocationSearch | null;
  ordering_search: OrderingSearch | null;
  nogoods: Nogood[];
  agents?: Array<{
    robot_id: string;
    state: RobotState;
    stuck_steps: number;
    backtrack_count: number;
    decision_stack: DecisionPoint[];
  }>;
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
