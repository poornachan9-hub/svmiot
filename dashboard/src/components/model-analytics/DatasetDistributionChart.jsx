import React, { useState, useMemo } from 'react';
import { Database, ArrowUpDown } from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';

export default function DatasetDistributionChart({
  distribution = [],
  runLabel,
  runName = 'Evaluation Dataset',
  totalSamples: propTotalSamples,
}) {
  const activeRunLabel = runLabel || runName;
  const [viewMode, setViewMode] = useState('count'); // 'count' | 'percentage'
  const [sortBy, setSortBy] = useState('count_desc'); // 'count_desc' | 'name_asc'

  const totalSamples = useMemo(() => {
    if (Number.isFinite(propTotalSamples) && propTotalSamples > 0) return propTotalSamples;
    return distribution.reduce((sum, item) => sum + (item.count || 0), 0);
  }, [distribution, propTotalSamples]);

  const sortedData = useMemo(() => {
    const list = [...distribution];
    if (sortBy === 'count_desc') {
      list.sort((a, b) => b.count - a.count);
    } else if (sortBy === 'name_asc') {
      list.sort((a, b) => a.class_name.localeCompare(b.class_name));
    }
    return list;
  }, [distribution, sortBy]);

  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <div className="card-header" style={{ flexWrap: 'wrap', gap: 12, marginBottom: 12 }}>
        <div>
          <div className="card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Database size={18} style={{ color: 'var(--accent-purple)' }} />
            Dataset Traffic & Attack Class Distribution
          </div>
          <div className="card-subtitle">
            Total Dataset Samples: <strong>{totalSamples.toLocaleString()}</strong> ({activeRunLabel})
          </div>
        </div>

        {/* View & Sort Controls */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          {/* Unit Toggle */}
          <div style={{ display: 'flex', gap: 4 }}>
            <button
              className={`btn ${viewMode === 'count' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '4px 10px', fontSize: 11 }}
              onClick={() => setViewMode('count')}
            >
              Raw Counts
            </button>
            <button
              className={`btn ${viewMode === 'percentage' ? 'btn-primary' : 'btn-outline'}`}
              style={{ padding: '4px 10px', fontSize: 11 }}
              onClick={() => setViewMode('percentage')}
            >
              Percentage (%)
            </button>
          </div>

          {/* Sort Selector */}
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <ArrowUpDown size={14} style={{ color: 'var(--text-muted)' }} />
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-subtle)',
                color: 'var(--text-primary)',
                padding: '4px 8px',
                borderRadius: 4,
                fontSize: 11,
              }}
            >
              <option value="count_desc">Sort by Count (High → Low)</option>
              <option value="name_asc">Sort by Name (A → Z)</option>
            </select>
          </div>
        </div>
      </div>

      {sortedData.length > 0 ? (
        <ResponsiveContainer width="100%" height={290}>
          <BarChart data={sortedData} margin={{ top: 10, right: 20, left: 20, bottom: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="class_name"
              angle={-35}
              textAnchor="end"
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              interval={0}
            />
            <YAxis
              tick={{ fill: '#64748b', fontSize: 11 }}
              unit={viewMode === 'percentage' ? '%' : ''}
            />
            <Tooltip
              formatter={(value, name, props) => [
                viewMode === 'percentage'
                  ? `${value}% (${props.payload.count.toLocaleString()} samples)`
                  : `${Number(value).toLocaleString()} samples (${props.payload.percentage}%)`,
                'Dataset Share',
              ]}
              contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-subtle)', borderRadius: 6 }}
            />
            <Bar
              dataKey={viewMode === 'percentage' ? 'percentage' : 'count'}
              fill="#8b5cf6"
              radius={[4, 4, 0, 0]}
            >
              {sortedData.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.percentage > 25 ? '#00d4ff' : '#8b5cf6'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      ) : (
        <p style={{ color: 'var(--text-muted)' }}>No dataset distribution available.</p>
      )}
    </div>
  );
}
