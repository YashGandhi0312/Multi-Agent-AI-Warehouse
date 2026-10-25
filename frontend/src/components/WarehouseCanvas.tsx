// ============================================================
// Warehouse Canvas — HTML5 Canvas Visualization
// Real-time 2D grid rendering of the warehouse simulation
// ============================================================

import React, { useRef, useEffect, useCallback, useState } from 'react';
import type { WarehouseState, Robot, InteractionMode } from '../types';

interface WarehouseCanvasProps {
  state: WarehouseState;
  interactionMode: InteractionMode;
  selectedRobot: string | null;
  onCellClick: (x: number, y: number) => void;
  onRobotClick: (robotId: string) => void;
  pendingPackagePickup: [number, number] | null;
}

const COLORS = {
  background: '#000000',
  grid: 'rgba(255,255,255,0.05)',
  gridBright: 'rgba(255,255,255,0.12)',
  shelf: '#18181b',
  shelfStroke: '#27272a',
  obstacle: '#450a0a',
  obstacleStroke: '#ef4444',
  pickup: '#064e3b',
  pickupStroke: '#10b981',
  delivery: '#1e3a8a',
  deliveryStroke: '#3b82f6',
  charging: '#18181b',
  chargingStroke: '#a855f7',
  package: '#78350f',
  packageStroke: '#f59e0b',
  packageDelivered: '#064e3b',
  empty: '#09090b',
};

