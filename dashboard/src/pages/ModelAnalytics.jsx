/**
 * SecureIoT-X — Model Analytics Page.
 * Dynamic, interactive model performance analytics, leakage governance,
 * confusion matrix heatmaps, per-class breakdown, and dataset distributions.
 */
import { useCallback, useEffect, useState, useMemo } from 'react';
import { AlertTriangle, RefreshCw, BarChart2 } from 'lucide-react';
import api from '../services/api';

import EvaluationIntegrityPanel from '../components/model-analytics/EvaluationIntegrityPanel';
import InteractiveConfusionMatrix from '../components/model-analytics/InteractiveConfusionMatrix';
import DynamicModelComparison from '../components/model-analytics/DynamicModelComparison';
import PerClassPerformanceChart from '../components/model-analytics/PerClassPerformanceChart';
import DatasetDistributionChart from '../components/model-analytics/DatasetDistributionChart';

const formatPercent = (value, digits = 2) => {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const norm = value <= 1.0 ? value * 100 : value;
  return `${norm.toFixed(digits)}%`;
};

export default function ModelAnalytics() {
  const [runs, setRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('deduplicated');
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Fetch available evaluation runs
  const fetchRuns = useCallback(async () => {
    try {
      const data = await api.getEvaluationRuns();
      if (Array.isArray(data) && data.length > 0) {
        setRuns(data);
        const def = data.find((r) => r.is_default) || data[0];
        setSelectedRunId(def.id);
      }
    } catch {
      setRuns([
        { id: 'deduplicated', name: 'Leak-Free Evaluation', available: true, is_default: true },
        { id: 'historical', name: 'Historical Retraining Run', available: true, is_default: false },
      ]);
    }
  }, []);

  // Fetch report for the currently selected run
  const fetchReport = useCallback(async (runId) => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getEvaluationReport(runId);
      if (!data || !Array.isArray(data.classes)) {
        throw new Error('API returned an invalid evaluation report schema');
      }
      setReport(data);
    } catch (err) {
      setReport(null);
      setError(err.message || `Could not load evaluation report for ${runId}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  useEffect(() => {
    if (selectedRunId) {
      fetchReport(selectedRunId);
    }
  }, [selectedRunId, fetchReport]);

  const [selectedModelKey, setSelectedModelKey] = useState('RandomForest');

  // Ensure selectedModelKey is valid when report changes
  useEffect(() => {
    if (report?.models && !report.models[selectedModelKey]) {
      const keys = Object.keys(report.models);
      if (keys.length > 0) setSelectedModelKey(keys[0]);
    }
  }, [report, selectedModelKey]);

  const activeModel = useMemo(() => {
    if (!report?.models) return null;
    return report.models[selectedModelKey] || report.models.RandomForest || Object.values(report.models)[0] || null;
  }, [report, selectedModelKey]);

  const classes = useMemo(() => {
    return report?.classes || [];
  }, [report]);

  const activePerClassStats = useMemo(() => {
    if (activeModel?.classification_report && classes.length) {
      return classes.map((cls) => {
        const cinfo = activeModel.classification_report[cls] || {};
        const sup = Number(cinfo.support || 0);
        return {
          class_name: cls,
          precision: Number(((cinfo.precision || 0) * 100).toFixed(2)),
          recall: Number(((cinfo.recall || 0) * 100).toFixed(2)),
          f1_score: Number(((cinfo['f1-score'] || 0) * 100).toFixed(2)),
          support: sup,
          is_low_support: sup < 100,
        };
      });
    }
    return report?.per_class_stats || [];
  }, [activeModel, classes, report]);

  return (
    <div className="page model-analytics">
      {/* Dynamic Header & Refresh */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', margin: 0, display: 'flex', alignItems: 'center', gap: 10 }}>
            <BarChart2 size={24} style={{ color: 'var(--accent-cyan)' }} />
            Model Analytics & Interactive Evaluation
          </h1>
          <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4, marginBottom: 0 }}>
            Live interactive telemetry recomputed directly from validated benchmark reports and holdout predictions.
          </p>
        </div>
        <button
          className="btn btn-outline"
          onClick={() => fetchReport(selectedRunId)}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}
        >
          <RefreshCw size={15} className={loading ? 'spin' : ''} />
          Refresh Report
        </button>
      </div>

      {/* Dynamic Evaluation Integrity Panel */}
      <EvaluationIntegrityPanel
        runs={runs}
        selectedRunId={selectedRunId}
        onSelectRun={(id) => setSelectedRunId(id)}
        integrity={report?.integrity || {}}
        loading={loading}
      />

      {/* Model Selection Tabs for Detailed Inspection */}
      {report?.models && (
        <div style={{ marginBottom: 16, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)' }}>
            Inspect Algorithm:
          </span>
          {Object.entries(report.models).map(([key, m]) => {
            const isSelected = key === selectedModelKey;
            const isEvaluated = m.evaluated !== false && m.status !== 'Not evaluated' && m.accuracy !== null;
            return (
              <button
                key={key}
                onClick={() => setSelectedModelKey(key)}
                className={`btn ${isSelected ? 'btn-primary' : 'btn-outline'}`}
                style={{
                  padding: '6px 14px',
                  fontSize: 12,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  borderColor: isSelected ? 'var(--accent-cyan)' : 'var(--border-subtle)',
                }}
              >
                {m.name || key}
                {!isEvaluated && (
                  <span style={{ fontSize: 10, color: 'var(--accent-yellow)', opacity: 0.9 }}>
                    (Not evaluated)
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Selected Model Metric Summary Cards */}
      {activeModel && (
        <section className="model-metric-grid" aria-label="Selected evaluation run metrics" style={{ marginBottom: 24 }}>
          {[
            ['Accuracy', activeModel.accuracy, 2],
            ['Macro-F1', activeModel.macro_f1, 2],
            ['Macro-Recall', activeModel.macro_recall, 2],
            ['Macro-Precision', activeModel.macro_precision, 2],
            ['Macro ROC-AUC', activeModel.roc_auc, 2],
          ].map(([label, val, digits]) => {
            const isEvaluated = activeModel.evaluated !== false && activeModel.status !== 'Not evaluated' && activeModel.accuracy !== null;
            const displayValue = !isEvaluated ? 'Not evaluated' : formatPercent(val, digits);
            return (
              <div className="stat-card model-metric-card" key={label}>
                <div className="stat-content">
                  <h3 style={{ fontSize: isEvaluated ? undefined : 18 }}>{displayValue}</h3>
                  <p>{label}</p>
                  <div className="stat-change">
                    {activeModel.name || 'Random Forest'} · {report?.run_id === 'deduplicated' ? 'Leak-Free Evaluation' : 'Historical Split'}
                  </div>
                </div>
              </div>
            );
          })}
        </section>
      )}

      {/* Loading State */}
      {loading && (
        <div className="card" role="status" style={{ padding: 36, textAlign: 'center', marginBottom: 24 }}>
          <RefreshCw size={28} className="spin" style={{ color: 'var(--accent-cyan)', margin: '0 auto 12px' }} />
          <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
            Loading validated evaluation artifacts for {selectedRunId}…
          </div>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="card model-analytics-error" role="alert" style={{ marginBottom: 24, display: 'flex', alignItems: 'center', gap: 14 }}>
          <AlertTriangle size={24} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
          <div style={{ flex: 1 }}>
            <strong style={{ color: 'var(--accent-red)' }}>Evaluation report unavailable</strong>
            <p style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--text-secondary)' }}>{error}</p>
          </div>
          <button className="btn btn-outline" onClick={() => fetchReport(selectedRunId)}>Retry</button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && (!report || !report.classes?.length) && (
        <div className="card" style={{ padding: 36, textAlign: 'center', marginBottom: 24, color: 'var(--text-muted)' }}>
          No evaluation data is available for this run.
        </div>
      )}

      {/* Interactive Charts (when report is loaded) */}
      {!loading && !error && report && (
        <>
          {/* 1. Dynamic Model Comparison */}
          <DynamicModelComparison
            models={report.models || {}}
            referenceBaseline={report.reference_baseline}
            runLabel={report.run_label}
          />

          {/* 2. Interactive Confusion Matrix */}
          <InteractiveConfusionMatrix
            models={report.models}
            selectedModelKey={selectedModelKey}
            onSelectModel={setSelectedModelKey}
            classNames={classes}
            modelName={activeModel?.name || 'Random Forest'}
            runLabel={report.run_label}
          />

          {/* 3. Interactive Per-Class Performance */}
          <PerClassPerformanceChart
            perClassStats={activePerClassStats}
            modelName={activeModel?.name || 'Random Forest'}
            runLabel={report.run_label}
          />

          {/* 4. Dataset Distribution Chart */}
          <DatasetDistributionChart
            distribution={report.dataset_distribution || []}
            runLabel={report.run_label}
          />
        </>
      )}
    </div>
  );
}
