import React, { useState, useMemo } from 'react';
import { BarChart3, CheckSquare, Square } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

const METRIC_OPTIONS = [
  { key: 'macro_f1', label: 'Macro-F1', color: '#8b5cf6' },
  { key: 'accuracy', label: 'Accuracy', color: '#00d4ff' },
  { key: 'macro_recall', label: 'Macro-Recall', color: '#10b981' },
  { key: 'macro_precision', label: 'Macro-Precision', color: '#f59e0b' },
  { key: 'roc_auc', label: 'ROC-AUC', color: '#ec4899' },
];

export default function DynamicModelComparison({
  models = {},
  referenceBaseline = null,
  runLabel,
  selectedRunName,
  runName = 'Evaluation',
}) {
  const activeRunLabel = selectedRunName || runLabel || runName;

  // Separate trained models from reference baseline
  const { trainedModels, baselineObj } = useMemo(() => {
    const raw = Array.isArray(models)
      ? models.reduce((acc, m) => {
          if (m && (m.id || m.name)) acc[m.id || m.name] = m;
          return acc;
        }, {})
      : (models || {});

    const trained = {};
    let baseline = referenceBaseline;

    Object.entries(raw).forEach(([key, m]) => {
      if (m.is_baseline || key === 'MajorityBaseline') {
        if (!baseline) baseline = m;
      } else {
        trained[key] = m;
      }
    });

    return { trainedModels: trained, baselineObj: baseline };
  }, [models, referenceBaseline]);

  const modelKeys = useMemo(() => Object.keys(trainedModels), [trainedModels]);
  const [selectedMetric, setSelectedMetric] = useState('macro_f1');

  // Default to selecting all evaluated models
  const [selectedModels, setSelectedModels] = useState(() => {
    return Object.entries(trainedModels)
      .filter(([, m]) => m.evaluated !== false && m.status !== 'Not evaluated')
      .map(([k]) => k);
  });

  const [showBaseline, setShowBaseline] = useState(false);

  // Update selected models when modelKeys change
  React.useEffect(() => {
    const validKeys = Object.entries(trainedModels)
      .filter(([, m]) => m.evaluated !== false && m.status !== 'Not evaluated')
      .map(([k]) => k);
    setSelectedModels(validKeys);
  }, [trainedModels]);

  const toggleModel = (id) => {
    const model = trainedModels[id];
    if (model && (model.evaluated === false || model.status === 'Not evaluated')) return;

    setSelectedModels((prev) => {
      if (prev.includes(id)) {
        if (prev.length === 1 && !showBaseline) return prev; // keep at least 1
        return prev.filter((m) => m !== id);
      }
      return [...prev, id];
    });
  };

  const currentMetricMeta = METRIC_OPTIONS.find((m) => m.key === selectedMetric) || METRIC_OPTIONS[0];

  // Prepare chart data dynamically
  const chartData = useMemo(() => {
    const items = selectedModels
      .map((key) => {
        const model = trainedModels[key];
        if (!model) return null;
        const val = model[selectedMetric];
        return {
          id: key,
          name: model.name || key,
          value: Number.isFinite(val) ? Number(val.toFixed(2)) : 0,
          isBaseline: false,
          hasProbabilities: selectedMetric === 'roc_auc' ? val !== null : true,
        };
      })
      .filter(Boolean);

    if (showBaseline && baselineObj) {
      const bVal = baselineObj[selectedMetric];
      items.push({
        id: 'MajorityBaseline',
        name: `${baselineObj.name || 'Majority Baseline'} (Reference)`,
        value: Number.isFinite(bVal) ? Number(bVal.toFixed(2)) : 0,
        isBaseline: true,
        hasProbabilities: true,
      });
    }

    return items.sort((a, b) => b.value - a.value);
  }, [trainedModels, selectedModels, selectedMetric, showBaseline, baselineObj]);

  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: 12, marginBottom: 16 }}>
        <div>
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BarChart3 size={18} style={{ color: currentMetricMeta.color }} />
            Dynamic Model Performance Comparison
          </div>
          <div className="card-subtitle">
            Actual test-set metrics from {activeRunLabel}; values recomputed from real evaluation artifacts
          </div>
        </div>

        {/* Metric Selector Tabs */}
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {METRIC_OPTIONS.map((opt) => {
            const active = opt.key === selectedMetric;
            return (
              <button
                key={opt.key}
                className="btn"
                onClick={() => setSelectedMetric(opt.key)}
                style={{
                  padding: '5px 12px',
                  fontSize: 12,
                  fontWeight: 600,
                  borderRadius: 6,
                  cursor: 'pointer',
                  background: active ? `${opt.color}25` : 'var(--bg-secondary)',
                  color: active ? opt.color : 'var(--text-secondary)',
                  border: active ? `1px solid ${opt.color}` : '1px solid var(--border-subtle)',
                }}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Model Selection Checkboxes & Separate Reference Baseline Toggle */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, alignItems: 'center', marginBottom: 16, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 8 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
          Include Trained Models:
        </span>
        {modelKeys.map((key) => {
          const model = trainedModels[key];
          const isEvaluated = model && model.evaluated !== false && model.status !== 'Not evaluated';
          const isSelected = selectedModels.includes(key);

          if (!isEvaluated) {
            return (
              <span
                key={key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '4px 10px',
                  borderRadius: 4,
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px dashed var(--border-subtle)',
                  color: 'var(--text-muted)',
                  fontSize: 12,
                  opacity: 0.6,
                }}
              >
                <Square size={14} />
                {model.name || key} (Not evaluated)
              </span>
            );
          }

          return (
            <button
              key={key}
              onClick={() => toggleModel(key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 4,
                cursor: 'pointer',
                background: isSelected ? 'var(--bg-card)' : 'transparent',
                border: isSelected ? '1px solid var(--border-accent)' : '1px solid transparent',
                color: isSelected ? 'var(--text-primary)' : 'var(--text-muted)',
                fontSize: 12,
              }}
            >
              {isSelected ? (
                <CheckSquare size={14} style={{ color: currentMetricMeta.color }} />
              ) : (
                <Square size={14} />
              )}
              {model.name || key}
            </button>
          );
        })}

        {/* Separate Reference Baseline Control */}
        {baselineObj && (
          <div style={{ marginLeft: 'auto', borderLeft: '1px solid var(--border-subtle)', paddingLeft: 12 }}>
            <button
              onClick={() => setShowBaseline((prev) => !prev)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '4px 10px',
                borderRadius: 4,
                cursor: 'pointer',
                background: showBaseline ? 'rgba(100, 116, 139, 0.2)' : 'transparent',
                border: showBaseline ? '1px solid #64748b' : '1px dashed #64748b',
                color: showBaseline ? '#cbd5e1' : '#94a3b8',
                fontSize: 12,
              }}
              title="Show naive majority-class baseline as a reference reference benchmark, not a trained model"
            >
              {showBaseline ? (
                <CheckSquare size={14} style={{ color: '#94a3b8' }} />
              ) : (
                <Square size={14} />
              )}
              Reference Baseline (Majority Class)
            </button>
          </div>
        )}
      </div>

      {/* Chart */}
      {chartData.length > 0 ? (
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="name" tick={{ fill: '#94a3b8', fontSize: 11 }} interval={0} />
            <YAxis domain={[0, 100]} tick={{ fill: '#64748b', fontSize: 11 }} unit="%" />
            <Tooltip
              formatter={(value, name, item) => {
                const label = item.payload.isBaseline
                  ? `${value}% (Reference Baseline)`
                  : `${value}%`;
                return [label, currentMetricMeta.label];
              }}
              contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 6 }}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.isBaseline ? '#64748b' : currentMetricMeta.color}
                  stroke={entry.isBaseline ? '#94a3b8' : 'none'}
                  strokeDasharray={entry.isBaseline ? '4 4' : 'none'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: 24 }}>No models selected for comparison.</p>
      )}
    </div>
  );
}