export const WarehouseCanvas: React.FC<WarehouseCanvasProps> = ({
  state,
  interactionMode,
  selectedRobot,
  onCellClick,
  onRobotClick,
  pendingPackagePickup,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{ x: number; y: number; text: string } | null>(null);
  const animFrameRef = useRef<number>(0);
  const robotAnimOffsets = useRef<Map<string, { x: number; y: number; prevX: number; prevY: number; t: number }>>(new Map());
  const prevStepRef = useRef<number>(-1);

  const getCellSize = useCallback(() => {
    if (!containerRef.current) return 28;
    const containerW = containerRef.current.clientWidth;
    const containerH = containerRef.current.clientHeight;
    const cellW = Math.floor(containerW / (state.grid_width + 0.5));
    const cellH = Math.floor(containerH / (state.grid_height + 0.5));
    return Math.max(20, Math.min(cellW, cellH, 44));
  }, [state.grid_width, state.grid_height]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const cellSize = getCellSize();
    const padX = Math.floor((canvas.width - state.grid_width * cellSize) / 2);
    const padY = Math.floor((canvas.height - state.grid_height * cellSize) / 2);

    // Clear
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = COLORS.background;
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid background
    for (let row = 0; row < state.grid_height; row++) {
      for (let col = 0; col < state.grid_width; col++) {
        const px = padX + col * cellSize;
        const py = padY + row * cellSize;
        ctx.fillStyle = (col + row) % 2 === 0 ? '#050507' : '#08080a';
        ctx.fillRect(px, py, cellSize, cellSize);
        ctx.strokeStyle = COLORS.grid;
        ctx.lineWidth = 0.5;
        ctx.strokeRect(px, py, cellSize, cellSize);
      }
    }

    const shelfSet = new Set(state.shelves.map(([x, y]) => `${x},${y}`));
    const dynObsSet = new Set(state.dynamic_obstacles.map(([x, y]) => `${x},${y}`));
    const pickupSet = new Set(state.pickup_locations.map(([x, y]) => `${x},${y}`));
    const deliverySet = new Set(state.delivery_stations.map(([x, y]) => `${x},${y}`));
    const chargingSet = new Set(state.charging_stations.map(([x, y]) => `${x},${y}`));

    // Draw shelves
    for (const [x, y] of state.shelves) {
      const px = padX + x * cellSize;
      const py = padY + y * cellSize;
      const grad = ctx.createLinearGradient(px, py, px, py + cellSize);
      grad.addColorStop(0, '#1c1c21');
      grad.addColorStop(1, '#111114');
      ctx.fillStyle = grad;
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      ctx.strokeStyle = '#27272a';
      ctx.lineWidth = 1;
      ctx.strokeRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      // Shelf rack lines
      ctx.strokeStyle = 'rgba(255,255,255,0.12)';
      ctx.lineWidth = 1;
      const m = cellSize * 0.15;
      ctx.beginPath();
      ctx.moveTo(px + m, py + cellSize * 0.35);
      ctx.lineTo(px + cellSize - m, py + cellSize * 0.35);
      ctx.moveTo(px + m, py + cellSize * 0.65);
      ctx.lineTo(px + cellSize - m, py + cellSize * 0.65);
      ctx.stroke();
    }

    // Draw dynamic obstacles
    for (const [x, y] of state.dynamic_obstacles) {
      const px = padX + x * cellSize;
      const py = padY + y * cellSize;
      ctx.fillStyle = '#3b0000';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      ctx.strokeStyle = '#dc2626';
      ctx.lineWidth = 2;
      ctx.strokeRect(px + 2, py + 2, cellSize - 4, cellSize - 4);
      // X mark
      ctx.strokeStyle = '#ef4444';
      ctx.lineWidth = 2;
      const m = cellSize * 0.25;
      ctx.beginPath();
      ctx.moveTo(px + m, py + m);
      ctx.lineTo(px + cellSize - m, py + cellSize - m);
      ctx.moveTo(px + cellSize - m, py + m);
      ctx.lineTo(px + m, py + cellSize - m);
      ctx.stroke();
    }

    // Draw pickup locations
    for (const [x, y] of state.pickup_locations) {
      const px = padX + x * cellSize;
      const py = padY + y * cellSize;
      ctx.fillStyle = 'rgba(14,165,233,0.15)';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      ctx.strokeStyle = '#0ea5e9';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 2]);
      ctx.strokeRect(px + 2, py + 2, cellSize - 4, cellSize - 4);
      ctx.setLineDash([]);
      // P label
      if (cellSize >= 24) {
        ctx.fillStyle = '#7dd3fc';
        ctx.font = `bold ${Math.floor(cellSize * 0.35)}px Inter`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('P', px + cellSize / 2, py + cellSize / 2);
      }
    }

    // Draw delivery stations
    for (const [x, y] of state.delivery_stations) {
      const px = padX + x * cellSize;
      const py = padY + y * cellSize;
      ctx.fillStyle = 'rgba(34,197,94,0.15)';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 2;
      ctx.strokeRect(px + 2, py + 2, cellSize - 4, cellSize - 4);
      if (cellSize >= 24) {
        ctx.fillStyle = '#4ade80';
        ctx.font = `bold ${Math.floor(cellSize * 0.35)}px Inter`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('D', px + cellSize / 2, py + cellSize / 2);
      }
    }

    // Draw charging stations
    for (const [x, y] of state.charging_stations) {
      const px = padX + x * cellSize;
      const py = padY + y * cellSize;
      ctx.fillStyle = 'rgba(124,58,237,0.15)';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      ctx.strokeStyle = '#7c3aed';
      ctx.lineWidth = 1.5;
      ctx.strokeRect(px + 2, py + 2, cellSize - 4, cellSize - 4);
      if (cellSize >= 24) {
        ctx.fillStyle = '#a78bfa';
        ctx.font = `bold ${Math.floor(cellSize * 0.35)}px Inter`;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('⚡', px + cellSize / 2, py + cellSize / 2);
      }
    }

    // Draw packages on grid
    for (const pkg of state.packages) {
      if (pkg.status === 'WAITING' || pkg.status === 'ASSIGNED') {
        const [x, y] = pkg.location;
        const px = padX + x * cellSize;
        const py = padY + y * cellSize;
        const boxSize = cellSize * 0.45;
        const bx = px + (cellSize - boxSize) / 2;
        const by = py + (cellSize - boxSize) / 2;
        ctx.fillStyle = '#92400e';
        ctx.fillRect(bx, by, boxSize, boxSize);
        ctx.strokeStyle = '#f59e0b';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(bx, by, boxSize, boxSize);
        // Box cross lines
        ctx.beginPath();
        ctx.moveTo(bx + boxSize / 2, by);
        ctx.lineTo(bx + boxSize / 2, by + boxSize);
        ctx.moveTo(bx, by + boxSize / 2);
        ctx.lineTo(bx + boxSize, by + boxSize / 2);
        ctx.strokeStyle = '#fbbf24';
        ctx.lineWidth = 0.8;
        ctx.stroke();
      }
    }

    // Draw robot paths (planned routes)
    for (const robot of state.robots) {
      if (robot.path.length > 1 && robot.state !== 'IDLE' && robot.state !== 'BLOCKED') {
        ctx.strokeStyle = robot.color + '55';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 4]);
        ctx.beginPath();
        const [rx, ry] = robot.position;
        ctx.moveTo(padX + rx * cellSize + cellSize / 2, padY + ry * cellSize + cellSize / 2);
        for (const [px, py] of robot.path) {
          ctx.lineTo(padX + px * cellSize + cellSize / 2, padY + py * cellSize + cellSize / 2);
        }
        ctx.stroke();
        ctx.setLineDash([]);

        // Arrow at end of path (goal indicator)
        if (robot.path.length > 0) {
          const [gx, gy] = robot.path[robot.path.length - 1];
          const gpx = padX + gx * cellSize + cellSize / 2;
          const gpy = padY + gy * cellSize + cellSize / 2;
          ctx.beginPath();
          ctx.arc(gpx, gpy, cellSize * 0.18, 0, Math.PI * 2);
          ctx.fillStyle = robot.color + '88';
          ctx.fill();
        }
      }
    }

    // Draw robots
    for (const robot of state.robots) {
      const isSelected = selectedRobot === robot.robot_id;
      const [rx, ry] = robot.position;
      const px = padX + rx * cellSize;
      const py = padY + ry * cellSize;
      const cx = px + cellSize / 2;
      const cy = py + cellSize / 2;
      const r = cellSize * 0.38;

      // Selection ring
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(cx, cy, r + 4, 0, Math.PI * 2);
        ctx.strokeStyle = robot.color;
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 2]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      // Glow
      const glow = ctx.createRadialGradient(cx, cy, 0, cx, cy, r + 6);
      glow.addColorStop(0, robot.color + '30');
      glow.addColorStop(1, 'transparent');
      ctx.fillStyle = glow;
      ctx.beginPath();
      ctx.arc(cx, cy, r + 6, 0, Math.PI * 2);
      ctx.fill();

      // Robot body
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, Math.PI * 2);
      const bodyGrad = ctx.createRadialGradient(cx - r * 0.2, cy - r * 0.2, r * 0.1, cx, cy, r);
      bodyGrad.addColorStop(0, robot.color + 'ff');
      bodyGrad.addColorStop(1, robot.color + 'aa');
      ctx.fillStyle = bodyGrad;
      ctx.fill();
      ctx.strokeStyle = 'rgba(255,255,255,0.3)';
      ctx.lineWidth = 1;
      ctx.stroke();

      // Package indicator
      if (robot.has_package) {
        ctx.beginPath();
        const boxS = r * 0.55;
        ctx.fillStyle = '#f59e0b';
        ctx.fillRect(cx - boxS / 2, cy - boxS / 2, boxS, boxS);
        ctx.strokeStyle = '#fbbf24';
        ctx.lineWidth = 1;
        ctx.strokeRect(cx - boxS / 2, cy - boxS / 2, boxS, boxS);
      }

      // Robot ID label
      if (cellSize >= 24) {
        ctx.fillStyle = '#ffffff';
        ctx.font = `bold ${Math.max(9, Math.floor(cellSize * 0.28))}px Inter`;
        ctx.textAlign = 'center';
        ctx.textBaseline = robot.has_package ? 'bottom' : 'middle';
        ctx.fillText(robot.robot_id, cx, robot.has_package ? cy - 1 : cy + 1);
      }

      // State indicator dot
      const dotColor = stateToColor(robot.state);
      ctx.beginPath();
      ctx.arc(cx + r * 0.7, cy - r * 0.7, 3, 0, Math.PI * 2);
      ctx.fillStyle = dotColor;
      ctx.fill();
    }

    // Pending package pickup indicator
    if (pendingPackagePickup) {
      const [x, y] = pendingPackagePickup;
      const px = padX + x * cellSize;
      const py = padY + y * cellSize;
      ctx.strokeStyle = '#f59e0b';
      ctx.lineWidth = 2;
      ctx.setLineDash([4, 2]);
      ctx.strokeRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      ctx.setLineDash([]);
      ctx.fillStyle = 'rgba(245,158,11,0.15)';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
    }

    // Hover cursor hint based on interaction mode
    if (interactionMode !== 'SELECT') {
      ctx.fillStyle = 'rgba(59,130,246,0.08)';
      ctx.font = '12px Inter';
      ctx.fillStyle = '#64748b';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'bottom';
      ctx.fillText(`Click to ${interactionModeLabel(interactionMode)}`, canvas.width / 2, canvas.height - 8);
    }
  }, [state, selectedRobot, interactionMode, pendingPackagePickup, getCellSize]);

  // Resize observer
  useEffect(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const resize = () => {
      canvas.width = container.clientWidth;
      canvas.height = container.clientHeight;
      draw();
    };

    const observer = new ResizeObserver(resize);
    observer.observe(container);
    resize();
    return () => observer.disconnect();
  }, [draw]);

  // Redraw on state change
  useEffect(() => {
    draw();
  }, [draw]);

  const handleCanvasClick = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const cellSize = getCellSize();
    const padX = Math.floor((canvas.width - state.grid_width * cellSize) / 2);
    const padY = Math.floor((canvas.height - state.grid_height * cellSize) / 2);

    const col = Math.floor((mouseX - padX) / cellSize);
    const row = Math.floor((mouseY - padY) / cellSize);

    if (col < 0 || col >= state.grid_width || row < 0 || row >= state.grid_height) return;

    // Check if a robot was clicked
    for (const robot of state.robots) {
      if (robot.position[0] === col && robot.position[1] === row) {
        onRobotClick(robot.robot_id);
        return;
      }
    }

    onCellClick(col, row);
  }, [state, getCellSize, onCellClick, onRobotClick]);

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const cellSize = getCellSize();
    const padX = Math.floor((canvas.width - state.grid_width * cellSize) / 2);
    const padY = Math.floor((canvas.height - state.grid_height * cellSize) / 2);

    const col = Math.floor((mouseX - padX) / cellSize);
    const row = Math.floor((mouseY - padY) / cellSize);

    if (col < 0 || col >= state.grid_width || row < 0 || row >= state.grid_height) {
      setTooltip(null);
      return;
    }

    // Build tooltip text
    let text = `(${col}, ${row})`;

    const robot = state.robots.find(r => r.position[0] === col && r.position[1] === row);
    if (robot) {
      text = `Robot ${robot.robot_id}\n${robot.state}\n${robot.has_package ? `📦 ${robot.package_id}` : 'No package'}`;
    }

    const pkg = state.packages.find(p =>
      p.location[0] === col && p.location[1] === row &&
      (p.status === 'WAITING' || p.status === 'ASSIGNED')
    );
    if (pkg) text += `\n📦 ${pkg.package_id}`;

    const isShelf = state.shelves.some(([x, y]) => x === col && y === row);
    if (isShelf) text = `Shelf at (${col},${row})`;

    const isPickup = state.pickup_locations.some(([x, y]) => x === col && y === row);
    if (isPickup) text = `Pickup Zone\n(${col}, ${row})`;

    const isDelivery = state.delivery_stations.some(([x, y]) => x === col && y === row);
    if (isDelivery) text = `Delivery Station\n(${col}, ${row})`;

    setTooltip({ x: e.clientX - rect.left + 12, y: e.clientY - rect.top - 8, text });
  }, [state, getCellSize]);

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%', position: 'relative', cursor: getCursorStyle(interactionMode) }}
    >
      <canvas
        ref={canvasRef}
        onClick={handleCanvasClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setTooltip(null)}
        style={{ width: '100%', height: '100%', display: 'block' }}
      />
      {tooltip && (
        <div
          className="tooltip"
          style={{ left: tooltip.x, top: tooltip.y, whiteSpace: 'pre-line' }}
        >
          {tooltip.text}
        </div>
      )}

      {/* Legend */}
      <div style={{
        position: 'absolute', bottom: 8, right: 8,
        background: 'rgba(2,8,24,0.8)', borderRadius: 8, padding: '6px 10px',
        border: '1px solid rgba(59,130,246,0.2)', display: 'flex', gap: 12, flexWrap: 'wrap'
      }}>
        {[
          { color: '#1e3a70', label: 'Shelf' },
          { color: '#0ea5e9', label: 'Pickup', border: true },
          { color: '#22c55e', label: 'Delivery' },
          { color: '#f59e0b', label: 'Package' },
          { color: '#dc2626', label: 'Obstacle' },
          { color: '#7c3aed', label: 'Charging' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <div style={{
              width: 10, height: 10, borderRadius: 2,
              background: item.color + '44',
              border: `1px solid ${item.color}`,
            }} />
            <span style={{ fontSize: 10, color: '#64748b' }}>{item.label}</span>
          </div>
        ))}
      </div>

      {/* Step counter */}
      <div style={{
        position: 'absolute', top: 8, right: 8,
        background: 'rgba(2,8,24,0.8)', borderRadius: 6, padding: '3px 10px',
        border: '1px solid rgba(59,130,246,0.2)', fontSize: 11, color: '#60a5fa',
        fontFamily: 'JetBrains Mono, monospace',
      }}>
        Step: {state.simulation_step}
      </div>
    </div>
  );
};

