// ============================================================
// Analytics & Benchmark Page — Classical AI Performance Analysis
// ============================================================

import React, { useState, useEffect } from 'react';
import type { WarehouseState } from '../types';
import * as api from '../services/api';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend
} from 'recharts';
import { Activity, ShieldCheck, Zap, GitBranch, Cpu, Award } from 'lucide-react';

interface AnalyticsProps {
  state: WarehouseState;
}

export const Analytics: React.FC<AnalyticsProps> = ({ state }) => {
  const [costMatrixData, setCostMatrixData] = useState<any>(null);
  const [loadingMatrix, setLoadingMatrix] = useState(false);

  useEffect(() => {
    const fetchMatrix = async () => {
      setLoadingMatrix(true);
      try {
        const data = await api.getCostMatrix();
        setCostMatrixData(data);
      } catch {
        // matrix might be empty if no idle robots or pending tasks
      } finally {
        setLoadingMatrix(false);
      }
    };
    fetchMatrix();
  }, [state.simulation_step]);

  const robotPerformanceData = state.robots.map(r => ({
    name: r.robot_id,
    distance: r.distance_traveled,
    completed: r.tasks_completed,
    replan: r.replan_count,
    waiting: r.wait_steps,
    color: r.color,
  }));

  const stats = state.statistics;
  const resolutionRate = stats.conflicts_detected > 0
    ? ((stats.conflicts_resolved / stats.conflicts_detected) * 100).toFixed(1)
    : '100.0';

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 16,
      height: '100%',
      overflowY: 'auto',
      padding: '16px 20px',
    }}>
      {/* Top Banner / Summary */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30,58,138,0.3) 0%, rgba(15,23,42,0.6) 100%)',
        border: '1px solid rgba(59,130,246,0.3)',
        borderRadius: 12,
        padding: '16px 20px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Activity size={20} color="#60a5fa" />
            <h2 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#f1f5f9' }}>
              Classical AI Performance & Benchmark Analytics
            </h2>
          </div>
          <p style={{ margin: '4px 0 0 0', fontSize: 12, color: '#94a3b8' }}>
            Quantitative evaluation of deterministic multi-agent search, cooperative space-time reservation, and task assignment optimality.
          </p>
        </div>
        <div style={{
          display: 'flex',
          gap: 12,
        }}>
          <div style={{
            background: 'rgba(15,23,42,0.8)',
            border: '1px solid rgba(59,130,246,0.2)',
            borderRadius: 8,
            padding: '6px 14px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>Simulation Step</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#38bdf8', fontFamily: 'monospace' }}>
              #{state.simulation_step}
            </div>
          </div>
          <div style={{
            background: 'rgba(15,23,42,0.8)',
            border: '1px solid rgba(34,197,94,0.2)',
            borderRadius: 8,
            padding: '6px 14px',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 11, color: '#94a3b8' }}>Cooperative Safety</div>
            <div style={{ fontSize: 18, fontWeight: 800, color: '#4ade80' }}>
              {resolutionRate}%
            </div>
          </div>
        </div>
      </div>

      {/* KPI Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: 12,
      }}>
        <div className="glass-card" style={{ padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Total Deliveries Completed</span>
            <Award size={18} color="#eab308" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#facc15', marginTop: 4 }}>
            {stats.completed_deliveries}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            {stats.pending_deliveries} pending in queue
          </div>
        </div>

        <div className="glass-card" style={{ padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Cumulative Distance Traveled</span>
            <Zap size={18} color="#38bdf8" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#38bdf8', marginTop: 4 }}>
            {stats.total_distance} <span style={{ fontSize: 14, fontWeight: 500 }}>cells</span>
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            Avg {stats.average_delivery_steps.toFixed(1)} steps per completed task
          </div>
        </div>

        <div className="glass-card" style={{ padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Space-Time Conflicts Avoided</span>
            <ShieldCheck size={18} color="#4ade80" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#4ade80', marginTop: 4 }}>
            {stats.conflicts_resolved} / {stats.conflicts_detected}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            Reservation table preventions
          </div>
        </div>

        <div className="glass-card" style={{ padding: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 12, color: '#94a3b8' }}>Search Nodes Explored</span>
            <GitBranch size={18} color="#c084fc" />
          </div>
          <div style={{ fontSize: 26, fontWeight: 800, color: '#c084fc', marginTop: 4 }}>
            {stats.nodes_explored}
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            {stats.total_planning_time_ms.toFixed(1)} ms total planning compute
          </div>
        </div>
      </div>

      {/* Chart Section */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))',
        gap: 16,
      }}>
        {/* Robot Distance Traveled Chart */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0', margin: '0 0 12px 0' }}>
            Workload Distribution: Distance Traveled by Robot (Cells)
          </h3>
          <div style={{ height: 220, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={robotPerformanceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: 8,
                    fontSize: 12,
                    color: '#f8fafc',
                  }}
                />
                <Bar dataKey="distance" name="Distance (cells)" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                <Bar dataKey="waiting" name="Wait Steps" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Tasks Completed per Robot */}
        <div className="glass-card" style={{ padding: 16 }}>
          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#e2e8f0', margin: '0 0 12px 0' }}>
            Mission Throughput: Completed Tasks & Replans
          </h3>
          <div style={{ height: 220, width: '100%' }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={robotPerformanceData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="name" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{
                    background: '#0f172a',
                    borderColor: '#334155',
                    borderRadius: 8,
                    fontSize: 12,
                    color: '#f8fafc',
                  }}
                />
                <Legend wrapperStyle={{ fontSize: 11, paddingTop: 6 }} />
                <Bar dataKey="completed" name="Completed Deliveries" fill="#10b981" radius={[4, 4, 0, 0]} />
                <Bar dataKey="replan" name="Dynamic Replans" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Classical AI Theoretical Comparison Table */}
      <div className="glass-card" style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
          <Cpu size={18} color="#38bdf8" />
          <h3 style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
            Classical Graph Search & Multi-Agent Planning Algorithmic Comparison
          </h3>
        </div>
        <div style={{ overflowX: 'auto' }}>
          <table style={{
            width: '100%',
            borderCollapse: 'collapse',
            fontSize: 12,
            textAlign: 'left',
          }}>
            <thead>
              <tr style={{ background: 'rgba(30,41,59,0.7)', borderBottom: '1px solid rgba(59,130,246,0.2)' }}>
                <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Algorithm</th>
                <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Time Complexity</th>
                <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Space Complexity</th>
                <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Optimality Guarantee</th>
                <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Multi-Agent Coordination</th>
                <th style={{ padding: '8px 12px', color: '#94a3b8' }}>Role in this System</th>
              </tr>
            </thead>
            <tbody>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: '#60a5fa' }}>A* Search (Manhattan)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(b^d)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(b^d)</td>
                <td style={{ padding: '10px 12px', color: '#4ade80' }}>Guaranteed Optimal (h admissible)</td>
                <td style={{ padding: '10px 12px', color: '#94a3b8' }}>Single-agent baseline</td>
                <td style={{ padding: '10px 12px', color: '#cbd5e1' }}>Primary single-robot pathfinder</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: '#a78bfa' }}>Cooperative A* (CA*)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(k · b^d_max)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(W · H · T)</td>
                <td style={{ padding: '10px 12px', color: '#facc15' }}>Locally optimal per priority order</td>
                <td style={{ padding: '10px 12px', color: '#4ade80' }}>Space-Time Reservation Table</td>
                <td style={{ padding: '10px 12px', color: '#cbd5e1' }}>Prevents robot collisions & deadlock</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: '#94a3b8' }}>Breadth-First Search (BFS)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(V + E)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(V)</td>
                <td style={{ padding: '10px 12px', color: '#4ade80' }}>Optimal for uniform edge costs</td>
                <td style={{ padding: '10px 12px', color: '#ef4444' }}>None (uncoordinated)</td>
                <td style={{ padding: '10px 12px', color: '#cbd5e1' }}>Benchmark comparison in Explorer</td>
              </tr>
              <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: '#34d399' }}>Greedy Task Allocation</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(R · P · log P)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(R · P)</td>
                <td style={{ padding: '10px 12px', color: '#facc15' }}>Heuristic approximation</td>
                <td style={{ padding: '10px 12px', color: '#4ade80' }}>Centralized Task Dispatcher</td>
                <td style={{ padding: '10px 12px', color: '#cbd5e1' }}>Matches idle robots to nearest tasks</td>
              </tr>
              <tr>
                <td style={{ padding: '10px 12px', fontWeight: 600, color: '#fb923c' }}>Production Rule Engine</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(R · Rules)</td>
                <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>O(1)</td>
                <td style={{ padding: '10px 12px', color: '#4ade80' }}>Deterministic rule-based safety</td>
                <td style={{ padding: '10px 12px', color: '#4ade80' }}>Priority conflict resolution</td>
                <td style={{ padding: '10px 12px', color: '#cbd5e1' }}>Dynamic obstacle replanning & state machine</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Task Allocation Cost Matrix Live Inspection */}
      <div className="glass-card" style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Award size={18} color="#eab308" />
            <h3 style={{ fontSize: 14, fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
              Live Task Allocation Cost Matrix [C(r, p)]
            </h3>
          </div>
          <span style={{ fontSize: 11, color: '#64748b' }}>
            Cost = Manhattan(r, pickup) + Manhattan(pickup, delivery) / Priority
          </span>
        </div>

        {loadingMatrix ? (
          <div style={{ padding: '16px', textAlign: 'center', color: '#64748b', fontSize: 12 }}>
            Evaluating allocation matrix...
          </div>
        ) : costMatrixData && costMatrixData.matrix && costMatrixData.matrix.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, textAlign: 'center' }}>
              <thead>
                <tr style={{ background: 'rgba(30,41,59,0.7)', borderBottom: '1px solid rgba(59,130,246,0.2)' }}>
                  <th style={{ padding: '6px 12px', textAlign: 'left', color: '#94a3b8' }}>Robot \ Package</th>
                  {costMatrixData.packages.map((pkg: any) => (
                    <th key={pkg.package_id} style={{ padding: '6px 12px', color: '#38bdf8' }}>
                      {pkg.package_id} (Prio: {pkg.priority || 1})
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {costMatrixData.robots.map((robot: any, rIdx: number) => (
                  <tr key={robot.robot_id} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                    <td style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 600, color: '#f1f5f9' }}>
                      {robot.robot_id} @ ({robot.position[0]}, {robot.position[1]})
                    </td>
                    {costMatrixData.matrix[rIdx]?.map((cost: number, pIdx: number) => (
                      <td key={pIdx} style={{
                        padding: '8px 12px',
                        fontFamily: 'monospace',
                        color: cost < 15 ? '#4ade80' : cost < 30 ? '#facc15' : '#f87171',
                        fontWeight: 600,
                      }}>
                        {cost}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{
            padding: 16,
            background: 'rgba(15,23,42,0.4)',
            borderRadius: 8,
            border: '1px dashed rgba(255,255,255,0.1)',
            textAlign: 'center',
            color: '#94a3b8',
            fontSize: 12,
          }}>
            All robots are currently assigned or all warehouse packages have been dispatched! Create new packages on the Dashboard or switch scenarios to view dynamic re-allocation costs.
          </div>
        )}
      </div>
    </div>
  );
};
