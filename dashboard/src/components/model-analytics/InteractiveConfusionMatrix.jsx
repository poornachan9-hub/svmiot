import React, { useState, useMemo } from 'react';
import { Grid, Filter } from 'lucide-react';

export default function InteractiveConfusionMatrix({
  matrix: propMatrix = [],
  classNames: propClassNames = [],
  classes = [],
  modelName: propModelName = 'RandomForest',
  models = null,
  selectedModelKey: controlledModelKey = null,
  onSelectModel = null,
  runLabel,
  runName = 'Evaluation',
}) {
  const classNames = useMemo(() => {
    return (propClassNames && propClassNames.length) ? propClassNames : (classes || []);
  }, [propClassNames, classes]);
  const activeRunLabel = runLabel || runName;

  // Available models when models dict is provided
  const modelList = useMemo(() => {
    if (!models || typeof models !== 'object') return [];
    return Object.entries(models).map(([key, m]) => ({
      key,
      name: m.name || key,
      evaluated: m.evaluated !== false && !!m.confusion_matrix,
      matrix: m.confusion_matrix,
    }));
  }, [models]);

  const [internalModelKey, setInternalModelKey] = useState(() => {
    if (controlledModelKey) return controlledModelKey;
    if (models?.RandomForest) return 'RandomForest';
    if (modelList.length > 0) return modelList[0].key;
    return 'RandomForest';
  });

  const activeModelKey = controlledModelKey || internalModelKey;

  const handleModelChange = (newKey) => {
    setInternalModelKey(newKey);
    if (onSelectModel) onSelectModel(newKey);
  };

  const activeModelObj = models ? models[activeModelKey] : null;
  const matrix = activeModelObj ? activeModelObj.confusion_matrix : propMatrix;
  const modelName = activeModelObj ? (activeModelObj.name || activeModelKey) : propModelName;
  const isModelEvaluated = activeModelObj ? (activeModelObj.evaluated !== false && !!matrix) : true;

  const [viewMode, setViewMode] = useState('normalized'); // 'raw' | 'normalized'
  const [selectedClasses, setSelectedClasses] = useState([]); // empty = show all
  const [hoveredCell, setHoveredCell] = useState(null);

  // Calculate row sums for normalization
  const rowSums = useMemo(() => {
    if (!Array.isArray(matrix)) return [];
    return matrix.map((row) => (Array.isArray(row) ? row.reduce((a, b) => a + b, 0) : 0));
  }, [matrix]);

  // Total samples in matrix
  const totalSamples = useMemo(() => {
    return rowSums.reduce((a, b) => a + b, 0);
  }, [rowSums]);

  // Overall diagonal accuracy
  const diagonalAccuracy = useMemo(() => {
    if (!Array.isArray(matrix) || !matrix.length || totalSamples === 0) return 0;
    let diag = 0;
    for (let i = 0; i < matrix.length; i++) {
      if (matrix[i] && matrix[i][i] !== undefined) {
        diag += matrix[i][i];
      }
    }
    return (diag / totalSamples) * 100;
  }, [matrix, totalSamples]);

  // Filtered rows and columns
  const activeClassIndices = useMemo(() => {
    if (!selectedClasses.length) return classNames.map((_, i) => i);
    return classNames
      .map((name, i) => (selectedClasses.includes(name) ? i : -1))
      .filter((i) => i !== -1);
  }, [classNames, selectedClasses]);

  const handleToggleClass = (className) => {
    setSelectedClasses((prev) => {
      if (prev.includes(className)) {
        return prev.filter((c) => c !== className);
      }
      return [...prev, className];
    });
  };

  const handleSelectAll = () => setSelectedClasses([]);

  // Compute color based on percentage (0% to 100%)
  const getCellColor = (pct, isDiagonal) => {
    if (pct === 0) return 'rgba(255, 255, 255, 0.02)';
    if (isDiagonal) {
      if (pct > 90) return 'rgba(0, 212, 255, 0.85)';
      if (pct > 70) return 'rgba(0, 212, 255, 0.60)';
      if (pct > 40) return 'rgba(0, 212, 255, 0.40)';
      return 'rgba(0, 212, 255, 0.20)';
    } else {
      if (pct > 20) return 'rgba(239, 68, 68, 0.80)';
      if (pct > 10) return 'rgba(239, 68, 68, 0.50)';
      if (pct > 5) return 'rgba(245, 158, 11, 0.40)';
      return 'rgba(245, 158, 11, 0.20)';
    }
  };

  const getTextColor = (pct) => {
    if (pct > 50) return '#ffffff';
    if (pct > 0) return '#e2e8f0';
    return '#475569';
  };

  return (
    <div className="card" style={{ marginBottom: 24, position: 'relative' }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
        <div>
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Grid size={18} style={{ color: 'var(--accent-cyan)' }} />
            Interactive 12-Class Confusion Matrix Heatmap
          </div>
          <div className="card-subtitle">
            {modelName} · {activeRunLabel} · Total Test Samples: <strong>{totalSamples.toLocaleString()}</strong> · Diagonal Accuracy: <strong>{diagonalAccuracy.toFixed(2)}%</strong>
          </div>
        </div>

        {/* Model Switcher & Display Mode Toggles */}
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          {modelList.length > 1 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Model:</span>
              <select
                value={activeModelKey}
                onChange={(e) => handleModelChange(e.target.value)}
                style={{
                  background: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 6,
                  padding: '5px 10px',
                  fontSize: 12,
                  cursor: 'pointer',
                }}
              >
                {modelList.map((m) => (
                  <option key={m.key} value={m.key} disabled={!m.evaluated}>
                    {m.name} {!m.evaluated ? '(Not evaluated)' : ''}
                  </option>
                ))}
              </select>
            </div>
          )}

          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <button
              className={`btn ${viewMode === 'normalized' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: 12 }}
              onClick={() => setViewMode('normalized')}
              disabled={!isModelEvaluated}
            >
              Row-Normalized (%)
            </button>
            <button
              className={`btn ${viewMode === 'raw' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '6px 12px', fontSize: 12 }}
              onClick={() => setViewMode('raw')}
              disabled={!isModelEvaluated}
            >
              Raw Counts
            </button>
          </div>
        </div>
      </div>

      {!isModelEvaluated || !matrix || !matrix.length ? (
        <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
          {activeModelObj && !activeModelObj.evaluated
            ? `Not evaluated: ${modelName} has not been evaluated under this protocol.`
            : `No confusion matrix data available for ${modelName}.`}
        </div>
      ) : (
        <>

      {/* Class Focus Selector */}
      <div style={{ marginBottom: 16, padding: '10px 14px', background: 'var(--bg-secondary)', borderRadius: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Filter size={14} /> Filter Attack Classes to Display:
          </div>
          <button
            className="btn"
            style={{ fontSize: 11, padding: '3px 8px', background: 'transparent', color: 'var(--accent-cyan)' }}
            onClick={handleSelectAll}
          >
            Show All 12 Classes
          </button>
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {classNames.map((name) => {
            const isSelected = selectedClasses.includes(name);
            return (
              <button
                key={name}
                onClick={() => handleToggleClass(name)}
                style={{
                  fontSize: 11,
                  padding: '3px 8px',
                  borderRadius: 4,
                  cursor: 'pointer',
                  border: isSelected ? '1px solid var(--accent-cyan)' : '1px solid var(--border-subtle)',
                  background: isSelected ? 'rgba(0, 212, 255, 0.2)' : 'var(--bg-input)',
                  color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                }}
              >
                {name}
              </button>
            );
          })}
        </div>
      </div>

      {/* Heatmap Grid */}
      <div style={{ overflowX: 'auto', position: 'relative' }}>
        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, fontStyle: 'italic' }}>
          Vertical Axis: Actual Class ↓ | Horizontal Axis: Predicted Class →
        </div>

        <table
          style={{
            borderCollapse: 'collapse',
            fontSize: 11,
            width: '100%',
            minWidth: 720,
            tableLayout: 'fixed',
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  width: 140,
                  textAlign: 'left',
                  padding: '6px 8px',
                  background: 'var(--bg-primary)',
                  color: 'var(--text-secondary)',
                  borderBottom: '1px solid var(--border-subtle)',
                }}
              >
                Actual \ Pred
              </th>
              {activeClassIndices.map((colIdx) => (
                <th
                  key={classNames[colIdx]}
                  title={classNames[colIdx]}
                  style={{
                    padding: '6px 4px',
                    textAlign: 'center',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-secondary)',
                    borderBottom: '1px solid var(--border-subtle)',
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                  }}
                >
                  {classNames[colIdx].length > 10 ? `${classNames[colIdx].slice(0, 9)}…` : classNames[colIdx]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {activeClassIndices.map((rowIdx) => {
              const actualClass = classNames[rowIdx];
              const rowSum = rowSums[rowIdx] || 1;

              return (
                <tr key={actualClass}>
                  <td
                    style={{
                      padding: '6px 8px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      background: 'var(--bg-primary)',
                      borderRight: '1px solid var(--border-subtle)',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                    title={`${actualClass} (N=${rowSum})`}
                  >
                    {actualClass}
                    <span style={{ fontSize: 9, color: 'var(--text-muted)', marginLeft: 4 }}>({rowSum})</span>
                  </td>
                  {activeClassIndices.map((colIdx) => {
                    const predClass = classNames[colIdx];
                    const count = matrix[rowIdx]?.[colIdx] ?? 0;
                    const pct = rowSum > 0 ? (count / rowSum) * 100 : 0;
                    const isDiagonal = rowIdx === colIdx;
                    const bg = getCellColor(pct, isDiagonal);
                    const textColor = getTextColor(pct);
                    const isHovered = hoveredCell && hoveredCell.row === rowIdx && hoveredCell.col === colIdx;

                    return (
                      <td
                        key={`${rowIdx}-${colIdx}`}
                        onMouseEnter={() =>
                          setHoveredCell({
                            row: rowIdx,
                            col: colIdx,
                            actual: actualClass,
                            predicted: predClass,
                            count,
                            pct,
                            rowSum,
                          })
                        }
                        onMouseLeave={() => setHoveredCell(null)}
                        style={{
                          textAlign: 'center',
                          padding: '8px 2px',
                          background: isHovered ? 'rgba(255, 255, 255, 0.25)' : bg,
                          color: textColor,
                          fontWeight: count > 0 ? 600 : 400,
                          cursor: 'pointer',
                          transition: 'all 0.15s ease',
                          border: isHovered
                            ? '1px solid #ffffff'
                            : isDiagonal
                            ? '1px solid rgba(0, 212, 255, 0.25)'
                            : '1px solid rgba(255, 255, 255, 0.03)',
                        }}
                      >
                        {viewMode === 'normalized' ? (
                          pct > 0 ? `${pct.toFixed(pct < 10 ? 1 : 0)}%` : '0%'
                        ) : (
                          count.toLocaleString()
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Floating Hover Tooltip */}
      {hoveredCell && (
        <div
          style={{
            marginTop: 12,
            padding: '10px 14px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--accent-cyan)',
            borderRadius: 6,
            fontSize: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 16,
            boxShadow: 'var(--glow-cyan)',
          }}
        >
          <div>
            <strong style={{ color: 'var(--text-muted)' }}>Actual:</strong>{' '}
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{hoveredCell.actual}</span>{' '}
            <span style={{ color: 'var(--text-muted)' }}>(N={hoveredCell.rowSum})</span>
            {'  →  '}
            <strong style={{ color: 'var(--text-muted)' }}>Predicted:</strong>{' '}
            <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{hoveredCell.predicted}</span>
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Count:</span>{' '}
              <strong style={{ color: 'var(--accent-cyan)' }}>{hoveredCell.count.toLocaleString()}</strong>
            </div>
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Class Recall:</span>{' '}
              <strong style={{ color: hoveredCell.pct > 70 ? 'var(--accent-green)' : 'var(--accent-yellow)' }}>
                {hoveredCell.pct.toFixed(2)}%
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* Legend & Instructions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 12, fontSize: 11, color: 'var(--text-muted)' }}>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, background: 'rgba(0, 212, 255, 0.7)', borderRadius: 2 }} />
            <span>High Correct Recall (Diagonal)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, background: 'rgba(239, 68, 68, 0.7)', borderRadius: 2 }} />
            <span>Confusion / Misclassification</span>
          </div>
        </div>
        <div>Hover over any cell to inspect exact sample count and row percentage</div>
      </div>
        </>
      )}
    </div>
  );
}
