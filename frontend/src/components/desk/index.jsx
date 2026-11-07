import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft, Inbox } from 'lucide-react';
import {
  AUTO_THRESHOLD,
  REVIEW_THRESHOLD,
  THRESHOLD_COPY,
  challanStatus,
  thresholdLevel,
  vehicleName,
  violationMeta,
} from '../../lib/violations';
import { errorMessage, formatPlate, pct, pctExact, plural } from '../../lib/format';
import { toFindings } from '../../lib/findings';
import useRto from '../../lib/useRto';

/* ── Page header ─────────────────────────────────────────────────────── */

export function PageHead({ title, lede, back, actions, badge }) {
  return (
    <header className="vd-page-head">
      <div>
        {back && (
          <Link className="vd-back" to={back.to}>
            <ArrowLeft aria-hidden="true" />
            {back.label}
          </Link>
        )}
        <div className="vd-title-row">
          <h1 className="vd-title">{title}</h1>
          {badge}
        </div>
        {lede && <p className="vd-lede">{lede}</p>}
      </div>
      {actions && <div className="vd-head-actions">{actions}</div>}
    </header>
  );
}

/* ── Number plate ────────────────────────────────────────────────────── */

export function Plate({ plate, size = 'lg' }) {
  const small = size === 'sm';
  if (!plate) {
    if (small) return <span className="vd-plate-none">Not read</span>;
    return (
      <div className="vd-plate is-missing">
        <span className="vd-plate-ind" aria-hidden="true"><i />IND</span>
        <span className="vd-plate-num">Plate not read</span>
      </div>
    );
  }
  return (
    <span className={`vd-plate${small ? ' vd-plate--sm' : ''}`} aria-label={`Number plate ${plate}`}>
      <span className="vd-plate-ind" aria-hidden="true"><i />IND</span>
      <span className="vd-plate-num">{formatPlate(plate)}</span>
    </span>
  );
}

// "Registered in Jhansi, Uttar Pradesh (RTO UP 93)" from the plate's district code
export function RegisteredAt({ plate }) {
  const rto = useRto(plate);
  if (!plate || rto === undefined) return null;
  const code = (plate || '').replace(/[^A-Z0-9]/gi, '').toUpperCase().match(/^([A-Z]{2})(\d{1,2})/);
  if (!rto) {
    return code ? (
      <p className="vd-plate-note">No RTO found for code {code[1]} {code[2]}.</p>
    ) : null;
  }
  return (
    <p className="vd-plate-note">
      Registered in <strong style={{ color: 'var(--vd-ink)' }}>{rto.place}</strong> (RTO {rto.display_code}).
    </p>
  );
}

export function PlateBlock({ plate, confidence }) {
  return (
    <>
      <Plate plate={plate} />
      {plate && <RegisteredAt plate={plate} />}
      <p className="vd-plate-note">
        {plate
          ? `Read with ${pct(confidence)} confidence. Check it against the photo before issuing.`
          : 'A challan needs a readable plate. Try a sharper photo where the plate is facing the camera.'}
      </p>
    </>
  );
}

/* ── Violation tags and status pills ─────────────────────────────────── */

export function ViolationTags({ types = [] }) {
  const unique = [...new Set(types)];
  if (!unique.length) return <span className="vd-plate-none">None</span>;
  return (
    <span className="vd-tags">
      {unique.map((t) => {
        const meta = violationMeta(t);
        return (
          <span key={t} className="vd-tag">
            <i style={{ background: meta.color }} aria-hidden="true" />
            {meta.name}
          </span>
        );
      })}
    </span>
  );
}

export function StatusPill({ status, large }) {
  const meta = challanStatus(status);
  return (
    <span className={`vd-pill${large ? ' vd-pill--lg' : ''}`} data-tone={meta.tone}>
      {meta.label}
    </span>
  );
}

/* ── Confidence with challan thresholds ──────────────────────────────── */

export function ThresholdBar({ confidence, label }) {
  const width = Math.max(0, Math.min(1, confidence || 0)) * 100;
  return (
    <div
      className="vd-bar"
      role="meter"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(width)}
    >
      <span className="vd-bar-fill" style={{ width: `${width}%` }} />
      <span className="vd-bar-tick" style={{ left: `${REVIEW_THRESHOLD * 100}%` }} />
      <span className="vd-bar-tick" style={{ left: `${AUTO_THRESHOLD * 100}%` }} />
    </div>
  );
}

export function Finding({ name, detail, confidence }) {
  const level = thresholdLevel(confidence);
  return (
    <div className="vd-finding">
      <span className="vd-finding-name">
        {name}
        {detail && <small>{detail}</small>}
      </span>
      <span className="vd-finding-pct">{pctExact(confidence)}</span>
      <ThresholdBar confidence={confidence} label={`${name} confidence`} />
      <span className="vd-status" data-level={level}>{THRESHOLD_COPY[level]}</span>
    </div>
  );
}

export function ThresholdLegend() {
  return (
    <p className="vd-legend">
      Tick marks show the challan thresholds. From {pct(REVIEW_THRESHOLD)} a violation goes for review;
      from {pct(AUTO_THRESHOLD)} the challan is generated automatically.
    </p>
  );
}

export function VehicleRecord({ vehicle, showPlate = true }) {
  const findings = toFindings(vehicle.violations);
  const type = vehicleName(vehicle.vehicle_type);
  return (
    <section className="vd-vehicle" aria-label={type}>
      <div className="vd-vehicle-head">
        <span className="vd-vehicle-type">{type}</span>
        <span className="vd-vehicle-count">
          {findings.length ? `${findings.length} ${plural(findings.length, 'violation', 'violations')}` : 'No violations'}
        </span>
      </div>
      {showPlate && <PlateBlock plate={vehicle.license_plate} confidence={vehicle.plate_confidence} />}
      {findings.length > 0 && (
        <div className="vd-findings">
          {findings.map((f) => <Finding key={f.key} {...f} />)}
        </div>
      )}
    </section>
  );
}

/* ── Loading, empty and error states ─────────────────────────────────── */

export function SkeletonRows({ rows = 5, height = 44 }) {
  return (
    <div style={{ display: 'grid', gap: 10, padding: '18px 24px' }} aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <span key={i} className="vd-skeleton" style={{ height, opacity: 1 - i * 0.12 }} />
      ))}
    </div>
  );
}

export function EmptyState({ title, children, action }) {
  return (
    <div className="vd-state">
      <Inbox aria-hidden="true" />
      <h3>{title}</h3>
      {children && <p>{children}</p>}
      {action}
    </div>
  );
}

export function ErrorState({ error, onRetry, title = 'Couldn’t load this' }) {
  return (
    <div className="vd-state" role="alert">
      <AlertTriangle aria-hidden="true" />
      <h3>{title}</h3>
      <p>{errorMessage(error)}</p>
      {onRetry && (
        <button type="button" className="vd-btn" onClick={() => onRetry()}>Try again</button>
      )}
    </div>
  );
}
