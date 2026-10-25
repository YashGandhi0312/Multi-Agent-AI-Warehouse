// ============================================================
// Multi-Agent AI Warehouse Management System
// Theme: Pitch Black (#000000)
// Simplified and Focused for External Demonstration
// ============================================================

import React, { useState } from 'react';
import { useSimulationWebSocket } from './hooks/useSimulation';
import { Dashboard } from './pages/Dashboard';
import { AlgorithmExplorer } from './pages/AlgorithmExplorer';
import * as api from './services/api';
import {
  Boxes,
  Cpu,
  RotateCcw,
  Sparkles,
  ChevronDown
} from 'lucide-react';

type Tab = 'simulation' | 'benchmark';

export const App: React.FC = () => {
  const { state, connected, refresh } = useSimulationWebSocket();
  const [currentTab, setCurrentTab] = useState<Tab>('simulation');
  const [loadingScenario, setLoadingScenario] = useState(false);
  const [scenarioMenuOpen, setScenarioMenuOpen] = useState(false);

  const handleSelectScenario = async (scenarioId: string) => {
    setLoadingScenario(true);
    setScenarioMenuOpen(false);
    try {
      await api.loadScenario(scenarioId);
      refresh();
    } catch (err: any) {
      alert(`Failed to load scenario: ${err.message}`);
    } finally {
      setLoadingScenario(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      width: '100vw',
      background: '#000000',
      color: '#f4f4f5',
      overflow: 'hidden',
      fontFamily: "'Inter', sans-serif",
    }}>
      {/* ── CLEAN TOP HEADER ───────────────────────────────────────── */}
      <header style={{
        height: 50,
        background: '#09090b',
        borderBottom: '1px solid #1f2228',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        zIndex: 50,
        flexShrink: 0,
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{
            width: 28,
            height: 28,
            borderRadius: 6,
            background: '#18181b',
            border: '1px solid #27272a',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}>
            <Boxes size={16} color="#38bdf8" />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: '-0.01em', color: '#ffffff' }}>
                Multi-Agent AI Warehouse
              </span>
              <span style={{
                fontSize: 9,
                fontWeight: 700,
                background: '#18181b',
                color: '#38bdf8',
                border: '1px solid #27272a',
                borderRadius: 4,
                padding: '1px 5px',
              }}>
                Classical AI • No ML
              </span>
            </div>
          </div>
        </div>

        {/* Center: 2 Essential Tabs Only */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <button
            onClick={() => setCurrentTab('simulation')}
            className={`nav-tab ${currentTab === 'simulation' ? 'active' : ''}`}
          >
            <Boxes size={14} />
            <span>Warehouse Simulation</span>
          </button>

          <button
            onClick={() => setCurrentTab('benchmark')}
            className={`nav-tab ${currentTab === 'benchmark' ? 'active' : ''}`}
          >
            <Cpu size={14} />
            <span>A* vs BFS Benchmark</span>
          </button>
        </nav>

        {/* Right: Demo Scenarios Selector & Live Indicator */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Preset Scenarios Menu */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={() => setScenarioMenuOpen(!scenarioMenuOpen)}
              disabled={loadingScenario}
              className="ctrl-btn"
              style={{
                background: '#121215',
                borderColor: '#27272a',
                color: '#38bdf8',
                fontWeight: 600,
              }}
            >
              <Sparkles size={13} color="#38bdf8" />
              <span>{loadingScenario ? 'Loading...' : 'Demo Scenarios'}</span>
              <ChevronDown size={12} />
            </button>

            {scenarioMenuOpen && (
              <div style={{
                position: 'absolute',
                top: '115%',
                right: 0,
                width: 260,
                background: '#09090b',
                border: '1px solid #27272a',
                borderRadius: 8,
                boxShadow: '0 10px 30px rgba(0,0,0,0.9)',
                padding: 6,
                zIndex: 100,
                display: 'flex',
                flexDirection: 'column',
                gap: 4,
              }}>
                <div style={{ fontSize: 10, color: '#71717a', padding: '4px 8px', fontWeight: 600, textTransform: 'uppercase' }}>
                  Select Demonstration
                </div>
                <button
                  onClick={() => handleSelectScenario('default')}
                  className="ctrl-btn"
                  style={{ textAlign: 'left', fontSize: 11, padding: '7px 10px', justifyContent: 'flex-start' }}
                >
                  🏢 Default Warehouse (5 Robots)
                </button>
                <button
                  onClick={() => handleSelectScenario('basic_delivery')}
                  className="ctrl-btn"
                  style={{ textAlign: 'left', fontSize: 11, padding: '7px 10px', justifyContent: 'flex-start' }}
                >
                  📦 Scenario A: Multi-Robot Delivery
                </button>
                <button
                  onClick={() => handleSelectScenario('collision_avoidance')}
                  className="ctrl-btn"
                  style={{ textAlign: 'left', fontSize: 11, padding: '7px 10px', justifyContent: 'flex-start' }}
                >
                  ⚡ Scenario B: Corridor Collision Avoidance
                </button>
                <button
                  onClick={() => handleSelectScenario('dynamic_obstacle')}
                  className="ctrl-btn"
                  style={{ textAlign: 'left', fontSize: 11, padding: '7px 10px', justifyContent: 'flex-start' }}
                >
                  🚧 Scenario C: Dynamic Obstacle Replanning
                </button>
              </div>
            )}
          </div>

          {/* Connection Status Pill */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: '#121215',
            border: '1px solid #27272a',
            borderRadius: 16,
            padding: '3px 8px',
            fontSize: 10,
            color: connected ? '#10b981' : '#f87171',
          }}>
            <span className="live-dot" />
            <span style={{ fontWeight: 600 }}>{connected ? 'CONNECTED' : 'CONNECTING'}</span>
          </div>

          {/* Refresh Button */}
          <button
            onClick={() => refresh()}
            className="ctrl-btn"
            title="Refresh State"
            style={{ padding: '5px 7px' }}
          >
            <RotateCcw size={12} />
          </button>
        </div>
      </header>

      {/* ── MAIN CONTENT ───────────────────────────────────────────── */}
      <main style={{ flex: 1, overflow: 'hidden', position: 'relative', background: '#000000' }}>
        {!state ? (
          <div style={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            color: '#71717a',
          }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: '50%',
              border: '2px solid #27272a',
              borderTopColor: '#38bdf8',
              animation: 'spin 1s linear infinite',
            }} />
            <div style={{ fontSize: 13, color: '#a1a1aa' }}>
              Connecting to Warehouse Simulation Server...
            </div>
          </div>
        ) : (
          <>
            {currentTab === 'simulation' && (
              <Dashboard state={state} onRefresh={refresh} />
            )}

            {currentTab === 'benchmark' && (
              <AlgorithmExplorer state={state} />
            )}
          </>
        )}
      </main>
    </div>
  );
};

export default App;
