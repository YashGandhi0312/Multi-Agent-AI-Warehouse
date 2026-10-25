// ============================================================
// Simplified Dashboard — Focused for External Demonstration
// Theme: Sleek Pitch Black (#000000)
// ============================================================

import React, { useState, useCallback } from 'react';
import type { WarehouseState, InteractionMode } from '../types';
import { WarehouseCanvas } from '../components/WarehouseCanvas';
import * as api from '../services/api';
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  PlusCircle,
  Package as PackageIcon,
  MousePointer,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Bot
} from 'lucide-react';

interface DashboardProps {
  state: WarehouseState;
  onRefresh: () => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ state, onRefresh }) => {
  const [interactionMode, setInteractionMode] = useState<InteractionMode>('SELECT');
  const [pendingPickup, setPendingPickup] = useState<[number, number] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  const notify = (msg: string) => {
    setStatusMsg(msg);
    setTimeout(() => setStatusMsg(null), 3000);
  };

  const showError = (msg: string) => {
    setError(msg);
    setTimeout(() => setError(null), 3000);
  };

  const handleCellClick = useCallback(async (x: number, y: number) => {
    const pos: [number, number] = [x, y];

    try {
      if (interactionMode === 'ADD_OBSTACLE') {
        await api.addObstacle(pos);
        notify(`Obstacle placed at (${x}, ${y}). Robots will dynamically replan!`);
        onRefresh();
      } else if (interactionMode === 'REMOVE_OBSTACLE') {
        await api.removeObstacle(pos);
        onRefresh();
      } else if (interactionMode === 'ADD_PACKAGE_PICKUP') {
        setPendingPickup(pos);
        setInteractionMode('ADD_PACKAGE_DELIVERY');
        notify(`Pickup set at (${x}, ${y}). Now click delivery station!`);
      } else if (interactionMode === 'ADD_PACKAGE_DELIVERY') {
        if (pendingPickup) {
          await api.addPackage(pendingPickup, pos);
          setPendingPickup(null);
          setInteractionMode('SELECT');
          notify(`Package created! Dispatcher will assign to nearest idle robot.`);
          onRefresh();
        }
      }
    } catch (e: any) {
      showError(e.message || 'Action failed');
    }
  }, [interactionMode, pendingPickup, onRefresh]);

  const handleTogglePlay = async () => {
    try {
      await api.simulationControl(state.is_running ? 'pause' : 'start');
      onRefresh();
    } catch (e: any) {
      showError(e.message || 'Control failed');
    }
  };

  const handleStep = async () => {
    try {
      await api.simulationControl('step');
      onRefresh();
    } catch (e: any) {
      showError(e.message || 'Step failed');
    }
  };

  const handleReset = async () => {
    try {
      await api.simulationControl('reset');
      onRefresh();
      notify('Warehouse reset to initial state');
    } catch (e: any) {
      showError(e.message || 'Reset failed');
    }
  };

  const handleSpeed = async (speed: number) => {
    try {
      await api.setSimulationSpeed(speed);
      onRefresh();
    } catch (e: any) {
      showError(e.message || 'Speed change failed');
    }
  };

  const stats = state.statistics;
  const recentLogs = state.event_logs?.slice(-8).reverse() || [];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '1fr 340px',
      height: '100%',
      width: '100%',
      background: '#000000',
      overflow: 'hidden',
      padding: '8px',
      gap: '8px',
    }}>
      {/* Toast Messages */}
      {statusMsg && (
        <div style={{
          position: 'fixed', top: 58, left: '50%', transform: 'translateX(-50%)',
          background: '#18181b', border: '1px solid #10b981',
          borderRadius: 8, padding: '7px 16px', color: '#34d399',
          fontSize: 12, zIndex: 1000, fontWeight: 500, boxShadow: '0 4px 15px rgba(0,0,0,0.8)'
        }}>
          ✓ {statusMsg}
        </div>
      )}
      {error && (
        <div style={{
          position: 'fixed', top: 58, left: '50%', transform: 'translateX(-50%)',
          background: '#270a0a', border: '1px solid #ef4444',
          borderRadius: 8, padding: '7px 16px', color: '#fca5a5',
          fontSize: 12, zIndex: 1000, fontWeight: 500,
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* ── LEFT: MAIN SIMULATION CANVAS & ESSENTIAL CONTROLS ──────── */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        background: '#09090b',
        border: '1px solid #1f2228',
        borderRadius: 10,
      }}>
        {/* Streamlined Top Control Bar */}
        <div style={{
          height: 48,
          background: '#0e0e11',
          borderBottom: '1px solid #1f2228',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          flexShrink: 0,
          gap: 12,
        }}>
          {/* Playback Controls */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <button
              onClick={handleTogglePlay}
              className={state.is_running ? 'btn-danger' : 'btn-success'}
              style={{ padding: '6px 14px' }}
            >
              {state.is_running ? (
                <>
                  <Pause size={14} />
                  <span>Pause</span>
                </>
              ) : (
                <>
                  <Play size={14} />
                  <span>Start</span>
                </>
              )}
            </button>

            <button
              onClick={handleStep}
              disabled={state.is_running}
              className="ctrl-btn"
              title="Advance 1 AI planning step"
            >
              <SkipForward size={14} />
              <span>Step</span>
            </button>

            <button
              onClick={handleReset}
              className="ctrl-btn"
              title="Reset Warehouse"
            >
              <RotateCcw size={14} />
              <span>Reset</span>
            </button>

            {/* Speed Selector */}
            <div style={{ display: 'flex', background: '#141417', border: '1px solid #27272a', borderRadius: 6, padding: 2, marginLeft: 6 }}>
              {[1, 2, 5].map(s => (
                <button
                  key={s}
                  onClick={() => handleSpeed(s)}
                  style={{
                    border: 'none',
                    background: state.speed === s ? '#27272a' : 'transparent',
                    color: state.speed === s ? '#ffffff' : '#71717a',
                    borderRadius: 4,
                    padding: '2px 8px',
                    fontSize: 11,
                    fontWeight: 600,
                    cursor: 'pointer',
                  }}
                >
                  {s}x
                </button>
              ))}
            </div>
          </div>

          {/* Interactive Tools for Evaluator Testing */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 11, color: '#71717a', marginRight: 4 }}>Interactive:</span>
            
            <button
              onClick={() => {
                setInteractionMode('SELECT');
                setPendingPickup(null);
              }}
              className={`ctrl-btn ${interactionMode === 'SELECT' ? 'active' : ''}`}
            >
              <MousePointer size={13} />
              <span>Select</span>
            </button>

            <button
              onClick={() => setInteractionMode(interactionMode === 'ADD_OBSTACLE' ? 'SELECT' : 'ADD_OBSTACLE')}
              className={`ctrl-btn ${interactionMode === 'ADD_OBSTACLE' ? 'active' : ''}`}
              title="Click on any grid cell to place an obstacle and watch robots replan!"
            >
              <PlusCircle size={13} color="#f87171" />
              <span>+ Obstacle</span>
            </button>

            <button
              onClick={() => setInteractionMode(interactionMode === 'ADD_PACKAGE_PICKUP' ? 'SELECT' : 'ADD_PACKAGE_PICKUP')}
              className={`ctrl-btn ${interactionMode === 'ADD_PACKAGE_PICKUP' || interactionMode === 'ADD_PACKAGE_DELIVERY' ? 'active' : ''}`}
              title="Click grid to drop a new package task"
            >
              <PackageIcon size={13} color="#fbbf24" />
              <span>+ Package</span>
            </button>
          </div>

          {/* Step Pill */}
          <div style={{
            background: '#141417',
            border: '1px solid #27272a',
            borderRadius: 6,
            padding: '4px 10px',
            fontSize: 11,
            color: '#a1a1aa',
            fontFamily: 'monospace',
          }}>
            Step <strong style={{ color: '#ffffff' }}>#{state.simulation_step}</strong>
          </div>
        </div>

        {/* Center: Canvas */}
        <div style={{ flex: 1, position: 'relative', overflow: 'hidden' }}>
          <WarehouseCanvas
            state={state}
            interactionMode={interactionMode}
            selectedRobot={null}
            onCellClick={handleCellClick}
            onRobotClick={() => {}}
            pendingPackagePickup={pendingPickup}
          />
        </div>

        {/* Bottom Legend Bar — Explains symbols to evaluator */}
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
            <span style={{ width: 10, height: 10, borderRadius: '50%', background: '#3b82f6', border: '1px solid #ffffff' }} />
            <span>Robot & Path</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, background: '#f59e0b', borderRadius: 2 }} />
            <span>Package Pickup</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, background: '#10b981', borderRadius: 2 }} />
            <span>Delivery Station</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, background: '#27272a', border: '1px solid #3f3f46', borderRadius: 2 }} />
            <span>Shelf Obstacle</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ width: 10, height: 10, background: '#ef4444', borderRadius: 2 }} />
            <span>Dynamic Block</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT: AI DECISION EXPLAINER & FLEET STATUS ────────────── */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        overflow: 'hidden',
        background: '#09090b',
        border: '1px solid #1f2228',
        borderRadius: 10,
        gap: 1,
      }}>
        {/* Header */}
        <div style={{
          padding: '12px 14px',
          background: '#0e0e11',
          borderBottom: '1px solid #1f2228',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
            <Sparkles size={16} color="#38bdf8" />
            <h3 style={{ margin: 0, fontSize: 13, fontWeight: 700, color: '#ffffff' }}>
              AI Decision Engine
            </h3>
          </div>
          <span style={{
            fontSize: 10,
            background: 'rgba(56, 189, 248, 0.1)',
            color: '#38bdf8',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: 4,
            padding: '2px 6px',
            fontWeight: 600,
          }}>
            Classical AI
          </span>
        </div>

        {/* 1. Essential Metrics Bar */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr 1fr',
          gap: 6,
          padding: '10px',
          background: '#0e0e11',
          borderBottom: '1px solid #1f2228',
        }}>
          <div style={{
            background: '#141417',
            border: '1px solid #27272a',
            borderRadius: 6,
            padding: '6px 8px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#10b981' }}>
              {stats.completed_deliveries}
            </div>
            <div style={{ fontSize: 10, color: '#71717a' }}>Deliveries</div>
          </div>

          <div style={{
            background: '#141417',
            border: '1px solid #27272a',
            borderRadius: 6,
            padding: '6px 8px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#38bdf8' }}>
              {stats.conflicts_resolved}
            </div>
            <div style={{ fontSize: 10, color: '#71717a' }}>Safe Yields</div>
          </div>

          <div style={{
            background: '#141417',
            border: '1px solid #27272a',
            borderRadius: 6,
            padding: '6px 8px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 16, fontWeight: 800, color: '#eab308' }}>
              {stats.replan_count}
            </div>
            <div style={{ fontSize: 10, color: '#71717a' }}>Replans</div>
          </div>
        </div>

        {/* 2. Active Robots List */}
        <div style={{ padding: '10px 12px', borderBottom: '1px solid #1f2228' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Robot Fleet ({state.robots.length})
            </span>
            <span style={{ fontSize: 10, color: '#71717a' }}>Space-Time CA*</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {state.robots.map(r => (
              <div
                key={r.robot_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  background: '#141417',
                  border: '1px solid #27272a',
                  borderRadius: 6,
                  padding: '6px 10px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{
                    width: 14,
                    height: 14,
                    borderRadius: '50%',
                    background: r.color,
                    boxShadow: `0 0 6px ${r.color}80`,
                  }} />
                  <span style={{ fontSize: 12, fontWeight: 700, color: '#ffffff' }}>
                    {r.robot_id}
                  </span>
                  <span style={{ fontSize: 10, color: '#71717a', fontFamily: 'monospace' }}>
                    ({r.position[0]}, {r.position[1]})
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  {r.has_package && (
                    <span style={{
                      fontSize: 9,
                      background: 'rgba(245, 158, 11, 0.15)',
                      color: '#fbbf24',
                      border: '1px solid rgba(245, 158, 11, 0.3)',
                      borderRadius: 3,
                      padding: '1px 4px',
                      fontWeight: 600,
                    }}>
                      📦 {r.package_id}
                    </span>
                  )}
                  <span className={`state-badge state-${r.state}`}>
                    {r.state}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 3. Live AI Decision Log (Plain English for External Evaluator) */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '10px 12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
            <Bot size={14} color="#a1a1aa" />
            <span style={{ fontSize: 11, fontWeight: 700, color: '#a1a1aa', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Live Decision Explanations
            </span>
          </div>

          <div style={{
            flex: 1,
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}>
            {recentLogs.length > 0 ? (
              recentLogs.map((log, idx) => (
                <div
                  key={idx}
                  style={{
                    background: '#121215',
                    borderLeft: `3px solid ${
                      log.event_type.includes('COLLISION') || log.event_type.includes('WAIT') ? '#f59e0b' :
                      log.event_type.includes('REPLAN') ? '#a855f7' :
                      log.event_type.includes('DELIVERY') ? '#10b981' :
                      '#3b82f6'
                    }`,
                    border: '1px solid #1f2228',
                    borderLeftWidth: 3,
                    borderRadius: 4,
                    padding: '6px 8px',
                    fontSize: 11,
                    color: '#d4d4d8',
                    lineHeight: 1.4,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', color: '#71717a', fontSize: 9, marginBottom: 2 }}>
                    <span>Step #{log.step}</span>
                    <span style={{ fontWeight: 600, color: '#a1a1aa' }}>{log.event_type}</span>
                  </div>
                  <div>{log.message}</div>
                </div>
              ))
            ) : (
              <div style={{ fontSize: 11, color: '#52525b', textAlign: 'center', marginTop: 20 }}>
                Press <strong>Start</strong> or <strong>Step</strong> to observe AI decisions in real-time.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
