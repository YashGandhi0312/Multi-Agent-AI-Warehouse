// ============================================================
// Task Panel — Left Sidebar: Pending/Active Tasks
// ============================================================

import React from 'react';
import type { Task } from '../types';
import { ClipboardList, CheckCircle, Clock, Loader } from 'lucide-react';

interface TaskPanelProps {
  tasks: Task[];
}

const statusIcon = (status: string) => {
  if (status === 'COMPLETED') return <CheckCircle size={11} style={{ color: '#4ade80' }} />;
  if (status === 'IN_PROGRESS') return <Loader size={11} style={{ color: '#22d3ee' }} />;
  if (status === 'ASSIGNED') return <Clock size={11} style={{ color: '#fb923c' }} />;
  return <Clock size={11} style={{ color: '#64748b' }} />;
};

export const TaskPanel: React.FC<TaskPanelProps> = ({ tasks }) => {
  const pending = tasks.filter(t => t.status === 'PENDING');
  const active = tasks.filter(t => ['ASSIGNED', 'IN_PROGRESS'].includes(t.status));
  const completed = tasks.filter(t => t.status === 'COMPLETED');

  const renderTask = (task: Task) => (
    <div
      key={task.task_id}
      style={{
        background: 'rgba(10,22,40,0.5)',
        border: `1px solid ${
          task.status === 'COMPLETED' ? 'rgba(34,197,94,0.15)' :
          task.status === 'IN_PROGRESS' ? 'rgba(6,182,212,0.2)' :
          task.status === 'ASSIGNED' ? 'rgba(249,115,22,0.2)' :
          'rgba(59,130,246,0.08)'
        }`,
        borderRadius: 6, padding: '7px 10px', marginBottom: 4,
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
        {statusIcon(task.status)}
        <span style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8' }}>
          {task.task_id}
        </span>
        <span style={{
          marginLeft: 'auto', fontSize: 10, color: '#475569',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          {task.package_id}
        </span>
      </div>
      <div style={{ fontSize: 10, color: '#475569', display: 'flex', gap: 6 }}>
        <span>
          ({task.pickup_location[0]},{task.pickup_location[1]})
        </span>
        <span>→</span>
        <span>
          ({task.delivery_station[0]},{task.delivery_station[1]})
        </span>
      </div>
      {task.assigned_robot && (
        <div style={{ fontSize: 10, color: '#60a5fa', marginTop: 2 }}>
          → {task.assigned_robot}
          {task.estimated_cost > 0 && (
            <span style={{ color: '#475569' }}> ({task.estimated_cost.toFixed(0)} est.)</span>
          )}
        </div>
      )}
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid rgba(59,130,246,0.1)',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <ClipboardList size={14} style={{ color: '#60a5fa' }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>Tasks</span>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
          <span style={{
            fontSize: 9, padding: '1px 6px', borderRadius: 10,
            background: 'rgba(249,115,22,0.15)', color: '#fb923c',
            border: '1px solid rgba(249,115,22,0.2)',
          }}>
            {pending.length + active.length} active
          </span>
          <span style={{
            fontSize: 9, padding: '1px 6px', borderRadius: 10,
            background: 'rgba(34,197,94,0.1)', color: '#4ade80',
            border: '1px solid rgba(34,197,94,0.2)',
          }}>
            {completed.length} done
          </span>
        </div>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', padding: '8px' }}>
        {active.length > 0 && (
          <>
            <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Active
            </div>
            {active.map(renderTask)}
          </>
        )}

        {pending.length > 0 && (
          <>
            <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginBottom: 4, marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Pending
            </div>
            {pending.map(renderTask)}
          </>
        )}

        {completed.length > 0 && (
          <>
            <div style={{ fontSize: 10, color: '#475569', fontWeight: 600, marginBottom: 4, marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Completed
            </div>
            {completed.slice(-5).map(renderTask)}
          </>
        )}
      </div>
    </div>
  );
};
