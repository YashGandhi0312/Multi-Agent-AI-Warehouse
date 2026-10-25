// ============================================================
// Documentation & Academic Guide — Classical AI Architecture
// ============================================================

import React from 'react';
import { BookOpen, ShieldAlert, Cpu, Network, Compass, CheckCircle2 } from 'lucide-react';

export const Documentation: React.FC = () => {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      gap: 20,
      height: '100%',
      overflowY: 'auto',
      padding: '20px 24px',
      color: '#e2e8f0',
      maxWidth: 1200,
      margin: '0 auto',
    }}>
      {/* Header Banner */}
      <div style={{
        background: 'linear-gradient(135deg, rgba(30,58,138,0.4) 0%, rgba(15,23,42,0.8) 100%)',
        border: '1px solid rgba(59,130,246,0.3)',
        borderRadius: 14,
        padding: '24px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <BookOpen size={24} color="#60a5fa" />
          <h1 style={{ margin: 0, fontSize: 22, fontWeight: 800, color: '#f8fafc' }}>
            Classical Artificial Intelligence in Multi-Agent Warehouse Automation
          </h1>
        </div>
        <p style={{ margin: 0, fontSize: 13, color: '#94a3b8', lineHeight: 1.6 }}>
          Comprehensive theoretical documentation, mathematical formulations, and algorithmic proofs for the AI Lab Mini Project.
          This system operates purely on deterministic graph search, space-time reservation planning, and symbolic rule-based reasoning — strictly with <strong>zero machine learning</strong>.
        </p>
      </div>

      {/* Section 1: Why Classical AI */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <ShieldAlert size={20} color="#f59e0b" />
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
            1. Classical AI vs. Machine Learning: The Academic Rationale
          </h2>
        </div>
        <div style={{ fontSize: 13, color: '#cbd5e1', lineHeight: 1.7, display: 'flex', flexDirection: 'column', gap: 12 }}>
          <p style={{ margin: 0 }}>
            In safety-critical industrial automation such as robotic warehouse fulfillment centers (e.g., Amazon Robotics, Kiva Systems), deterministic classical AI is heavily preferred over black-box Deep Learning and Reinforcement Learning for core navigation and safety:
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12, marginTop: 4 }}>
            <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, padding: 12 }}>
              <div style={{ fontWeight: 700, color: '#60a5fa', marginBottom: 4 }}>1. Formal Safety Guarantees</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                Cooperative A* with space-time reservation mathematically guarantees zero collisions between agents, whereas RL policies can unpredictably fail on out-of-distribution states.
              </div>
            </div>
            <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, padding: 12 }}>
              <div style={{ fontWeight: 700, color: '#4ade80', marginBottom: 4 }}>2. 100% Explainability & Auditability</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                Every decision made by the system is traceable to a specific IF-THEN rule (e.g., Rule R6: Dynamic Replanning) or an exact A* cost valuation $f(n) = g(n) + h(n)$.
              </div>
            </div>
            <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(59,130,246,0.2)', borderRadius: 8, padding: 12 }}>
              <div style={{ fontWeight: 700, color: '#facc15', marginBottom: 4 }}>3. Zero Training & Instant Adaptability</div>
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                When a human worker drops a box (dynamic obstacle) or layout shifts, A* replans in milliseconds without requiring neural network retraining.
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Section 2: Mathematical Formulations */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <Cpu size={20} color="#38bdf8" />
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
            2. Core Algorithmic & Mathematical Formulations
          </h2>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* A* Formulation */}
          <div style={{ background: 'rgba(15,23,42,0.5)', borderRadius: 8, padding: 14, borderLeft: '3px solid #3b82f6' }}>
            <h3 style={{ margin: '0 0 6px 0', fontSize: 14, color: '#93c5fd' }}>
              A. A* Graph Search & Heuristic Admissibility
            </h3>
            <p style={{ margin: '0 0 8px 0', fontSize: 12, color: '#cbd5e1', lineHeight: 1.6 }}>
              A* calculates the evaluation function for each node $n$:
            </p>
            <div style={{
              background: '#020818',
              padding: '8px 14px',
              borderRadius: 6,
              fontFamily: 'monospace',
              fontSize: 13,
              color: '#38bdf8',
              display: 'inline-block',
              marginBottom: 8,
            }}>
              f(n) = g(n) + h(n)
            </div>
            <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
              Where $g(n)$ is the exact accumulated path cost from start to node $n$, and $h(n)$ is the Manhattan Distance heuristic:
              <br />
              <code style={{ color: '#facc15', fontFamily: 'monospace' }}>h(n) = |x_n - x_goal| + |y_n - y_goal|</code>
              <br />
              <strong>Theorem:</strong> Because diagonal movement is disallowed in our 4-connected grid, Manhattan distance is <em>admissible</em> ($h(n) \le h^*(n)$) and <em>consistent</em> ($h(n) \le c(n, a, n') + h(n')$), mathematically guaranteeing that A* finds the optimal shortest path without suboptimal re-expansions.
            </p>
          </div>

          {/* Cooperative A* Formulation */}
          <div style={{ background: 'rgba(15,23,42,0.5)', borderRadius: 8, padding: 14, borderLeft: '3px solid #a855f7' }}>
            <h3 style={{ margin: '0 0 6px 0', fontSize: 14, color: '#c084fc' }}>
              B. Cooperative A* (CA*) & Space-Time Reservation Table
            </h3>
            <p style={{ margin: '0 0 8px 0', fontSize: 12, color: '#cbd5e1', lineHeight: 1.6 }}>
              Standard 2D pathfinding cannot prevent multi-robot collisions. Cooperative A* (Silver, 2005) expands the search space into 3 dimensions: <code style={{ color: '#a855f7', fontFamily: 'monospace' }}>(x, y, t)</code>.
            </p>
            <p style={{ margin: '0 0 8px 0', fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
              A shared <strong>Space-Time Reservation Table</strong> R(x, y, t) records reserved states. Two collision types are explicitly prevented:
            </p>
            <ul style={{ margin: 0, paddingLeft: 20, fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
              <li><strong>Vertex Conflict:</strong> Two robots cannot occupy the same coordinate at the same time: <code style={{ color: '#f87171' }}>Pos(R_A, t) == Pos(R_B, t)</code></li>
              <li><strong>Edge/Swap Conflict:</strong> Robots cannot swap adjacent positions across time steps: <code style={{ color: '#f87171' }}>Pos(R_A, t) == Pos(R_B, t+1) AND Pos(R_A, t+1) == Pos(R_B, t)</code></li>
            </ul>
            <p style={{ margin: '8px 0 0 0', fontSize: 12, color: '#cbd5e1' }}>
              Robots plan sequentially according to dynamic priority; higher-priority robots reserve their space-time tubes first, and subsequent robots either wait (wait action) or detours around them.
            </p>
          </div>

          {/* Task Allocation */}
          <div style={{ background: 'rgba(15,23,42,0.5)', borderRadius: 8, padding: 14, borderLeft: '3px solid #10b981' }}>
            <h3 style={{ margin: '0 0 6px 0', fontSize: 14, color: '#6ee7b7' }}>
              C. Optimal Task Allocation
            </h3>
            <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.6 }}>
              Task allocation solves the bipartite matching between available robots {'{'}R₁ ... Rₘ{'}'} and pending packages {'{'}P₁ ... Pₖ{'}'}.
              The assignment cost matrix is formulated as:
              <br />
              <code style={{ color: '#34d399', fontFamily: 'monospace' }}>Cost(R_i, P_j) = Manhattan(Pos(R_i), Pickup(P_j)) + Manhattan(Pickup(P_j), Delivery(P_j)) / Priority(P_j)</code>
              <br />
              The centralized dispatcher solves this using a greedy priority-distance matcher or Hungarian Algorithm ($O(n^3)$), minimizing the global mission completion time (makespan).
            </p>
          </div>
        </div>
      </div>

      {/* Section 3: Symbolic Rule Engine */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <Network size={20} color="#ec4899" />
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
            3. Symbolic Expert System: Production Rule Set
          </h2>
        </div>
        <p style={{ margin: '0 0 12px 0', fontSize: 12, color: '#94a3b8' }}>
          Robot state transitions and behavioral decisions are governed by a forward-chaining production rule engine with strict deterministic priority resolution:
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 10 }}>
          {[
            { id: 'R1', name: 'Task Assignment', prio: 10, desc: 'IF Robot is IDLE AND Pending Package exists, THEN assign nearest high-priority package' },
            { id: 'R2', name: 'Plan to Pickup', prio: 20, desc: 'IF Robot is ASSIGNED AND Has No Path, THEN compute Space-Time A* path to pickup station' },
            { id: 'R3', name: 'Execute Pickup', prio: 30, desc: 'IF Robot is at Pickup Location, THEN transition package to PICKED_UP and set state to DELIVERING' },
            { id: 'R4', name: 'Plan to Delivery', prio: 40, desc: 'IF Robot has Package AND Has No Path, THEN plan Space-Time A* path to designated delivery bay' },
            { id: 'R5', name: 'Execute Delivery', prio: 50, desc: 'IF Robot arrives at Delivery Station, THEN unload package, mark COMPLETED, and revert to IDLE' },
            { id: 'R6', name: 'Dynamic Obstacle Replanning', prio: 60, desc: 'IF Next path cell is blocked by obstacle, THEN trigger instant A* dynamic recalculation' },
            { id: 'R7', name: 'Space-Time Conflict Wait', prio: 70, desc: 'IF Higher priority robot reserves next step, THEN issue WAIT action until cell clears' },
          ].map(rule => (
            <div key={rule.id} style={{
              background: 'rgba(15,23,42,0.6)',
              border: '1px solid rgba(236,72,153,0.2)',
              borderRadius: 8,
              padding: 10,
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                <span style={{ fontWeight: 700, color: '#f472b6', fontSize: 12 }}>{rule.id}: {rule.name}</span>
                <span style={{ fontSize: 10, background: 'rgba(236,72,153,0.15)', color: '#f472b6', padding: '2px 6px', borderRadius: 4 }}>
                  Prio {rule.prio}
                </span>
              </div>
              <div style={{ fontSize: 11, color: '#94a3b8', lineHeight: 1.4 }}>
                {rule.desc}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Section 4: Preset Scenarios Walkthrough */}
      <div className="glass-card" style={{ padding: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
          <Compass size={20} color="#a78bfa" />
          <h2 style={{ margin: 0, fontSize: 16, fontWeight: 700, color: '#f8fafc' }}>
            4. Interactive Evaluation Scenarios
          </h2>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 12 }}>
          <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(167,139,250,0.2)', borderRadius: 8, padding: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <CheckCircle2 size={16} color="#a78bfa" />
              <span style={{ fontWeight: 700, color: '#c084fc', fontSize: 13 }}>Scenario A: Basic Multi-Robot Delivery</span>
            </div>
            <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
              Tests autonomous dispatching of 3 robots across open warehouse aisles. Demonstrates optimal Manhattan distance task assignment and parallel pickup/delivery execution.
            </p>
          </div>

          <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(167,139,250,0.2)', borderRadius: 8, padding: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <CheckCircle2 size={16} color="#a78bfa" />
              <span style={{ fontWeight: 700, color: '#c084fc', fontSize: 13 }}>Scenario B: Corridor Collision Avoidance</span>
            </div>
            <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
              Positions two robots facing each other in a narrow single-cell corridor. Demonstrates Cooperative A* space-time coordination where Robot 1 claims priority and Robot 2 pulls into a passing alcove or yields.
            </p>
          </div>

          <div style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(167,139,250,0.2)', borderRadius: 8, padding: 14 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <CheckCircle2 size={16} color="#a78bfa" />
              <span style={{ fontWeight: 700, color: '#c084fc', fontSize: 13 }}>Scenario C: Dynamic Obstacle Replanning</span>
            </div>
            <p style={{ margin: 0, fontSize: 12, color: '#94a3b8', lineHeight: 1.5 }}>
              Simulates real-world warehouse interference. As a robot moves toward its delivery station, an unexpected obstacle appears directly in its path, triggering rule R6 and instantaneous dynamic A* replanning.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
