import React, { useState, useMemo } from 'react';
import { Target, AlertCircle, Info } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

export default function PerClassPerformanceChart({
  perClassStats: propPerClassStats = [],
  perClassData,
  modelName = 'Random Forest',
  runLabel,
  runName = 'Evaluation',
}) {
  const activeRunLabel = runLabel || runName;

  const perClassStats = useMemo(() => {
    if (Array.isArray(propPerClassStats) && propPerClassStats.length > 0) {
      return propPerClassStats;
    }
    if (perClassData && typeof perClassData === 'object') {
      return Object.entries(perClassData).map(([cls, info]) => {
        const sup = info.test_support ?? info.support ?? 0;
        return {
          class_name: cls,
          precision: Number(((info.precision ?? info.rf_precision ?? 0) * 100).toFixed(2)),
          recall: Number(((info.recall ?? info.rf_recall ?? 0) * 100).toFixed(2)),
          f1_score: Number(((info.f1_score ?? info.rf_f1 ?? 0) * 100).toFixed(2)),
          support: sup,
          is_low_support: sup < 100,
        };
      });
    }
    return [];
  }, [propPerClassStats, perClassData]);

  const [metric, setMetric] = useState('recall'); // 'precision' | 'recall' | 'f1_score'
  const [filterMode, setFilterMode] = useState('all'); // 'all' | 'common' | 'low_support'

  const metricLabel = {
    precision: 'Precision',
    recall: 'Recall',
    f1_score: 'F1-Score',
  }[metric];

  const metricColor = {
    precision: '#00d4ff',
    recall: '#10b981',
    f1_score: '#8b5cf6',
  }[metric];

  // Filter data based on support
  const filteredData = useMemo(() => {
    return perClassStats.filter((item) => {
      if (filterMode === 'common') return item.support >= 100;
      if (filterMode === 'low_support') return item.support < 100;
      return true;
    });
  }, [perClassStats, filterMode]);

  // Highlight classes with very low support (< 10)
  const lowSupportClasses = perClassStats.filter((c) => c.support < 10);

  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
        <div>
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Target size={18} style={{ color: metricColor }} />
            Per-Class Detection Performance ({modelName})
          </div>
          <div className="card-subtitle">
            Evaluated on holdout test set ({activeRunLabel}) · Support counts reflect actual test rows
          </div>
        </div>

        {/* Metric Selector Buttons */}
        <div style={{ display: 'flex', gap: 6 }}>
          {['recall', 'precision', 'f1_score'].map((m) => {
            const active = m === metric;
            return (
              <button
                key={m}
                className="btn"
                onClick={() => setMetric(m)}
                style={{
                  padding: '5px 12px',
                  fontSize: 12,
                  fontWeight: 600,
                  borderRadius: 6,
                  cursor: 'pointer',
                  background: active ? 'rgba(0, 212, 255, 0.2)' : 'var(--bg-secondary)',
                  color: active ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                  border: active ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                }}
              >
                {m === 'f1_score' ? 'F1-Score' : m.charAt(0).toUpperCase() + m.slice(1)}
              </button>
            );
          })}
        </div>
      </div>

      {/* Class Support Filter Bar */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10, flexWrap: 'wrap', marginBottom: 16, padding: '8px 12px', background: 'var(--bg-secondary)', borderRadius: 8 }}>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Class Filter:</span>
          {[
            { key: 'all', label: 'All Classes (12)' },
            { key: 'common', label: 'Common (≥100 samples)' },
            { key: 'low_support', label: 'Low-Support (<100 samples)' },
          ].map((f) => (
            <button
              key={f.key}
              onClick={() => setFilterMode(f.key)}
              style={{
                fontSize: 11,
                padding: '4px 10px',
                borderRadius: 4,
                cursor: 'pointer',
                background: filterMode === f.key ? 'var(--bg-card)' : 'transparent',
                border: filterMode === f.key ? '1px solid var(--border-accent)' : '1px solid transparent',
                color: filterMode === f.key ? 'var(--accent-cyan)' : 'var(--text-muted)',
              }}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Small class uncertainty warning */}
        {lowSupportClasses.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--accent-yellow)' }}>
            <AlertCircle size={14} />
            <span>
              Low test support:{' '}
              {lowSupportClasses.map((c) => `${c.class_name} (N=${c.support})`).join(', ')}
            </span>
          </div>
        )}
      </div>

      {/* Chart */}
      {filteredData.length > 0 ? (
        <ResponsiveContainer width="100%" height={320}>
          <BarChart
            data={filteredData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: 80, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis type="number" domain={[0, 100]} unit="%" tick={{ fill: '#64748b', fontSize: 11 }} />
            <YAxis
              type="category"
              dataKey="class_name"
              tick={{ fill: '#94a3b8', fontSize: 11 }}
              width={140}
            />
            <Tooltip
              formatter={(value, name, props) => [
                `${value}% (Test Support: ${props.payload.support.toLocaleString()} samples)`,
                metricLabel,
              ]}
              contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 6 }}
            />
            <Bar dataKey={metric} radius={[0, 4, 4, 0]}>
              {filteredData.map((entry, index) => {
                const isCriticallyLow = entry.support < 10;
                return (
                  <Cell
                    key={`cell-${index}`}
                    fill={isCriticallyLow ? '#f59e0b' : metricColor}
                  />
                );
              })}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p style={{ color: 'var(--text-muted)' }}>No attack classes matching selected filter.</p>
      )}

      {/* Footer Notes on Rare Attack Uncertainty */}
      <div style={{ marginTop: 12, padding: '8px 12px', background: 'rgba(245, 158, 11, 0.08)', borderRadius: 6, display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--text-secondary)' }}>
        <Info size={14} style={{ color: 'var(--accent-yellow)', flexShrink: 0 }} />
        <span>
          Amber bars denote classes with fewer than 10 test examples (e.g. <strong>NMAP_FIN_SCAN N=1</strong>, <strong>Metasploit_Brute_Force_SSH N=7</strong>). Their metrics carry wide binomial confidence intervals and cannot certify field readiness alone.
        </span>
      </div>
    </div>
  );
}
