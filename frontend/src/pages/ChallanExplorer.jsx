import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import { getChallans } from '../services/api';
import useRequest from '../lib/useRequest';
import useDebounced from '../lib/useDebounced';
import { CHALLAN_STATUSES, vehicleName } from '../lib/violations';
import { formatNumber, formatTime, inr, pctExact } from '../lib/format';
import { EmptyState, ErrorState, PageHead, Plate, SkeletonRows, StatusPill, ViolationTags } from '../components/desk';

const PAGE_SIZE = 20;

export default function ChallanExplorer() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const status = params.get('status') || '';
  const page = Math.max(0, Number(params.get('page') || 0));
  const [plateInput, setPlateInput] = useState(params.get('plate') || '');
  const plate = useDebounced(plateInput.trim().toUpperCase().replace(/\s+/g, ''));

  const setParam = (key, value) => {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value); else next.delete(key);
    if (key !== 'page') next.delete('page');
    setParams(next, { replace: true });
  };

  // Keep the plate filter in the URL once typing settles
  useEffect(() => {
    if ((params.get('plate') || '') !== plate) setParam('plate', plate);
  }, [plate]);

  const { data, error, loading, reload } = useRequest(
    () => getChallans({
      limit: PAGE_SIZE,
      skip: page * PAGE_SIZE,
      status: status || undefined,
      plate_number: plate || undefined,
    }),
    [status, plate, page],
  );

  const records = data?.records || [];
  const total = data?.total || 0;
  const filtered = Boolean(status || plate);
  const from = total ? page * PAGE_SIZE + 1 : 0;
  const to = Math.min((page + 1) * PAGE_SIZE, total);

  const open = (id) => navigate(`/challan/${id}`);

  return (
    <div className="vd-page">
      <PageHead title="Challans" lede="Every notice created from evidence. Open one to review, issue or close it." />

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
            Status
            <select className="vd-select" value={status} onChange={(e) => setParam('status', e.target.value)}>
              <option value="">All statuses</option>
              {CHALLAN_STATUSES.filter((s) => s.value !== 'PENDING').map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
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
            {data && `${formatNumber(total)} ${total === 1 ? 'challan' : 'challans'}`}
          </span>
        </div>

        {loading && !data && <SkeletonRows rows={6} />}
        {error && !data && <ErrorState error={error} onRetry={reload} title="Couldn’t load challans" />}

        {data && records.length === 0 && (
          filtered ? (
            <EmptyState title="No challans match these filters">Try another plate number or status.</EmptyState>
          ) : (
            <EmptyState title="No challans yet">
              A challan is created when evidence has a readable plate and a violation at 70% confidence or more.
            </EmptyState>
          )
        )}

        {records.length > 0 && (
          <div className="vd-table-wrap" style={{ opacity: loading ? 0.6 : 1 }}>
            <table className="vd-table">
              <thead>
                <tr>
                  <th>Challan</th>
                  <th>Plate</th>
                  <th>Violation</th>
                  <th>Vehicle</th>
                  <th className="is-num">Confidence</th>
                  <th className="is-num">Fine</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {records.map((c) => (
                  <tr
                    key={c.challan_id}
                    className="vd-row-link"
                    tabIndex={0}
                    onClick={() => open(c.challan_id)}
                    onKeyDown={(e) => { if (e.key === 'Enter') open(c.challan_id); }}
                  >
                    <td>
                      <div className="is-id">{c.challan_id}</div>
                      <div className="is-muted">{formatTime(c.created_at || c.timestamp)}</div>
                    </td>
                    <td><Plate plate={c.plate_number} size="sm" /></td>
                    <td><ViolationTags types={[c.violation_type]} /></td>
                    <td>{vehicleName(c.vehicle_type)}</td>
                    <td className="is-num">{pctExact(c.confidence)}</td>
                    <td className="is-num">{inr(c.fine_amount)}</td>
                    <td><StatusPill status={c.status} /></td>
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
