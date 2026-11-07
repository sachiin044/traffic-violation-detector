import React from 'react';
import { Link } from 'react-router-dom';
import { Camera } from 'lucide-react';
import { getAssetUrl, getDashboardSummary, getEnforcementStats, searchEvidence } from '../services/api';
import useRequest from '../lib/useRequest';
import { VIOLATIONS } from '../lib/violations';
import { formatNumber, formatTime, inr, pct, plural } from '../lib/format';
import {
  EmptyState,
  ErrorState,
  PageHead,
  Plate,
  SkeletonRows,
  StatusPill,
  ViolationTags,
} from '../components/desk';

const REFRESH_MS = 5000;

// The summary endpoint counts these five; wrong-side only comes from video
const SUMMARY_KEYS = ['helmet', 'triple_riding', 'seatbelt', 'red_light', 'illegal_parking'];

async function loadOverview() {
  const [summary, latest, enforcement] = await Promise.all([
    getDashboardSummary(),
    searchEvidence({ limit: 6 }),
    getEnforcementStats().catch(() => null),
  ]);
  return { summary, recent: latest?.records || [], enforcement };
}

function ViolationLedger({ summary }) {
  const rows = VIOLATIONS.filter((v) => SUMMARY_KEYS.includes(v.key)).map((v) => ({
    ...v,
    value: summary[v.key] || 0,
  }));
  const max = Math.max(1, ...rows.map((r) => r.value));

  return (
    <section className="vd-panel" aria-labelledby="ledger-title">
      <div className="vd-panel-head">
        <h2 className="vd-panel-title" id="ledger-title">Violations by type</h2>
        <span className="vd-panel-note">All time</span>
      </div>
      <div className="vd-ledger">
        <div className="vd-ledger-total">
          <div className="vd-big">{formatNumber(summary.total || 0)}</div>
          <p>
            evidence {plural(summary.total || 0, 'record', 'records')}. Each one is a photo or video moment with at
            least one violation, so it can count towards more than one type.
          </p>
        </div>
        <div className="vd-hbars">
          {rows.map((r) => (
            <div className="vd-hbar" key={r.key}>
              <span className="vd-hbar-name">
                <i style={{ background: r.color }} aria-hidden="true" />
                {r.name}
              </span>
              <span className="vd-hbar-track" aria-hidden="true">
                <span className="vd-hbar-fill" style={{ width: `${(r.value / max) * 100}%`, background: r.color }} />
              </span>
              <span className="vd-hbar-val">{formatNumber(r.value)}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function LatestEvidence({ records }) {
  return (
    <section className="vd-panel vd-panel--flush" aria-labelledby="latest-title">
      <div className="vd-panel-head">
        <h2 className="vd-panel-title" id="latest-title">Latest evidence</h2>
        <Link className="vd-link" to="/evidence">See all evidence</Link>
      </div>
      {records.length === 0 ? (
        <EmptyState
          title="No evidence yet"
          action={<Link className="vd-btn vd-btn--primary" to="/image">Check a photo</Link>}
        >
          Evidence appears here when a checked photo or video has at least one violation.
        </EmptyState>
      ) : (
        <ul className="vd-feed" style={{ marginTop: 12 }}>
          {records.map((r) => (
            <li key={r.evidence_id}>
              <Link to={`/evidence/${r.evidence_id}`}>
                <img className="vd-thumb" src={getAssetUrl(r.thumbnail_path)} alt="" loading="lazy" />
                <span className="vd-feed-main">
                  <span className="vd-feed-top">
                    <Plate plate={r.plate_number} size="sm" />
                  </span>
                  <ViolationTags types={r.violations} />
                </span>
                <span className="vd-feed-meta">
                  <b>{formatTime(r.timestamp)}</b>
                  {pct(r.confidence)} confidence
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ChallanSnapshot({ stats }) {
  if (!stats) return null;
  const rows = [
    { status: 'REVIEW_REQUIRED', value: stats.review_required + (stats.pending || 0) },
    { status: 'GENERATED', value: stats.generated },
    { status: 'ISSUED', value: stats.issued },
    { status: 'PAID', value: stats.paid },
    { status: 'DISPUTED', value: stats.disputed },
  ];
  return (
    <section className="vd-panel" aria-labelledby="challan-title">
      <div className="vd-panel-head">
        <h2 className="vd-panel-title" id="challan-title">Challans</h2>
        <Link className="vd-link" to="/challans">Open</Link>
      </div>
      <div className="vd-amount">
        {inr(stats.estimated_fines)}
      </div>
      <p className="vd-sub" style={{ marginTop: 8 }}>
        in fines across {formatNumber(stats.total_challans)} {plural(stats.total_challans, 'challan', 'challans')},
        not counting disputed ones.
      </p>
      <dl className="vd-kv" style={{ marginTop: 16 }}>
        {rows.map((r) => (
          <React.Fragment key={r.status}>
            <dt>
              <Link to={`/challans?status=${r.status}`} style={{ color: 'inherit', textDecoration: 'none' }}>
                <StatusPill status={r.status} />
              </Link>
            </dt>
            <dd>{formatNumber(r.value || 0)}</dd>
          </React.Fragment>
        ))}
      </dl>
    </section>
  );
}

export default function DashboardOverview() {
  const { data, error, loading, reload } = useRequest(loadOverview, [], { interval: REFRESH_MS });
  const live = !error || Boolean(data);

  return (
    <div className="vd-page">
      <PageHead
        title="Overview"
        lede="What has been caught so far, and what is waiting for a decision."
        actions={
          <>
            <span className="vd-live" data-state={error ? 'offline' : 'live'} style={{ alignSelf: 'center' }}>
              {error ? 'Not updating, the API is unreachable' : 'Updates every 5 seconds'}
            </span>
            <Link className="vd-btn vd-btn--primary" to="/image">
              <Camera aria-hidden="true" />
              Check a photo
            </Link>
          </>
        }
      />

      {loading && !data && (
        <div className="vd-stack">
          <div className="vd-panel"><SkeletonRows rows={4} height={22} /></div>
          <div className="vd-panel vd-panel--flush"><SkeletonRows rows={5} /></div>
        </div>
      )}

      {!data && error && (
        <div className="vd-panel">
          <ErrorState error={error} onRetry={reload} title="Couldn’t load the overview" />
        </div>
      )}

      {data && live && (
        <div className="vd-stack">
          <ViolationLedger summary={data.summary} />
          <div className="vd-grid-main">
            <LatestEvidence records={data.recent} />
            <ChallanSnapshot stats={data.enforcement} />
          </div>
        </div>
      )}
    </div>
  );
}
