// ============================================================
// Backtracking Panel — Branch & Bound search tree, priority-order
// backtracking, agent decision stacks and learned nogoods
// ============================================================

import React, { useEffect, useState } from 'react';
import type { BacktrackingState, SearchTreeNode, WarehouseState } from '../types';
import * as api from '../services/api';
import { GitBranch, RefreshCw } from 'lucide-react';

interface BacktrackingPanelProps {
  state: WarehouseState;
}

const STATUS_COLORS: Record<SearchTreeNode['status'], string> = {
  best: '#10b981',
  expanded: '#38bdf8',
  pruned: '#52525b',
};

const card: React.CSSProperties = {
  background: '#121215',
  border: '1px solid #1f2228',
  borderRadius: 8,
  padding: 12,
};

const sectionTitle: React.CSSProperties = {
  fontSize: 11, fontWeight: 700, color: '#ffffff', marginBottom: 8,
};

const Metric: React.FC<{ label: string; value: React.ReactNode; color?: string }> = ({
  label, value, color = '#e4e4e7',
}) => (
  <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
    <span style={{ fontSize: 10, color: '#71717a' }}>{label}</span>
    <span style={{ fontSize: 13, fontWeight: 700, color }}>{value}</span>
  </div>
);

export const BacktrackingPanel: React.FC<BacktrackingPanelProps> = ({ state }) => {
  const [data, setData] = useState<BacktrackingState | null>(null);
  const searchStep = state.backtracking?.allocation_search?.step;
  const orderingStep = state.backtracking?.ordering_search?.step;

  const refresh = () => {
    api.getBacktracking()
      .then(res => setData(res as BacktrackingState))
      .catch(console.error);
  };

  // Re-fetch the full trace only when a new search actually ran
  useEffect(refresh, [searchStep, orderingStep]);

  const alloc = data?.allocation_search;
  const ordering = data?.ordering_search;
  const trace = alloc?.trace ?? [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <GitBranch size={14} color="#f472b6" />
          <span style={{ fontSize: 11, fontWeight: 700, color: '#a1a1aa', textTransform: 'uppercase' }}>
            Backtracking Search
          </span>
        </div>
        <button onClick={refresh} className="ctrl-btn" title="Refresh">
          <RefreshCw size={12} />
        </button>
      </div>

      {/* ── Branch & Bound allocation ── */}
      <div style={card}>
        <div style={sectionTitle}>
          Task Allocation · Branch &amp; Bound
          {alloc && (
            <span style={{ fontWeight: 400, color: '#71717a' }}> (step {alloc.step})</span>
          )}
        </div>
        {alloc ? (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, marginBottom: 10 }}>
              <Metric label="Nodes" value={alloc.nodes_expanded} />
              <Metric label="Pruned" value={alloc.branches_pruned} />
              <Metric label="Backtracks" value={alloc.backtracks} />
              <Metric label="Joint cost" value={alloc.best_cost} color="#10b981" />
              <Metric label="Greedy cost" value={alloc.greedy_cost} />
              <Metric
                label={alloc.optimal ? 'Optimal' : 'Budget hit'}
                value={alloc.cost_saved > 0 ? `−${alloc.cost_saved}` : '±0'}
                color={alloc.optimal ? '#34d399' : '#fbbf24'}
              />
            </div>

            {trace.length > 0 && (
              <div style={{
                maxHeight: 220, overflowY: 'auto', background: '#09090b',
                border: '1px solid #1f2228', borderRadius: 6, padding: '6px 8px',
                fontFamily: 'JetBrains Mono, monospace', fontSize: 10, lineHeight: 1.6,
              }}>
                {trace.map(node => (
                  <div
                    key={node.id}
                    style={{
                      paddingLeft: (node.depth - 1) * 12,
                      color: STATUS_COLORS[node.status],
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {node.depth > 1 ? '└ ' : ''}
                    {node.task_id} → {node.robot_id ?? 'SKIP'}
                    <span style={{ color: '#52525b' }}> g={node.cost}</span>
                    {node.status !== 'expanded' && (
                      <span> [{node.status}]</span>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div style={{ display: 'flex', gap: 12, marginTop: 6, fontSize: 10, color: '#71717a' }}>
              {(Object.keys(STATUS_COLORS) as SearchTreeNode['status'][]).map(s => (
                <span key={s} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span style={{ width: 8, height: 8, borderRadius: 2, background: STATUS_COLORS[s] }} />
                  {s}
                </span>
              ))}
            </div>
          </>
        ) : (
          <div style={{ fontSize: 11, color: '#71717a' }}>
            Run the simulation; the search tree appears after the next allocation.
          </div>
        )}
      </div>

      {/* ── Priority-order backtracking ── */}
      <div style={card}>
        <div style={sectionTitle}>Planning Order · Cooperative A*</div>
        {ordering ? (
          <div style={{ fontSize: 11, color: '#a1a1aa', lineHeight: 1.6 }}>
            <div>
              Step {ordering.step}: {ordering.orderings_tried} orderings, {ordering.ca_calls} CA* calls,{' '}
              {ordering.backtracks} backtracks
            </div>
            <div>
              Final order:{' '}
              <span style={{ color: ordering.resolved_by_backtracking ? '#34d399' : '#e4e4e7' }}>
                {ordering.final_order.join(' → ') || '—'}
              </span>
            </div>
            {ordering.unsolvable.length > 0 && (
              <div style={{ color: '#f87171' }}>
                Unreachable goal: {ordering.unsolvable.join(', ')}
              </div>
            )}
          </div>
        ) : (
          <div style={{ fontSize: 11, color: '#71717a' }}>
            The fixed planning order has worked every step so far.
          </div>
        )}
      </div>

      {/* ── Agent decision stacks ── */}
      <div style={card}>
        <div style={sectionTitle}>Agent Choice Points</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4, fontSize: 11 }}>
          {(data?.agents ?? []).map(agent => (
            <div key={agent.robot_id} style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
              <span style={{ color: '#e4e4e7', fontWeight: 600 }}>{agent.robot_id}</span>
              <span style={{ color: '#a1a1aa', fontFamily: 'JetBrains Mono, monospace', flex: 1, textAlign: 'right' }}>
                {agent.decision_stack.length === 0
                  ? '—'
                  : agent.decision_stack.map(c =>
                      c.level === 'TASK'
                        ? `${c.label}${c.committed ? '🔒' : ''}`
                        : `route×${c.attempts}`
                    ).join(' › ')}
              </span>
              <span style={{ color: '#f472b6', minWidth: 28, textAlign: 'right' }}>
                ↩{agent.backtrack_count}
              </span>
            </div>
          ))}
        </div>
        {(data?.nogoods.length ?? 0) > 0 && (
          <div style={{ marginTop: 8, paddingTop: 8, borderTop: '1px solid #1f2228', fontSize: 10, color: '#fbbf24' }}>
            Nogoods:{' '}
            {data!.nogoods.map(n =>
              `${n.robot_id ?? 'ALL'}✗${n.task_id} (until ${n.expires_at})`
            ).join(', ')}
          </div>
        )}
      </div>
    </div>
  );
};
