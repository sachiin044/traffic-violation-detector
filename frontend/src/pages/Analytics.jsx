import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { getDashboardSummary, getHotspots, getTopPlates, getTrends } from '../services/api';
import useRequest from '../lib/useRequest';
import { VIOLATIONS } from '../lib/violations';
import { formatDay, formatNumber, plural } from '../lib/format';
import { EmptyState, ErrorState, PageHead, Plate, SkeletonRows } from '../components/desk';

const SUMMARY_KEYS = ['helmet', 'triple_riding', 'seatbelt', 'red_light', 'illegal_parking'];

async function loadAnalytics() {
  const [summary, trends, hotspots, topPlates] = await Promise.all([
    getDashboardSummary(),
    getTrends(),
    getHotspots(),
    getTopPlates(8),
  ]);
  return { summary, trends: trends || [], hotspots: hotspots || [], topPlates: topPlates || [] };
}

function TrendTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const rows = [...payload].sort((a, b) => b.value - a.value);
  return (
    <div className="vd-tooltip">
      <p>{formatDay(label)}</p>
      {rows.map((p) => (
        <div key={p.dataKey}>
          <i style={{ background: p.color }} />
          {p.name}
          <b>{formatNumber(p.value)}</b>
        </div>
      ))}
    </div>
  );
}

