// ============================================================
// Event Logs Panel — Real-time simulation activity log
// ============================================================

import React, { useEffect, useRef } from 'react';
import type { EventLog } from '../types';
import { Terminal, Trash2 } from 'lucide-react';

interface EventLogsProps {
  logs: EventLog[];
}

const EVENT_ICONS: Record<string, string> = {
  SYSTEM: '⚙️',
  TASK_ASSIGNED: '📋',
  PATH_PLANNED: '🗺️',
  PICKUP: '📦',
  DELIVERY: '✅',
  COLLISION_AVOIDED: '⚠️',
  SWAP_CONFLICT: '🔄',
  REPLAN: '🔁',
  REPLAN_TRIGGERED: '🔁',
  EMERGENCY_REPLAN: '🚨',
  BLOCKED: '🚫',
  OBSTACLE_ADDED: '🧱',
  OBSTACLE_REMOVED: '🔓',
  ROBOT_ADDED: '🤖',
  ROBOT_REMOVED: '❌',
  PACKAGE_ADDED: '📦',
  WAIT: '⏸️',
  SCENARIO_LOADED: '🎬',
  ALLOCATION_SEARCH: '🌳',
  PRIORITY_BACKTRACK: '🔀',
  BACKTRACK: '↩️',
  DEADLOCK_DETECTED: '⛓️',
};

export const EventLogs: React.FC<EventLogsProps> = ({ logs }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs.length]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 14px', borderBottom: '1px solid rgba(59,130,246,0.1)',
      }}>
        <Terminal size={14} style={{ color: '#60a5fa' }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8', flex: 1 }}>
          Activity Log
        </span>
        <span style={{
          fontSize: 10, color: '#475569',
          fontFamily: 'JetBrains Mono, monospace',
        }}>
          {logs.length} events
        </span>
      </div>

      <div style={{
        flex: 1, overflowY: 'auto', padding: '6px 8px',
        display: 'flex', flexDirection: 'column', gap: 2,
      }}>
        {logs.length === 0 ? (
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            height: '100%', color: '#334155', fontSize: 12,
          }}>
            Simulation not started yet
          </div>
        ) : (
          logs.slice(-150).map((log, idx) => (
            <div
              key={idx}
              className={`log-entry ${log.event_type}`}
            >
              <span style={{ color: '#475569', fontSize: 10 }}>[{log.timestamp}]</span>
              {' '}
              <span style={{ fontSize: 10 }}>{EVENT_ICONS[log.event_type] || '•'}</span>
              {' '}
              <span style={{ color: '#cbd5e1' }}>{log.message}</span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
