import React from 'react';
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function EvaluationIntegrityPanel({
  runs = [],
  selectedRunId = 'deduplicated',
  onSelectRun,
  integrity = {},
  loading = false,
}) {
  const isLeakFree = selectedRunId === 'deduplicated';

  return (
    <div className="card" style={{ marginBottom: 24, border: isLeakFree ? '1px solid rgba(0, 212, 255, 0.3)' : '1px solid rgba(239, 68, 68, 0.4)' }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
        <div>
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {isLeakFree ? (
              <CheckCircle2 size={20} style={{ color: 'var(--accent-cyan)' }} />
            ) : (
              <AlertTriangle size={20} style={{ color: 'var(--accent-red)' }} />
            )}
            Evaluation Integrity & Leakage Governance
          </div>
          <div className="card-subtitle">
            Compare data leakage, holdout partition integrity, and deployment readiness across evaluation protocols
          </div>
        </div>

        {/* Run Selector */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Evaluation Protocol:</span>
          {runs.map((run) => {
            const active = run.id === selectedRunId;
            return (
              <button
                key={run.id}
                className="btn"
                onClick={() => onSelectRun(run.id)}
                disabled={loading}
                style={{
                  padding: '6px 14px',
                  fontSize: 12,
                  fontWeight: 600,
                  borderRadius: 6,
                  cursor: 'pointer',
                  background: active
                    ? (run.id === 'deduplicated' ? 'rgba(0, 212, 255, 0.2)' : 'rgba(239, 68, 68, 0.2)')
                    : 'var(--bg-secondary)',
                  color: active
                    ? (run.id === 'deduplicated' ? 'var(--accent-cyan)' : 'var(--accent-red)')
                    : 'var(--text-secondary)',
                  border: active
                    ? (run.id === 'deduplicated' ? '1px solid var(--accent-cyan)' : '1px solid var(--accent-red)')
                    : '1px solid var(--border-subtle)',
                }}
              >
                {run.id === 'deduplicated' ? '🛡️ Leak-Free (Deduplicated)' : '⚠️ Historical Retraining Run'}
              </button>
            );
          })}
        </div>
      </div>

      {/* Warning / Audit State Banner */}
      <div
        style={{
          padding: '12px 16px',
          borderRadius: 8,
          marginBottom: 16,
          background: isLeakFree ? 'rgba(0, 212, 255, 0.08)' : 'rgba(239, 68, 68, 0.12)',
          borderLeft: isLeakFree ? '4px solid var(--accent-cyan)' : '4px solid var(--accent-red)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: 16,
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ShieldAlert size={20} style={{ color: isLeakFree ? 'var(--accent-cyan)' : 'var(--accent-red)', flexShrink: 0 }} />
          <div style={{ fontSize: 13, color: 'var(--text-primary)' }}>
            <strong>{isLeakFree ? 'LEAK-FREE PROTOCOL:' : 'HISTORICAL LEAKAGE AUDIT:'}</strong>{' '}
            {integrity.warning || 'Audit review in progress.'}
          </div>
        </div>
      </div>

      {/* Metric Tiles */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 12,
          marginBottom: 16,
        }}
      >
        <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Cross-Split Feature Overlap</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: integrity.feature_overlap_pct === 0 ? 'var(--accent-green)' : 'var(--accent-red)', marginTop: 4 }}>
            {Number.isFinite(integrity.feature_overlap_pct) ? `${integrity.feature_overlap_pct.toFixed(2)}%` : '—'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
            {integrity.feature_overlap_count ? `${integrity.feature_overlap_count.toLocaleString()} duplicate test rows` : '0 duplicate rows (0.00% leakage)'}
          </div>
        </div>

        <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Untouched Holdout Test Set</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-cyan)', marginTop: 4 }}>
            {integrity.test_samples ? integrity.test_samples.toLocaleString() : '—'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
            {isLeakFree ? 'Distinct test flow signatures' : 'Includes repeated flood frames'}
          </div>
        </div>

        <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Training Set Partition</div>
          <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--accent-purple)', marginTop: 4 }}>
            {integrity.train_samples ? integrity.train_samples.toLocaleString() : '—'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', marginTop: 2 }}>
            Transformers fitted on Train split only
          </div>
        </div>

        <div style={{ padding: 12, background: 'var(--bg-secondary)', borderRadius: 8, border: '1px solid var(--border-subtle)' }}>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase' }}>Governance Certification</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 8 }}>
            Blocked pending augmented multi-source traces
          </div>
        </div>
      </div>

      {/* Limitations note */}
      {integrity.unavoidable_limitations && integrity.unavoidable_limitations.length > 0 && (
        <div style={{ fontSize: 12, color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.2)', padding: '8px 12px', borderRadius: 6 }}>
          <strong style={{ color: 'var(--text-muted)' }}>Documented Constraints:</strong>{' '}
          {integrity.unavoidable_limitations.join(' ')}
        </div>
      )}
    </div>
  );
}