function TrendPanel({ trends }) {
  const [asTable, setAsTable] = useState(false);
  // Only series that actually occur; colour stays tied to the violation type
  const series = VIOLATIONS.filter((v) => trends.some((d) => (d[v.key] || 0) > 0));
  const data = trends.map((d) => {
    const row = { date: d.date };
    series.forEach((s) => { row[s.key] = d[s.key] || 0; });
    return row;
  });

  return (
    <section className="vd-panel" aria-labelledby="trend-title">
      <div className="vd-panel-head">
        <h2 className="vd-panel-title" id="trend-title">Violations per day</h2>
        {data.length > 0 && (
          <button type="button" className="vd-toggle-link" onClick={() => setAsTable((t) => !t)}>
            {asTable ? 'Show as chart' : 'Show as table'}
          </button>
        )}
      </div>

      {data.length === 0 ? (
        <EmptyState title="No days to show yet">Daily counts appear once evidence has been recorded.</EmptyState>
      ) : asTable ? (
        <div className="vd-table-wrap">
          <table className="vd-table">
            <thead>
              <tr>
                <th>Day</th>
                {series.map((s) => <th key={s.key} className="is-num">{s.name}</th>)}
              </tr>
            </thead>
            <tbody>
              {data.map((d) => (
                <tr key={d.date}>
                  <td>{formatDay(d.date)}</td>
                  {series.map((s) => <td key={s.key} className="is-num">{formatNumber(d[s.key])}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <>
          <div className="vd-chart">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
                <CartesianGrid vertical={false} />
                <XAxis dataKey="date" tickFormatter={formatDay} tickLine={false} axisLine={{ stroke: '#d2d7dd' }} tickMargin={10} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} width={44} />
                <Tooltip content={<TrendTooltip />} cursor={{ stroke: '#8a939d', strokeWidth: 1 }} />
                {series.map((s) => (
                  <Line
                    key={s.key}
                    type="linear"
                    dataKey={s.key}
                    name={s.name}
                    stroke={s.color}
                    strokeWidth={2}
                    dot={{ r: 4, fill: s.color, stroke: '#fff', strokeWidth: 2 }}
                    activeDot={{ r: 5, stroke: '#fff', strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="vd-legend-row" aria-label="Legend">
            {series.map((s) => (
              <span key={s.key}><i style={{ background: s.color }} aria-hidden="true" />{s.name}</span>
            ))}
          </div>
        </>
      )}
    </section>
  );
}

function Breakdown({ summary }) {
  const rows = VIOLATIONS.filter((v) => SUMMARY_KEYS.includes(v.key))
    .map((v) => ({ ...v, value: summary[v.key] || 0 }))
    .sort((a, b) => b.value - a.value);
  const total = rows.reduce((n, r) => n + r.value, 0);
  const max = Math.max(1, ...rows.map((r) => r.value));

  return (
    <section className="vd-panel" aria-labelledby="mix-title">
      <div className="vd-panel-head">
        <h2 className="vd-panel-title" id="mix-title">Share by type</h2>
        <span className="vd-panel-note">{formatNumber(total)} in total</span>
      </div>
      <div className="vd-hbars">
        {rows.map((r) => (
          <div className="vd-hbar" key={r.key} style={{ gridTemplateColumns: '150px minmax(0,1fr) 84px' }}>
            <span className="vd-hbar-name">
              <i style={{ background: r.color }} aria-hidden="true" />
              {r.name}
            </span>
            <span className="vd-hbar-track" aria-hidden="true">
              <span className="vd-hbar-fill" style={{ width: `${(r.value / max) * 100}%`, background: r.color }} />
            </span>
            <span className="vd-hbar-val">
              {formatNumber(r.value)}
              <span style={{ color: 'var(--vd-muted)', fontWeight: 400, marginLeft: 8 }}>
                {total ? Math.round((r.value / total) * 100) : 0}%
              </span>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function Hotspots({ hotspots }) {
  return (
    <section className="vd-panel vd-panel--flush" aria-labelledby="hot-title">
      <div className="vd-panel-head">
        <h2 className="vd-panel-title" id="hot-title">Busiest cameras</h2>
        <span className="vd-panel-note">Video uploads only</span>
      </div>
      {hotspots.length === 0 ? (
        <EmptyState title="No camera data yet">
          Cameras appear here after a video is checked with a camera ID.
        </EmptyState>
      ) : (
        <div className="vd-table-wrap" style={{ marginTop: 12 }}>
          <table className="vd-table">
            <thead>
              <tr><th>Camera</th><th>Location</th><th className="is-num">Evidence</th></tr>
            </thead>
            <tbody>
              {hotspots.map((h) => (
                <tr key={`${h.camera_id}-${h.location}`}>
                  <td className="is-id">{h.camera_id}</td>
                  <td>
                    {h.location || <span className="vd-plate-none">Not set</span>}
                    {Number.isFinite(h.latitude) && (
                      <div className="is-muted">{h.latitude.toFixed(4)}, {h.longitude.toFixed(4)}</div>
                    )}
                  </td>
                  <td className="is-num">{formatNumber(h.total_violations)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

function RepeatPlates({ plates }) {
  const repeat = plates.filter((p) => p.offenses > 0);
  return (
    <section className="vd-panel vd-panel--flush" aria-labelledby="plates-title">
      <div className="vd-panel-head">
        <h2 className="vd-panel-title" id="plates-title">Most recorded plates</h2>
        <span className="vd-panel-note">By evidence records</span>
      </div>
      {repeat.length === 0 ? (
        <EmptyState title="No plates read yet">Plates appear here once OCR reads them on flagged vehicles.</EmptyState>
      ) : (
        <div className="vd-table-wrap" style={{ marginTop: 12 }}>
          <table className="vd-table">
            <thead>
              <tr><th>Plate</th><th className="is-num">Records</th><th aria-label="Actions" /></tr>
            </thead>
            <tbody>
              {repeat.map((p) => (
                <tr key={p.plate_number}>
                  <td><Plate plate={p.plate_number} size="sm" /></td>
                  <td className="is-num">
                    {formatNumber(p.offenses)} {plural(p.offenses, 'record', 'records')}
                  </td>
                  <td className="is-num">
                    <Link className="vd-link" to={`/evidence?plate=${encodeURIComponent(p.plate_number)}`}>View</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

export default function Analytics() {
  const { data, error, loading, reload } = useRequest(loadAnalytics, []);

  return (
    <div className="vd-page">
      <PageHead title="Analytics" lede="How violations change over time, and where and by whom they happen most." />

      {loading && !data && (
        <div className="vd-stack">
          <div className="vd-panel"><SkeletonRows rows={1} height={280} /></div>
          <div className="vd-grid-2">
            <div className="vd-panel"><SkeletonRows rows={5} height={18} /></div>
            <div className="vd-panel"><SkeletonRows rows={5} height={18} /></div>
          </div>
        </div>
      )}

      {!data && error && (
        <div className="vd-panel"><ErrorState error={error} onRetry={reload} title="Couldn’t load analytics" /></div>
      )}

      {data && (
        <div className="vd-stack">
          <TrendPanel trends={data.trends} />
          <div className="vd-grid-2">
            <Breakdown summary={data.summary} />
            <RepeatPlates plates={data.topPlates} />
          </div>
          <Hotspots hotspots={data.hotspots} />
        </div>
      )}
    </div>
  );
}
