import React from 'react';
import { Link } from 'react-router-dom';
import { getEnforcementStats } from '../services/api';
import useRequest from '../lib/useRequest';
import { AUTO_THRESHOLD, REVIEW_THRESHOLD } from '../lib/violations';
import { formatNumber, inr, pct, plural } from '../lib/format';
import { ErrorState, PageHead, SkeletonRows, StatusPill, ThresholdBar } from '../components/desk';

// Challans move through these statuses in order; disputed sits outside the flow
const FLOW = [
  { status: 'REVIEW_REQUIRED', key: (s) => s.review_required + (s.pending || 0), text: 'Waiting for an officer to approve or reject' },
  { status: 'GENERATED', key: (s) => s.generated, text: 'Approved, notice not sent yet' },
  { status: 'ISSUED', key: (s) => s.issued, text: 'Notice sent to the vehicle owner' },
  { status: 'PAID', key: (s) => s.paid, text: 'Fine received, case closed' },
];

export default function EnforcementCenter() {
  const { data: stats, error, loading, reload } = useRequest(getEnforcementStats, [], { interval: 15000 });

  return (
    <div className="vd-page">
      <PageHead
        title="Enforcement"
        lede="Where every challan is in the process, and the rules that decide when one is created."
        actions={<Link className="vd-btn" to="/challans">Open challans</Link>}
      />

      {loading && !stats && <div className="vd-panel"><SkeletonRows rows={3} height={60} /></div>}
      {!stats && error && (
        <div className="vd-panel"><ErrorState error={error} onRetry={reload} title="Couldn’t load enforcement data" /></div>
      )}

      {stats && (
        <div className="vd-stack">
          <section className="vd-panel vd-panel--flush" aria-labelledby="flow-title">
            <div className="vd-panel-head">
              <h2 className="vd-panel-title" id="flow-title">Challan progress</h2>
              <span className="vd-panel-note">
                {formatNumber(stats.total_challans)} {plural(stats.total_challans, 'challan', 'challans')} in total
              </span>
            </div>
            <div className="vd-pipeline" style={{ marginTop: 8, borderTop: '1px solid var(--vd-rule)' }}>
              {FLOW.map((step) => (
                <Link key={step.status} className="vd-stage-step" to={`/challans?status=${step.status}`}>
                  <StatusPill status={step.status} />
                  <b>{formatNumber(step.key(stats) || 0)}</b>
                  <span className="vd-stage-step-note">{step.text}</span>
                </Link>
              ))}
            </div>
          </section>

          <div className="vd-grid-2">
            <section className="vd-panel" aria-labelledby="fines-title">
              <div className="vd-panel-head">
                <h2 className="vd-panel-title" id="fines-title">Fines</h2>
              </div>
              <div className="vd-amount">{inr(stats.estimated_fines)}</div>
              <p className="vd-sub">Total of all challans except disputed ones.</p>
              <dl className="vd-kv" style={{ marginTop: 16 }}>
                <dt>Evidence records</dt>
                <dd>{formatNumber(stats.total_violations)}</dd>
                <dt>Challans created</dt>
                <dd>{formatNumber(stats.total_challans)}</dd>
                <dt>
                  <Link to="/challans?status=DISPUTED" style={{ color: 'inherit', textDecoration: 'none' }}>
                    <StatusPill status="DISPUTED" />
                  </Link>
                </dt>
                <dd>{formatNumber(stats.disputed || 0)}</dd>
              </dl>
            </section>

            <section className="vd-panel" aria-labelledby="rules-title">
              <div className="vd-panel-head">
                <h2 className="vd-panel-title" id="rules-title">When a challan is created</h2>
              </div>
              <div className="vd-rules">
                <div className="vd-rule-row">
                  <b>Plate required</b>
                  <span>No challan is created when the number plate can’t be read. The evidence is still saved.</span>
                </div>
                <div className="vd-rule-row">
                  <b>{pct(AUTO_THRESHOLD)} and above</b>
                  <span>
                    The challan and its PDF notice are generated automatically.
                    <div style={{ marginTop: 10 }}><ThresholdBar confidence={0.92} label="Example: 92% confidence" /></div>
                  </span>
                </div>
                <div className="vd-rule-row">
                  <b>{pct(REVIEW_THRESHOLD)} to {pct(AUTO_THRESHOLD - 0.01)}</b>
                  <span>
                    The challan is created as Needs review and waits for an officer.
                    <div style={{ marginTop: 10 }}><ThresholdBar confidence={0.77} label="Example: 77% confidence" /></div>
                  </span>
                </div>
                <div className="vd-rule-row">
                  <b>Below {pct(REVIEW_THRESHOLD)}</b>
                  <span>
                    Counted in analytics only. You can still create a challan by hand from the evidence record.
                    <div style={{ marginTop: 10 }}><ThresholdBar confidence={0.55} label="Example: 55% confidence" /></div>
                  </span>
                </div>
              </div>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
