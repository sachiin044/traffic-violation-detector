import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { getAssetUrl, searchEvidence } from '../services/api';
import useRequest from '../lib/useRequest';
import useDebounced from '../lib/useDebounced';
import { VIOLATIONS, vehicleName } from '../lib/violations';
import { formatNumber, formatTime, pct } from '../lib/format';
import { EmptyState, ErrorState, PageHead, Plate, SkeletonRows, ViolationTags } from '../components/desk';

const PAGE_SIZE = 15;

export default function EvidenceExplorer() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const type = params.get('type') || '';
  const page = Math.max(0, Number(params.get('page') || 0));
  const [plateInput, setPlateInput] = useState(params.get('plate') || '');
  const plate = useDebounced(plateInput.trim().toUpperCase().replace(/\s+/g, ''));

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== 'page') next.delete('page');
    setParams(next, { replace: true });
  };

  useEffect(() => {
    if ((params.get('plate') || '') !== plate) setParam('plate', plate);
  }, [plate]);

  const { data, error, loading, reload } = useRequest(
    () => searchEvidence({
      skip: page * PAGE_SIZE,
      limit: PAGE_SIZE,
      plate_number: plate || undefined,
      violation_type: type || undefined,
    }),
    [page, plate, type],
  );

  const records = data?.records || [];
  const total = data?.total || 0;
  const filtered = Boolean(plate || type);
  const from = total ? page * PAGE_SIZE + 1 : 0;
  const to = Math.min((page + 1) * PAGE_SIZE, total);
  const open = (id) => navigate(`/evidence/${id}`);

  return (
    <div className="vd-page">
      <PageHead title="Evidence" lede="Every photo and video moment where a violation was found, newest first." />

      <section className="vd-panel vd-panel--flush">
        <div className="vd-toolbar" role="search">
          <label className="vd-field">
            Plate number
            <span className="vd-search">
              <Search aria-hidden="true" />
              <input
                className="vd-input"
                type="search"
                placeholder="e.g. OD02AK5678"
                value={plateInput}
                onChange={(e) => setPlateInput(e.target.value)}
              />
            </span>
          </label>
          <label className="vd-field">
            Violation
            <select className="vd-select" value={type} onChange={(e) => setParam('type', e.target.value)}>
              <option value="">All violations</option>
              {VIOLATIONS.map((v) => <option key={v.type} value={v.type}>{v.name}</option>)}
            </select>
          </label>
          {filtered && (
            <button
              type="button"
              className="vd-toggle-link"
              style={{ paddingBottom: 11 }}
              onClick={() => { setPlateInput(''); setParams({}, { replace: true }); }}
            >
              Clear filters
            </button>
          )}
          <span className="vd-toolbar-end">
            {data && `${formatNumber(total)} ${total === 1 ? 'record' : 'records'}`}
          </span>
        </div>

        {loading && !data && <SkeletonRows rows={6} />}
        {error && !data && <ErrorState error={error} onRetry={reload} title="Couldn’t load evidence" />}

        {data && records.length === 0 && (
          filtered ? (
            <EmptyState title="No evidence matches these filters">Try another plate number or violation.</EmptyState>
          ) : (
            <EmptyState title="No evidence yet">
              Evidence is saved when a checked photo or video has at least one violation.
            </EmptyState>
          )
        )}

        {records.length > 0 && (
          <div className="vd-table-wrap" style={{ opacity: loading ? 0.6 : 1 }}>
            <table className="vd-table">
              <thead>
                <tr>
                  <th aria-label="Photo" />
                  <th>Evidence</th>
                  <th>Plate</th>
                  <th>Vehicle</th>
                  <th>Violations</th>
                  <th className="is-num">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {records.map((r) => (
                  <tr
                    key={r.evidence_id}
                    className="vd-row-link"
                    tabIndex={0}
                    onClick={() => open(r.evidence_id)}
                    onKeyDown={(e) => { if (e.key === 'Enter') open(r.evidence_id); }}
                  >
                    <td style={{ width: 88 }}>
                      <img className="vd-thumb" src={getAssetUrl(r.thumbnail_path)} alt="" loading="lazy" />
                    </td>
                    <td>
                      <div className="is-id">{r.evidence_id}</div>
                      <div className="is-muted">
                        {formatTime(r.timestamp)}
                        {r.camera_id ? ` on ${r.camera_id}` : ''}
                      </div>
                    </td>
                    <td><Plate plate={r.plate_number} size="sm" /></td>
                    <td>{vehicleName(r.vehicle_type)}</td>
                    <td><ViolationTags types={r.violations} /></td>
                    <td className="is-num">{pct(r.confidence)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {total > PAGE_SIZE && (
          <div className="vd-pager">
            <span>Showing {from} to {to} of {formatNumber(total)}</span>
            <span className="vd-head-actions">
              <button type="button" className="vd-btn" disabled={page === 0} onClick={() => setParam('page', String(page - 1))}>
                Previous
              </button>
              <button type="button" className="vd-btn" disabled={to >= total} onClick={() => setParam('page', String(page + 1))}>
                Next
              </button>
            </span>
          </div>
        )}
      </section>
    </div>
  );
}
