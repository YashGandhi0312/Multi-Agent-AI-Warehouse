// ============================================================
// Robot Panel — Left Sidebar: Robot Status List
// ============================================================

import React from 'react';
import type { Robot, Task } from '../types';
import { Bot, Package, MapPin, Activity } from 'lucide-react';

interface RobotPanelProps {
  robots: Robot[];
  tasks: Task[];
  selectedRobot: string | null;
  onSelectRobot: (robotId: string | null) => void;
  onRemoveRobot: (robotId: string) => void;
}

export const RobotPanel: React.FC<RobotPanelProps> = ({
  robots, tasks, selectedRobot, onSelectRobot, onRemoveRobot
}) => {
  const taskMap = Object.fromEntries(tasks.map(t => [t.task_id, t]));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid rgba(59,130,246,0.1)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <Bot size={14} style={{ color: '#60a5fa' }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
          Robots ({robots.length})
        </span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {robots.length === 0 && (
          <div style={{ color: '#475569', fontSize: 12, textAlign: 'center', marginTop: 20 }}>
            No robots in simulation
          </div>
        )}
        {robots.map(robot => {
          const task = robot.task_id ? taskMap[robot.task_id] : null;
          const isSelected = selectedRobot === robot.robot_id;
          return (
            <div
              key={robot.robot_id}
              onClick={() => onSelectRobot(isSelected ? null : robot.robot_id)}
              style={{
                background: isSelected
                  ? 'rgba(59,130,246,0.12)'
                  : 'rgba(15,32,64,0.5)',
                border: `1px solid ${isSelected ? robot.color + '60' : 'rgba(59,130,246,0.1)'}`,
                borderRadius: 8, padding: '10px 12px', marginBottom: 6,
                cursor: 'pointer', transition: 'all 0.2s',
              }}
            >
              {/* Robot header */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: robot.color + '30',
                  border: `2px solid ${robot.color}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 10, fontWeight: 700, color: robot.color,
                  flexShrink: 0,
                }}>
                  {robot.robot_id}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: '#e2e8f0' }}>
                    {robot.robot_id}
                  </div>
                  <span className={`state-badge state-${robot.state}`}>
                    {robot.state.replace(/_/g, ' ')}
                  </span>
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); onRemoveRobot(robot.robot_id); }}
                  style={{
                    background: 'none', border: 'none', color: '#475569',
                    cursor: 'pointer', fontSize: 14, padding: '2px',
                    lineHeight: 1,
                  }}
                  title="Remove robot"
                >
                  ×
                </button>
              </div>

              {isSelected && (
                <div style={{ fontSize: 11, color: '#64748b', display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <MapPin size={10} /> Pos
                    </span>
                    <span style={{ color: '#94a3b8', fontFamily: 'JetBrains Mono, monospace' }}>
                      ({robot.position[0]}, {robot.position[1]})
                    </span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Activity size={10} /> Traveled
                    </span>
                    <span style={{ color: '#94a3b8' }}>{robot.distance_traveled} steps</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Deliveries</span>
                    <span style={{ color: '#4ade80' }}>{robot.tasks_completed}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Wait steps</span>
                    <span style={{ color: '#fbbf24' }}>{robot.wait_steps}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>Replans</span>
                    <span style={{ color: '#c084fc' }}>{robot.replan_count}</span>
                  </div>
                  {robot.has_package && (
                    <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
                      <Package size={10} style={{ color: '#f59e0b' }} />
                      <span style={{ color: '#f59e0b' }}>Carrying: {robot.package_id}</span>
                    </div>
                  )}
                  {task && (
                    <div style={{
                      marginTop: 4, padding: '4px 8px', borderRadius: 4,
                      background: 'rgba(59,130,246,0.08)',
                      border: '1px solid rgba(59,130,246,0.15)',
                    }}>
                      <div style={{ color: '#60a5fa', fontSize: 10 }}>Task: {task.task_id}</div>
                      <div style={{ color: '#475569', fontSize: 10 }}>
                        {task.pickup_location[0]},{task.pickup_location[1]} →{' '}
                        {task.delivery_station[0]},{task.delivery_station[1]}
                      </div>
                      {robot.path.length > 0 && (
                        <div style={{ color: '#22d3ee', fontSize: 10 }}>
                          Remaining: {robot.path.length} steps
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
