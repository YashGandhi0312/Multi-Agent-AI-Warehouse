// ============================================================
// Algorithm Panel — Right Sidebar: AI Decision Visualization
// ============================================================

import React, { useState } from 'react';
import type { RuleInfo, EventLog } from '../types';
import { Brain, ChevronDown, ChevronRight, Zap } from 'lucide-react';

interface AlgorithmPanelProps {
  activeAlgorithm: string;
  rules: RuleInfo[];
  recentLogs: EventLog[];
}

const ALGORITHM_DESCRIPTIONS: Record<string, string> = {
  'Cooperative A*': `Cooperative A* plans collision-free paths for multiple robots in time-space. Each state is (x, y, t). A shared reservation table prevents vertex and edge-swap collisions. Robots plan sequentially by priority — later robots route around earlier ones.`,
  'A* Search': `A* finds optimal paths using f(n) = g(n) + h(n). g(n) is the actual cost from start; h(n) is Manhattan distance to goal. By expanding nodes in f-score order, A* guarantees the shortest path when h is admissible (never overestimates).`,
  'Task Allocation': `Greedy minimum-cost allocation: for each pending task, compute cost(robot, task) = dist(robot→pickup) + dist(pickup→delivery) using A*. Assign the task to the minimum-cost available robot. O(T×R) per cycle.`,
  'Rule Engine': `Forward-chaining IF-THEN rules govern robot behavior. Rules fire in priority order. The rule engine implements the reactive reasoning layer of each autonomous agent.`,
};

const CATEGORY_COLORS: Record<string, string> = {
  NAVIGATION: '#22d3ee',
  DELIVERY: '#4ade80',
  PICKUP: '#60a5fa',
  REPLANNING: '#c084fc',
  COLLISION_AVOIDANCE: '#fbbf24',
  TASK_MANAGEMENT: '#fb923c',
  DEFAULT: '#64748b',
};

export const AlgorithmPanel: React.FC<AlgorithmPanelProps> = ({
  activeAlgorithm,
  rules,
  recentLogs,
}) => {
  const [showRules, setShowRules] = useState(true);

  // Find recently fired rules from logs
  const recentRuleIds = new Set(
    recentLogs.slice(-20).map(l => l.rule_id).filter(Boolean)
  );

  // Detect the most recent firing event from the log
  const lastRuleFired = recentLogs
    .slice().reverse()
    .find(l => l.rule_id && l.event_type === 'RULE_FIRED');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Active Algorithm */}
      <div style={{
        padding: '10px 14px', borderBottom: '1px solid rgba(59,130,246,0.1)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <Brain size={14} style={{ color: '#a855f7' }} />
          <span style={{ fontSize: 12, fontWeight: 600, color: '#94a3b8' }}>
            Active Algorithm
          </span>
        </div>
        <div style={{
          background: 'rgba(168,85,247,0.1)',
          border: '1px solid rgba(168,85,247,0.3)',
          borderRadius: 6, padding: '6px 10px', marginBottom: 8,
        }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#c084fc' }}>
            {activeAlgorithm}
          </div>
        </div>
        <div style={{
          fontSize: 11, color: '#64748b', lineHeight: 1.5,
          maxHeight: 80, overflowY: 'auto',
        }}>
          {ALGORITHM_DESCRIPTIONS[activeAlgorithm] || 'Multi-agent coordination using classical AI algorithms.'}
        </div>
      </div>

      {/* Rules Section */}
      <div style={{
        borderBottom: '1px solid rgba(59,130,246,0.1)',
      }}>
        <button
          onClick={() => setShowRules(!showRules)}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 8,
            padding: '8px 14px', background: 'none', border: 'none',
            cursor: 'pointer', color: '#64748b',
          }}
        >
          {showRules ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
          <span style={{ fontSize: 11, fontWeight: 600 }}>IF-THEN RULES</span>
          <span style={{
            marginLeft: 'auto', fontSize: 10, color: '#334155',
            fontFamily: 'JetBrains Mono, monospace',
          }}>
            {rules.length} rules
          </span>
        </button>

        {showRules && (
          <div style={{
            maxHeight: 260, overflowY: 'auto', padding: '0 8px 8px',
            display: 'flex', flexDirection: 'column', gap: 4,
          }}>
            {rules.map(rule => {
              const isFiring = recentRuleIds.has(rule.rule_id);
              const catColor = CATEGORY_COLORS[rule.category] || '#64748b';
              return (
                <div
                  key={rule.rule_id}
                  className={`rule-card ${isFiring ? 'firing' : ''}`}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}>
                    {isFiring && (
                      <Zap size={10} style={{ color: '#4ade80' }} />
                    )}
                    <span style={{
                      fontSize: 9, padding: '1px 5px', borderRadius: 3,
                      background: catColor + '20', color: catColor,
                      border: `1px solid ${catColor}30`,
                    }}>
                      {rule.rule_id}
                    </span>
                    <span style={{ fontSize: 10, fontWeight: 600, color: '#94a3b8' }}>
                      {rule.name}
                    </span>
                    <span style={{
                      marginLeft: 'auto', fontSize: 9, color: '#334155',
                    }}>
                      P{rule.priority}
                    </span>
                  </div>
                  <div style={{ fontSize: 10, color: '#475569', lineHeight: 1.4 }}>
                    {rule.description}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Recent Decisions */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <div style={{
          padding: '8px 14px', borderBottom: '1px solid rgba(59,130,246,0.08)',
          fontSize: 11, fontWeight: 600, color: '#475569',
        }}>
          RECENT DECISIONS
        </div>
        <div style={{ flex: 1, overflowY: 'auto', padding: '6px 8px' }}>
          {recentLogs.filter(l =>
            ['COLLISION_AVOIDED', 'SWAP_CONFLICT', 'REPLAN', 'TASK_ASSIGNED', 'PATH_PLANNED', 'BLOCKED'].includes(l.event_type)
          ).slice(-20).reverse().map((log, i) => (
            <div key={i} style={{
              padding: '4px 8px', marginBottom: 3, borderRadius: 4,
              background: 'rgba(10,22,40,0.4)',
              border: '1px solid rgba(59,130,246,0.08)',
              fontSize: 10, color: '#64748b',
            }}>
              <span style={{ color: '#475569' }}>[{log.timestamp}] </span>
              <span style={{ color: '#94a3b8' }}>{log.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
