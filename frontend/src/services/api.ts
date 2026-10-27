// ============================================================
// API Service Layer — Communicates with FastAPI Backend
// ============================================================

const BASE_URL = '/api';

async function apiRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  return response.json();
}

// ─── Simulation Control ──────────────────────────────────────────────────────

export const simulationControl = (action: string) =>
  apiRequest('/simulation/control', {
    method: 'POST',
    body: JSON.stringify({ action }),
  });

export const setSimulationSpeed = (speed: number) =>
  apiRequest('/simulation/speed', {
    method: 'POST',
    body: JSON.stringify({ speed }),
  });

// ─── State ───────────────────────────────────────────────────────────────────

export const getState = () => apiRequest('/state');

// ─── Robot Management ────────────────────────────────────────────────────────

export const addRobot = (position: [number, number]) =>
  apiRequest('/robot/add', {
    method: 'POST',
    body: JSON.stringify({ position }),
  });

export const removeRobot = (robot_id: string) =>
  apiRequest('/robot/remove', {
    method: 'POST',
    body: JSON.stringify({ robot_id }),
  });

// ─── Package Management ──────────────────────────────────────────────────────

export const addPackage = (
  pickup_location: [number, number],
  delivery_station: [number, number],
  priority: number = 1,
) =>
  apiRequest('/package/add', {
    method: 'POST',
    body: JSON.stringify({ pickup_location, delivery_station, priority }),
  });

// ─── Obstacle Management ─────────────────────────────────────────────────────

export const addObstacle = (position: [number, number]) =>
  apiRequest('/obstacle/add', {
    method: 'POST',
    body: JSON.stringify({ position }),
  });

export const removeObstacle = (position: [number, number]) =>
  apiRequest('/obstacle/remove', {
    method: 'POST',
    body: JSON.stringify({ position }),
  });

// ─── Scenarios ───────────────────────────────────────────────────────────────

export const loadScenario = (scenario_id: string) =>
  apiRequest(`/scenario/${scenario_id}`, { method: 'POST' });

// ─── A* Algorithm ────────────────────────────────────────────────────────────

export const runAstar = (
  start: [number, number],
  goal: [number, number],
  includeVisualization: boolean = false,
) =>
  apiRequest('/astar', {
    method: 'POST',
    body: JSON.stringify({
      start,
      goal,
      include_visualization: includeVisualization,
    }),
  });

export const compareAlgorithms = (start: [number, number], goal: [number, number]) =>
  apiRequest('/compare', {
    method: 'POST',
    body: JSON.stringify({ start, goal }),
  });

// ─── Rules & Cost Matrix ─────────────────────────────────────────────────────

export const getRules = () => apiRequest('/rules');
export const getCostMatrix = () => apiRequest('/cost-matrix');
export const getReservationTable = () => apiRequest('/reservation-table');
export const getBacktracking = () => apiRequest('/backtracking');
