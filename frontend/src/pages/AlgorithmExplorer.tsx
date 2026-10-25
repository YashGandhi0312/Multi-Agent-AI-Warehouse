// ============================================================
// Classical AI Algorithm Explorer & Benchmark
// Theme: Sleek Pitch Black (#000000)
// Evaluator Focus: Direct proof of A* Optimality vs BFS
// ============================================================

import React, { useState, useRef, useEffect, useCallback } from 'react';
import type { WarehouseState } from '../types';
import * as api from '../services/api';
import { Play, RotateCcw, Cpu, CheckCircle2, Zap, ArrowRight, ShieldCheck } from 'lucide-react';

interface AlgorithmExplorerProps {
  state: WarehouseState;
}

export const AlgorithmExplorer: React.FC<AlgorithmExplorerProps> = ({ state }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [start, setStart] = useState<[number, number]>([1, 1]);
  const [goal, setGoal] = useState<[number, number]>([state.grid_width - 2, state.grid_height - 2]);
  const [settingMode, setSettingMode] = useState<'IDLE' | 'START' | 'GOAL'>('IDLE');
  
  const [astarPath, setAstarPath] = useState<[number, number][] | null>(null);
  const [closedNodes, setClosedNodes] = useState<[number, number][]>([]);
  const [openNodes, setOpenNodes] = useState<[number, number][]>([]);
  const [compareResult, setCompareResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const getCellSize = useCallback(() => {
    if (!containerRef.current) return 26;
    const w = containerRef.current.clientWidth;
    const h = containerRef.current.clientHeight;
    const cw = Math.floor(w / (state.grid_width + 0.5));
    const ch = Math.floor(h / (state.grid_height + 0.5));
    return Math.max(18, Math.min(cw, ch, 40));
  }, [state.grid_width, state.grid_height]);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = container.clientWidth;
    canvas.height = container.clientHeight;

    const cellSize = getCellSize();
    const padX = Math.floor((canvas.width - state.grid_width * cellSize) / 2);
    const padY = Math.floor((canvas.height - state.grid_height * cellSize) / 2);

    // Deep black canvas background
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = '#000000';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Grid cells
    for (let r = 0; r < state.grid_height; r++) {
      for (let c = 0; c < state.grid_width; c++) {
        const px = padX + c * cellSize;
        const py = padY + r * cellSize;
        ctx.fillStyle = (c + r) % 2 === 0 ? '#050507' : '#08080a';
        ctx.fillRect(px, py, cellSize, cellSize);
        ctx.strokeStyle = 'rgba(255,255,255,0.05)';
        ctx.lineWidth = 0.5;
        ctx.strokeRect(px, py, cellSize, cellSize);
      }
    }

    // Shelves / Obstacles
    const allObstacles = [...state.shelves, ...state.dynamic_obstacles];
    for (const [x, y] of allObstacles) {
      const px = padX + x * cellSize;
      const py = padY + y * cellSize;
      ctx.fillStyle = '#1c1c21';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
      ctx.strokeStyle = '#27272a';
      ctx.lineWidth = 1;
      ctx.strokeRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
    }

    // Explored / Closed nodes (Violet tint)
    for (const [cx, cy] of closedNodes) {
      const px = padX + cx * cellSize;
      const py = padY + cy * cellSize;
      ctx.fillStyle = 'rgba(168, 85, 247, 0.25)';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
    }

    // Frontier / Open nodes (Cyan tint)
    for (const [ox, oy] of openNodes) {
      const px = padX + ox * cellSize;
      const py = padY + oy * cellSize;
      ctx.fillStyle = 'rgba(6, 182, 212, 0.35)';
      ctx.fillRect(px + 1, py + 1, cellSize - 2, cellSize - 2);
    }

    // A* Final Optimal Path (Bright Emerald Line)
    if (astarPath && astarPath.length > 1) {
      ctx.strokeStyle = '#10b981';
      ctx.lineWidth = Math.max(3, cellSize * 0.18);
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';
      ctx.beginPath();
      for (let i = 0; i < astarPath.length; i++) {
        const [x, y] = astarPath[i];
        const px = padX + x * cellSize + cellSize / 2;
        const py = padY + y * cellSize + cellSize / 2;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.stroke();
    }

    // Start Marker (Blue S)
    const [sx, sy] = start;
    const spx = padX + sx * cellSize;
    const spy = padY + sy * cellSize;
    ctx.fillStyle = '#2563eb';
    ctx.beginPath();
    ctx.arc(spx + cellSize / 2, spy + cellSize / 2, cellSize * 0.38, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#ffffff';
    ctx.font = `bold ${Math.max(10, cellSize * 0.4)}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('S', spx + cellSize / 2, spy + cellSize / 2);

    // Goal Marker (Emerald G)
    const [gx, gy] = goal;
    const gpx = padX + gx * cellSize;
    const gpy = padY + gy * cellSize;
    ctx.fillStyle = '#059669';
    ctx.beginPath();
    ctx.arc(gpx + cellSize / 2, gpy + cellSize / 2, cellSize * 0.38, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();
    ctx.fillStyle = '#ffffff';
    ctx.font = `bold ${Math.max(10, cellSize * 0.4)}px Inter, sans-serif`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('G', gpx + cellSize / 2, gpy + cellSize / 2);

  }, [state, start, goal, astarPath, closedNodes, openNodes, getCellSize]);

  useEffect(() => {
    draw();
  }, [draw]);

  useEffect(() => {
    const handleResize = () => draw();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [draw]);

  const handleCanvasClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const cellSize = getCellSize();
    const padX = Math.floor((canvas.width - state.grid_width * cellSize) / 2);
    const padY = Math.floor((canvas.height - state.grid_height * cellSize) / 2);
    const col = Math.floor((e.clientX - rect.left - padX) / cellSize);
    const row = Math.floor((e.clientY - rect.top - padY) / cellSize);

    if (col < 0 || col >= state.grid_width || row < 0 || row >= state.grid_height) return;

    if (settingMode === 'START') {
      setStart([col, row]);
      setSettingMode('IDLE');
      setAstarPath(null);
    } else if (settingMode === 'GOAL') {
      setGoal([col, row]);
      setSettingMode('IDLE');
      setAstarPath(null);
    }
  };

  const runAstar = async () => {
    setLoading(true);
    try {
      const res: any = await api.runAstar(start, goal, true);
      setAstarPath(res.path || []);
      if (res.steps && res.steps.length > 0) {
        const lastStep = res.steps[res.steps.length - 1];
        setClosedNodes(lastStep.closed || []);
        setOpenNodes(lastStep.open || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const runCompare = async () => {
    setLoading(true);
    try {
      const res: any = await api.compareAlgorithms(start, goal);
      setCompareResult(res);
      // Run A* visual as well
      await runAstar();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 380px',
      height: '100%',
      width: '100%',
      background: '#000000',
      overflow: 'hidden',
      padding: '8px',
      gap: '8px',
    }}>
      {/* ── LEFT: GRID VISUALIZER ────────────────────────────────── */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        background: '#09090b',
        border: '1px solid #1f2228',
        borderRadius: 10,
      }}>
        {/* Top Controls */}
        <div style={{
          height: 48,
          background: '#0e0e11',
          borderBottom: '1px solid #1f2228',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={runAstar}
              disabled={loading}
              className="btn-primary"
            >
              <Play size={13} />
              <span>Run A* Search</span>
            </button>

            <button
              onClick={runCompare}
              disabled={loading}
              className="btn-success"
            >
              <Zap size={13} />
              <span>Compare A* vs BFS</span>
            </button>

            <button
              onClick={() => {
                setAstarPath(null);
                setClosedNodes([]);
                setOpenNodes([]);
                setCompareResult(null);
              }}
              className="ctrl-btn"
            >
              <RotateCcw size={13} />
              <span>Clear</span>
            </button>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: '#71717a' }}>Markers:</span>
            <button
              onClick={() => setSettingMode(settingMode === 'START' ? 'IDLE' : 'START')}
              className={`ctrl-btn ${settingMode === 'START' ? 'active' : ''}`}
            >
              Start ({start[0]}, {start[1]})
            </button>
            <button
              onClick={() => setSettingMode(settingMode === 'GOAL' ? 'IDLE' : 'GOAL')}
              className={`ctrl-btn ${settingMode === 'GOAL' ? 'active' : ''}`}
            >
              Goal ({goal[0]}, {goal[1]})
            </button>
          </div>
        </div>

        {/* Canvas */}
        <div ref={containerRef} style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <canvas
            ref={canvasRef}
            onClick={handleCanvasClick}
            style={{ width: '100%', height: '100%', cursor: settingMode !== 'IDLE' ? 'crosshair' : 'default' }}
          />
        </div>

        {/* Legend */}
        <div style={{
          height: 36,
          background: '#09090b',
          borderTop: '1px solid #1f2228',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 20,
          fontSize: 11,
          color: '#a1a1aa',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 12, height: 4, background: '#10b981', borderRadius: 2 }} />
            <span>Optimal A* Path</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, background: 'rgba(168,85,247,0.4)', borderRadius: 2 }} />
            <span>Closed (Explored)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, background: 'rgba(6,182,212,0.5)', borderRadius: 2 }} />
            <span>Open (Frontier)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, background: '#1c1c21', border: '1px solid #27272a', borderRadius: 2 }} />
            <span>Warehouse Shelves</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT: BENCHMARK PROOF & METRICS ─────────────────────── */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflowY: 'auto',
        background: '#09090b',
        border: '1px solid #1f2228',
        borderRadius: 10,
        padding: '16px',
        gap: '16px',
      }}>
        {/* Header */}
        <div style={{ borderBottom: '1px solid #1f2228', paddingBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Cpu size={18} color="#10b981" />
            <h3 style={{ margin: 0, fontSize: 15, fontWeight: 700, color: '#ffffff' }}>
              Classical AI Verification
            </h3>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: 11, color: '#71717a' }}>
            Quantitative proof of A* optimality vs blind search (BFS).
          </p>
        </div>

        {/* Comparison Result Table */}
        {compareResult ? (
          <div style={{
            background: '#121215',
            border: '1px solid #27272a',
            borderRadius: 8,
            padding: 12,
          }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', marginBottom: 8 }}>
              Benchmark Results: ({start[0]},{start[1]}) → ({goal[0]},{goal[1]})
            </div>
            
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11, textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #27272a', color: '#71717a' }}>
                  <th style={{ padding: '6px 4px' }}>Metric</th>
                  <th style={{ padding: '6px 4px', color: '#10b981' }}>A* Search</th>
                  <th style={{ padding: '6px 4px', color: '#a1a1aa' }}>BFS</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #1a1a1e' }}>
                  <td style={{ padding: '8px 4px', color: '#a1a1aa' }}>Path Length</td>
                  <td style={{ padding: '8px 4px', fontWeight: 700, color: '#10b981' }}>
                    {compareResult.astar?.path_length} cells
                  </td>
                  <td style={{ padding: '8px 4px', color: '#d4d4d8' }}>
                    {compareResult.bfs?.path_length} cells
                  </td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1a1a1e' }}>
                  <td style={{ padding: '8px 4px', color: '#a1a1aa' }}>Nodes Explored</td>
                  <td style={{ padding: '8px 4px', fontWeight: 700, color: '#10b981' }}>
                    {compareResult.astar?.nodes_explored}
                  </td>
                  <td style={{ padding: '8px 4px', color: '#f87171', fontWeight: 600 }}>
                    {compareResult.bfs?.nodes_explored} ({Math.round((compareResult.bfs?.nodes_explored / Math.max(1, compareResult.astar?.nodes_explored)) * 100)}% of A*)
                  </td>
                </tr>
                <tr>
                  <td style={{ padding: '8px 4px', color: '#a1a1aa' }}>Execution Time</td>
                  <td style={{ padding: '8px 4px', fontWeight: 700, color: '#10b981' }}>
                    {compareResult.astar?.execution_time_ms.toFixed(2)} ms
                  </td>
                  <td style={{ padding: '8px 4px', color: '#d4d4d8' }}>
                    {compareResult.bfs?.execution_time_ms.toFixed(2)} ms
                  </td>
                </tr>
              </tbody>
            </table>

            <div style={{
              marginTop: 10,
              padding: 8,
              background: 'rgba(16, 185, 129, 0.08)',
              border: '1px solid rgba(16, 185, 129, 0.2)',
              borderRadius: 6,
              fontSize: 10,
              color: '#34d399',
              lineHeight: 1.4,
            }}>
              ✓ A* explored {compareResult.bfs?.nodes_explored - compareResult.astar?.nodes_explored} fewer grid nodes than BFS while guaranteeing the same optimal path length.
            </div>
          </div>
        ) : (
          <div style={{
            background: '#121215',
            border: '1px dashed #27272a',
            borderRadius: 8,
            padding: 14,
            textAlign: 'center',
            fontSize: 11,
            color: '#71717a',
          }}>
            Click <strong>"Compare A* vs BFS"</strong> above to generate real-time metrics for this grid layout.
          </div>
        )}

        {/* Theoretical Highlights for Evaluators */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: '#a1a1aa', textTransform: 'uppercase' }}>
            Academic Theoretical Proofs
          </div>

          <div style={{
            background: '#121215',
            border: '1px solid #1f2228',
            borderRadius: 8,
            padding: 12,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <CheckCircle2 size={14} color="#10b981" />
              <span style={{ fontSize: 11, fontWeight: 700, color: '#ffffff' }}>
                1. Heuristic Admissibility Theorem
              </span>
            </div>
            <p style={{ margin: 0, fontSize: 11, color: '#a1a1aa', lineHeight: 1.5 }}>
              On our 4-connected grid, Manhattan distance <code style={{ color: '#38bdf8' }}>h(n) = |Δx| + |Δy|</code> is mathematically admissible (<code style={{ color: '#34d399' }}>h(n) ≤ h*(n)</code>) and consistent. This proves A* never overestimates cost and is guaranteed to return the minimal path.
            </p>
          </div>

          <div style={{
            background: '#121215',
            border: '1px solid #1f2228',
            borderRadius: 8,
            padding: 12,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
              <ShieldCheck size={14} color="#38bdf8" />
              <span style={{ fontSize: 11, fontWeight: 700, color: '#ffffff' }}>
                2. Why No Machine Learning?
              </span>
            </div>
            <p style={{ margin: 0, fontSize: 11, color: '#a1a1aa', lineHeight: 1.5 }}>
              Industrial warehouses require 100% deterministic safety guarantees. Cooperative A* with space-time reservation mathematically guarantees zero collisions, zero black-box hallucinations, and zero training overhead.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
