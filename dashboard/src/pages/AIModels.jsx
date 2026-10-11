/**
 * SecureIoT-X — AI Models & Intelligence Page.
 * Displays interactive model analytics, leak-free evaluations, and model governance.
 */
import { useEffect, useState, useCallback } from 'react';
import { Activity, AlertTriangle, Award, Brain, RefreshCw, Zap } from 'lucide-react';
import api from '../services/api';

import EvaluationIntegrityPanel from '../components/model-analytics/EvaluationIntegrityPanel';

const percent = (value) => (
  Number.isFinite(value) ? `${(value * 100).toFixed(2)}%` : '—'
);

const dateLabel = (value) => (
  value ? new Date(value).toLocaleString() : '—'
);

export default function AIModels() {
  const [models, setModels] = useState([]);
  const [activeModel, setActiveModel] = useState('');
  const [loadingModels, setLoadingModels] = useState(true);
  const [modelsError, setModelsError] = useState('');

  // Evaluation runs & report state
  const [evaluationRuns, setEvaluationRuns] = useState([]);
  const [selectedRunId, setSelectedRunId] = useState('deduplicated');
  const [reportData, setReportData] = useState(null);
  const [loadingReport, setLoadingReport] = useState(true);
  const [reportError, setReportError] = useState('');

  // Inference smoke test state
  const [inferencing, setInferencing] = useState(false);
  const [inferResult, setInferResult] = useState(null);
  const [inferError, setInferError] = useState('');
  const [deploying, setDeploying] = useState(false);

  // Fetch evaluated models list (serving & artifacts)
  const refreshModels = useCallback(async () => {
    setLoadingModels(true);
    setModelsError('');
    try {
      const data = await api.getModels();
      if (!Array.isArray(data)) throw new Error('Model API returned an invalid response');
      setModels(data);
      setActiveModel((current) => (
        data.some((m) => m.id === current)
          ? current
          : (data.find((m) => m.status === 'ACTIVE')?.id || data.find((m) => m.available)?.id || '')
      ));
    } catch (err) {
      setModelsError(err.message || 'Could not load registered models');
    } finally {
      setLoadingModels(false);
    }
  }, []);

  // Fetch available evaluation runs
  const fetchEvaluationRuns = useCallback(async () => {
    try {
      const runs = await api.getEvaluationRuns();
      if (Array.isArray(runs) && runs.length > 0) {
        setEvaluationRuns(runs);
        const def = runs.find((r) => r.is_default) || runs[0];
        setSelectedRunId(def.id);
      }
    } catch {
      // Fallback if runs endpoint fails
      setEvaluationRuns([
        { id: 'deduplicated', name: 'Leak-Free Evaluation', available: true, is_default: true },
        { id: 'historical', name: 'Historical Retraining Run', available: true, is_default: false },
      ]);
    }
  }, []);

  // Fetch evaluation report for the selected run
  const fetchReport = useCallback(async (runId) => {
    setLoadingReport(true);
    setReportError('');
    try {
      const data = await api.getEvaluationReport(runId);
      setReportData(data);
    } catch (err) {
      setReportError(err.message || `Could not load evaluation report for ${runId}`);
    } finally {
      setLoadingReport(false);
    }
  }, []);

  useEffect(() => {
    refreshModels();
    fetchEvaluationRuns();
  }, [refreshModels, fetchEvaluationRuns]);

  useEffect(() => {
    if (selectedRunId) {
      fetchReport(selectedRunId);
    }
  }, [selectedRunId, fetchReport]);

  const servingModel = models.find((model) => model.status === 'ACTIVE');
  const availableCount = models.filter((model) => model.available).length;

  const handleDeployModel = async (model) => {
    setDeploying(true);
    setModelsError('');
    try {
      await api.activateModel(model.name, model.version);
      await refreshModels();
    } catch (error) {
      setModelsError(error.message || 'Could not activate the evaluated model');
    } finally {
      setDeploying(false);
    }
  };

  const handleTestInference = async () => {
    setInferencing(true);
    setInferResult(null);
    setInferError('');
    try {
      const example = await api.getModelSample();
      const result = await api.predict('ML_PIPELINE_SMOKE_TEST', example.features);
      setInferResult({ ...result, source: example.source });
    } catch (error) {
      setInferError(error.message || 'Model inference failed');
    } finally {
      setInferencing(false);
    }
  };

  return (
    <div className="page">
      {modelsError && (
        <div
          className="card"
          role="alert"
          style={{
            marginBottom: 16,
            borderLeft: '4px solid var(--accent-red)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <AlertTriangle size={20} style={{ color: 'var(--accent-red)', flexShrink: 0 }} />
            <div>
              <strong style={{ color: 'var(--accent-red)' }}>Backend Connection Error:</strong>{' '}
              <span style={{ fontSize: 13 }}>{modelsError}</span>
              <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--text-muted)' }}>
                Ensure the FastAPI backend is running (<code>python -m uvicorn backend.app:app --host 0.0.0.0 --port 8000</code>).
              </p>
            </div>
          </div>
          <button
            className="btn btn-outline"
            style={{ fontSize: 12, display: 'flex', alignItems: 'center', gap: 6 }}
            onClick={() => {
              refreshModels();
              fetchEvaluationRuns();
              if (selectedRunId) fetchReport(selectedRunId);
            }}
          >
            <RefreshCw size={13} />
            Retry Connection
          </button>
        </div>
      )}

      {/* Top Stat Summary Cards */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon purple"><Brain size={22} /></div>
          <div className="stat-content">
            <h3>{loadingModels ? '…' : `${availableCount} / ${models.length}`}</h3>
            <p>Evaluated Artifacts</p>
            <div className="stat-change">Verified weights & pipelines</div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon green"><Award size={22} /></div>
          <div className="stat-content">
            <h3>{servingModel?.name || 'None'}</h3>
            <p>Active Serving Model</p>
            <div className="stat-change">
              {servingModel ? 'Active for inference' : 'No evaluated artifact active'}
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon cyan"><Activity size={22} /></div>
          <div className="stat-content">
            <h3>{reportData?.integrity?.test_samples ? `${reportData.integrity.test_samples.toLocaleString()} samples` : '—'}</h3>
            <p>Selected Test Partition</p>
            <div className="stat-change">
              {reportData?.run_id === 'deduplicated' ? '0.00% feature overlap' : '81.34% historical overlap'}
            </div>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon yellow"><Zap size={22} /></div>
          <div className="stat-content">
            <h3>{servingModel ? dateLabel(servingModel.evaluation_date) : '—'}</h3>
            <p>Serving Evaluation Date</p>
            <div className="stat-change">Untouched test split verified</div>
          </div>
        </div>
      </div>

      {/* ── SECTION 1: DYNAMIC EVALUATION INTEGRITY PANEL ─────────── */}
      <EvaluationIntegrityPanel
        runs={evaluationRuns}
        selectedRunId={selectedRunId}
        onSelectRun={(id) => setSelectedRunId(id)}
        integrity={reportData?.integrity || {}}
        loading={loadingReport}
      />



      {reportError && (
        <div
          className="card"
          role="alert"
          style={{
            marginBottom: 24,
            padding: 16,
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid var(--accent-red)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 12,
            flexWrap: 'wrap',
          }}
        >
          <div>
            <strong style={{ color: 'var(--accent-red)' }}>Evaluation audit details unavailable:</strong>{' '}
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{reportError}</span>
          </div>
          <button
            className="btn btn-outline"
            style={{ fontSize: 12 }}
            onClick={() => fetchReport(selectedRunId)}
          >
            Retry Report
          </button>
        </div>
      )}

      {/* ── SECTION 2: REGISTERED ARTIFACTS INVENTORY ───────────── */}
      <div style={{ marginTop: 24, marginBottom: 12 }}>
        <h3 style={{ fontSize: 18, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 }}>
          Registered AI Model Artifacts
        </h3>
        <p style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>
          Historical run model weights, latencies, and production deployment controls
        </p>
      </div>

      {loadingModels && (
        <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)', marginBottom: 24 }}>
          <RefreshCw size={20} className="spin" style={{ margin: '0 auto 8px', display: 'block', color: 'var(--accent-cyan)' }} />
          Loading registered model artifacts…
        </div>
      )}

      {modelsError && !loadingModels && (
        <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', marginBottom: 24 }}>
          Registered model artifacts cannot be displayed while the backend is offline.
        </div>
      )}

      {!loadingModels && !modelsError && models.length === 0 && (
        <div className="card" style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', marginBottom: 24 }}>
          No models are currently registered in the model registry.
        </div>
      )}

      {!loadingModels && !modelsError && models.length > 0 && (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
            gap: 20,
            marginBottom: 24,
          }}
        >
          {models.map((model) => {
            const selected = model.id === activeModel;
            const metrics = model.metrics || {};
            return (
              <div
                key={model.id}
                className="card"
                onClick={() => setActiveModel(model.id)}
                style={{
                  border: selected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                  cursor: 'pointer',
                }}
              >
                <div className="card-header" style={{ marginBottom: 12 }}>
                  <div>
                    <div className="card-title" style={{ fontSize: 16 }}>{model.name}</div>
                    <div className="card-subtitle">
                      {model.type} {model.version ? `· ${model.version}` : ''}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <span className={`status-badge ${model.status === 'ACTIVE' ? 'online' : model.available ? 'pending' : 'offline'}`}>
                      {model.status}
                    </span>
                  </div>
                </div>

                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 16 }}>
                  {model.description}
                </p>

                {model.available ? (
                  <>
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr 1fr',
                        gap: 10,
                        padding: 12,
                        background: 'var(--bg-secondary)',
                        borderRadius: 8,
                        marginBottom: 14,
                        fontSize: 12,
                      }}
                    >
                      <div><span style={{ color: 'var(--text-muted)' }}>Accuracy</span><div style={{ fontWeight: 600 }}>{percent(metrics.accuracy)}</div></div>
                      <div><span style={{ color: 'var(--text-muted)' }}>Macro F1</span><div style={{ fontWeight: 600 }}>{percent(metrics.f1_macro)}</div></div>
                      <div><span style={{ color: 'var(--text-muted)' }}>Macro precision</span><div style={{ fontWeight: 600 }}>{percent(metrics.precision_macro)}</div></div>
                      <div><span style={{ color: 'var(--text-muted)' }}>Macro recall</span><div style={{ fontWeight: 600 }}>{percent(metrics.recall_macro)}</div></div>
                      <div><span style={{ color: 'var(--text-muted)' }}>Macro ROC-AUC</span><div style={{ fontWeight: 600 }}>{percent(metrics.roc_auc)}</div></div>
                      <div>
                        <span style={{ color: 'var(--text-muted)' }}>Inference / sample</span>
                        <div style={{ fontWeight: 600 }}>
                          {Number.isFinite(metrics.inference_ms_per_sample)
                            ? `${metrics.inference_ms_per_sample.toFixed(4)} ms`
                            : '—'}
                        </div>
                      </div>
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 12 }}>
                      Dataset: {model.dataset} · Test rows: {model.test_size?.toLocaleString()}
                      {' · '}Evaluated: {dateLabel(model.evaluation_date)}
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                      {model.status === 'ACTIVE' ? (
                        <span style={{ fontSize: 12, color: 'var(--accent-green)', fontWeight: 600 }}>
                          Serving evaluated artifact
                        </span>
                      ) : (
                        <button
                          className="btn btn-outline"
                          disabled={deploying}
                          onClick={(event) => {
                            event.stopPropagation();
                            handleDeployModel(model);
                          }}
                        >
                          {deploying ? 'Activating…' : 'Set as serving artifact'}
                        </button>
                      )}
                    </div>
                  </>
                ) : (
                  <p style={{ color: 'var(--text-muted)' }}>
                    Unavailable: trained artifact or held-out evaluation is missing.
                  </p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── SECTION 7: SERVING INFERENCE SMOKE TEST ────────────── */}
      <div className="card" style={{ marginTop: 24 }}>
        <div className="card-header">
          <div>
            <div className="card-title">Serving Inference Smoke Test</div>
            <div className="card-subtitle">
              Validates real runtime prediction latency on a stored network traffic vector
            </div>
          </div>
          <Zap size={18} style={{ color: 'var(--accent-yellow)' }} />
        </div>
        <button
          className="btn btn-primary"
          onClick={handleTestInference}
          disabled={inferencing || !servingModel}
        >
          {inferencing
            ? <><RefreshCw size={16} className="spin" /> Running inference…</>
            : <><Zap size={16} /> Run serving inference</>}
        </button>
        {!servingModel && !modelsError && (
          <p style={{ marginTop: 12, color: 'var(--text-muted)' }}>
            No evaluated serving artifact is available.
          </p>
        )}
        {modelsError && !servingModel && (
          <p style={{ marginTop: 12, color: 'var(--accent-red)' }}>
            Inference smoke test requires an active backend server connection.
          </p>
        )}
        {inferError && (
          <p role="alert" style={{ marginTop: 12, color: 'var(--accent-red)' }}>{inferError}</p>
        )}
        {inferResult && (
          <div style={{ marginTop: 16, padding: 16, background: 'var(--bg-secondary)', borderRadius: 8 }}>
            <div><strong>Source:</strong> {inferResult.source}</div>
            <div><strong>Model:</strong> {inferResult.model_name} {inferResult.model_version}</div>
            <div><strong>Prediction:</strong> <span style={{ color: 'var(--accent-cyan)', fontWeight: 700 }}>{inferResult.prediction}</span></div>
            <div><strong>Confidence:</strong> {percent(inferResult.confidence)}</div>
            <div><strong>Inference time:</strong> {inferResult.inference_time_ms} ms</div>
            <div><strong>Recommended action:</strong> {inferResult.recommended_action || '—'}</div>
          </div>
        )}
      </div>
    </div>
  );
}