function stateToColor(state: string): string {
  const map: Record<string, string> = {
    IDLE: '#64748b',
    ASSIGNED: '#f97316',
    MOVING_TO_PICKUP: '#22d3ee',
    PICKING_UP: '#60a5fa',
    MOVING_TO_DELIVERY: '#4ade80',
    DELIVERING: '#22c55e',
    WAITING: '#fbbf24',
    REPLANNING: '#c084fc',
    BLOCKED: '#f87171',
  };
  return map[state] || '#64748b';
}

function getCursorStyle(mode: InteractionMode): string {
  if (mode === 'SELECT') return 'default';
  if (mode === 'ADD_OBSTACLE' || mode === 'REMOVE_OBSTACLE') return 'crosshair';
  return 'cell';
}

function interactionModeLabel(mode: InteractionMode): string {
  const map: Record<string, string> = {
    ADD_ROBOT: 'place robot',
    ADD_PACKAGE_PICKUP: 'set pickup location',
    ADD_PACKAGE_DELIVERY: 'set delivery location',
    ADD_OBSTACLE: 'add obstacle',
    REMOVE_OBSTACLE: 'remove obstacle',
    ASTAR_START: 'set A* start',
    ASTAR_GOAL: 'set A* goal',
  };
  return map[mode] || 'click';
}
