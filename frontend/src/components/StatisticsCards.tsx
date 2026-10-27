// ============================================================
// Statistics Cards Panel — Bottom Stats Bar
// ============================================================

import React from 'react';
import type { Statistics } from '../types';
import {
  TrendingUp, Package, Clock, AlertTriangle,
  CheckCircle, BarChart2, Zap, Target, Map, Undo2, GitBranch
} from 'lucide-react';

interface StatsCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
  sub?: string;
}

const StatItem: React.FC<StatsCardProps> = ({ label, value, icon, color, sub }) => (
  <div className="stat-card" style={{ minWidth: 110 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
      <div style={{
        width: 28, height: 28, borderRadius: 6,
        background: color + '20', border: `1px solid ${color}40`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: color, flexShrink: 0,
      }}>
        {icon}
      </div>
      <span style={{ fontSize: 11, color: '#64748b', fontWeight: 500 }}>{label}</span>
    </div>
    <div style={{ fontSize: 22, fontWeight: 800, color: '#e2e8f0', lineHeight: 1 }}>
      {value}
    </div>
    {sub && <div style={{ fontSize: 10, color: '#475569', marginTop: 2 }}>{sub}</div>}
  </div>
);

interface StatisticsCardsProps {
  stats: Statistics;
}

export const StatisticsCards: React.FC<StatisticsCardsProps> = ({ stats }) => {
  return (
    <div style={{
      display: 'flex', gap: 8, overflowX: 'auto', padding: '0 4px',
      flexWrap: 'nowrap',
    }}>
      <StatItem
        label="Completed"
        value={stats.completed_deliveries}
        icon={<CheckCircle size={14} />}
        color="#22c55e"
        sub="deliveries"
      />
      <StatItem
        label="Pending"
        value={stats.pending_deliveries}
        icon={<Package size={14} />}
        color="#f97316"
        sub="in queue"
      />
      <StatItem
        label="Distance"
        value={stats.total_distance}
        icon={<Map size={14} />}
        color="#3b82f6"
        sub="total steps"
      />
      <StatItem
        label="Planning"
        value={`${stats.total_planning_time_ms.toFixed(0)}ms`}
        icon={<Clock size={14} />}
        color="#06b6d4"
        sub="total"
      />
      <StatItem
        label="Conflicts"
        value={stats.conflicts_detected}
        icon={<AlertTriangle size={14} />}
        color="#ef4444"
        sub="detected"
      />
      <StatItem
        label="Resolved"
        value={stats.conflicts_resolved}
        icon={<CheckCircle size={14} />}
        color="#a855f7"
        sub="conflicts"
      />
      <StatItem
        label="Avg Steps"
        value={stats.average_delivery_steps.toFixed(1)}
        icon={<TrendingUp size={14} />}
        color="#eab308"
        sub="per delivery"
      />
      <StatItem
        label="Waiting"
        value={stats.total_waiting_steps}
        icon={<Zap size={14} />}
        color="#94a3b8"
        sub="total steps"
      />
      <StatItem
        label="Nodes"
        value={stats.nodes_explored}
        icon={<BarChart2 size={14} />}
        color="#22d3ee"
        sub="explored"
      />
      <StatItem
        label="Replans"
        value={stats.replan_count}
        icon={<Target size={14} />}
        color="#c084fc"
        sub="total"
      />
      <StatItem
        label="Backtracks"
        value={stats.agent_backtracks ?? 0}
        icon={<Undo2 size={14} />}
        color="#f472b6"
        sub={`${stats.deadlocks_resolved ?? 0} deadlocks broken`}
      />
      <StatItem
        label="B&B Saved"
        value={(stats.allocation_cost_saved ?? 0).toFixed(0)}
        icon={<GitBranch size={14} />}
        color="#34d399"
        sub={`${stats.branches_pruned ?? 0} branches pruned`}
      />
    </div>
  );
};
