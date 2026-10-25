// ============================================================
// Control Panel — Simulation Controls and Environment Editing
// ============================================================

import React from 'react';
import type { InteractionMode } from '../types';
import {
  Play, Pause, RotateCcw, StepForward, Zap,
  Bot, Package, Square, Eraser, MousePointer2,
  Gauge
} from 'lucide-react';
import * as api from '../services/api';

interface ControlPanelProps {
  isRunning: boolean;
  speed: number;
  interactionMode: InteractionMode;
  onModeChange: (mode: InteractionMode) => void;
  onStateChange: () => void;
}

const SPEEDS = [0.5, 1, 2, 4];

export const ControlPanel: React.FC<ControlPanelProps> = ({
  isRunning,
  speed,
  interactionMode,
  onModeChange,
  onStateChange,
}) => {

  const handleStart = async () => {
    try {
      await api.simulationControl('start');
      onStateChange();
    } catch (e) { console.error(e); }
  };

  const handlePause = async () => {
    try {
      await api.simulationControl('pause');
      onStateChange();
    } catch (e) { console.error(e); }
  };

  const handleReset = async () => {
    try {
      await api.simulationControl('reset');
      onStateChange();
    } catch (e) { console.error(e); }
  };

  const handleStep = async () => {
    try {
      await api.simulationControl('step');
      onStateChange();
    } catch (e) { console.error(e); }
  };

  const handleSpeed = async (s: number) => {
    try {
      await api.setSimulationSpeed(s);
      onStateChange();
    } catch (e) { console.error(e); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10, padding: '12px 14px' }}>
      {/* Playback Controls */}
      <div>
        <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Simulation
        </div>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {!isRunning ? (
            <button id="btn-start" className="btn-success" onClick={handleStart} style={{ flex: 1, justifyContent: 'center', padding: '8px 10px' }}>
              <Play size={13} /> Start
            </button>
          ) : (
            <button id="btn-pause" className="btn-warning" onClick={handlePause} style={{ flex: 1, justifyContent: 'center', padding: '8px 10px' }}>
              <Pause size={13} /> Pause
            </button>
          )}
          <button id="btn-step" className="btn-ghost" onClick={handleStep} title="Step forward">
            <StepForward size={13} />
          </button>
          <button id="btn-reset" className="btn-danger" onClick={handleReset} style={{ justifyContent: 'center', padding: '8px 10px' }}>
            <RotateCcw size={13} />
          </button>
        </div>
      </div>

      {/* Speed Controls */}
      <div>
        <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: 4 }}>
          <Gauge size={10} /> Speed: {speed}×
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {SPEEDS.map(s => (
            <button
              key={s}
              id={`btn-speed-${s}`}
              className={`btn-ghost ${speed === s ? 'active' : ''}`}
              onClick={() => handleSpeed(s)}
              style={{ flex: 1, justifyContent: 'center', padding: '5px 4px', fontSize: 11 }}
            >
              {s}×
            </button>
          ))}
        </div>
      </div>

      {/* Edit Mode */}
      <div>
        <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Edit Mode
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {[
            { mode: 'SELECT' as InteractionMode, label: 'Select', icon: <MousePointer2 size={11} />, color: '#60a5fa' },
            { mode: 'ADD_ROBOT' as InteractionMode, label: 'Add Robot', icon: <Bot size={11} />, color: '#4ade80' },
            { mode: 'ADD_PACKAGE_PICKUP' as InteractionMode, label: 'Add Package', icon: <Package size={11} />, color: '#f59e0b' },
            { mode: 'ADD_OBSTACLE' as InteractionMode, label: 'Add Obstacle', icon: <Square size={11} />, color: '#ef4444' },
            { mode: 'REMOVE_OBSTACLE' as InteractionMode, label: 'Remove Obstacle', icon: <Eraser size={11} />, color: '#a855f7' },
          ].map(item => (
            <button
              key={item.mode}
              id={`btn-mode-${item.mode.toLowerCase()}`}
              className={`btn-ghost ${interactionMode === item.mode ? 'active' : ''}`}
              onClick={() => onModeChange(item.mode)}
              style={{ justifyContent: 'flex-start', gap: 8 }}
            >
              <span style={{ color: item.color }}>{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
