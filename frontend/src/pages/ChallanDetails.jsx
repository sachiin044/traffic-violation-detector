import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Download, FileText } from 'lucide-react';
import { getChallanDetails, getChallanPdfUrl, updateChallanStatus } from '../services/api';
import useRequest from '../lib/useRequest';
import { challanStatus, vehicleName, violationName } from '../lib/violations';
import { errorMessage, formatDateTime, inr, plural } from '../lib/format';
import { ErrorState, Finding, PageHead, Plate, RegisteredAt, SkeletonRows, StatusPill, ThresholdLegend } from '../components/desk';

// What an officer can do next from each status
const NEXT_STEPS = {
  REVIEW_REQUIRED: [{ to: 'GENERATED', label: 'Approve challan', done: 'Approved. It is ready to issue.' }],
  PENDING: [{ to: 'GENERATED', label: 'Approve challan', done: 'Approved. It is ready to issue.' }],
  GENERATED: [{ to: 'ISSUED', label: 'Issue notice', done: 'Notice issued.' }],
  ISSUED: [
    { to: 'PAID', label: 'Mark as paid', done: 'Marked as paid.' },
    { to: 'DISPUTED', label: 'Mark as disputed', secondary: true, done: 'Marked as disputed.' },
  ],
  DISPUTED: [{ to: 'PAID', label: 'Mark as paid', done: 'Marked as paid.' }],
  PAID: [],
};

const STATUS_HELP = {
  REVIEW_REQUIRED: 'Confidence was between 70% and 85%, so an officer has to check the evidence before this can be issued.',
  PENDING: 'Waiting for an officer to check the evidence.',
  GENERATED: 'Approved and ready. Issue the notice to send it to the vehicle owner.',
  ISSUED: 'The notice has been issued. Mark it paid once the fine is received.',
  PAID: 'The fine has been paid. Nothing else to do.',
  DISPUTED: 'The owner has disputed this challan. Review the evidence before closing it.',
};

// Load the PDF as a blob so a missing file shows a clear message, not raw JSON
function usePdf(id) {
  const [pdf, setPdf] = useState({ state: 'loading' });
  useEffect(() => {
    let url;
    let cancelled = false;
    setPdf({ state: 'loading' });
    fetch(getChallanPdfUrl(id))
      .then((res) => (res.ok ? res.blob() : Promise.reject(new Error(String(res.status)))))
      .then((blob) => {
        if (cancelled) return;
        url = URL.createObjectURL(blob);
        setPdf({ state: 'ready', url });
      })
      .catch(() => { if (!cancelled) setPdf({ state: 'missing' }); });
    return () => {
      cancelled = true;
      if (url) URL.revokeObjectURL(url);
    };
  }, [id]);
  return pdf;
}

export default function ChallanDetails() {
  const { id } = useParams();
  const { data: challan, error, loading, reload } = useRequest(() => getChallanDetails(id), [id]);
  const [override, setOverride] = useState(null); // status after an update, until the next reload
  const [action, setAction] = useState({ state: 'idle' });
  const pdf = usePdf(id);

  const status = override || challan?.status;

  const changeStatus = async (step) => {
    setAction({ state: 'saving', to: step.to });
    try {
      await updateChallanStatus(id, step.to);
      setOverride(step.to);
      setAction({ state: 'done', message: step.done });
    } catch (err) {
      setAction({ state: 'error', message: errorMessage(err, 'The status could not be changed.') });
    }
  };

  if (loading && !challan) {
    return (
      <div className="vd-page">
        <PageHead title="Challan" back={{ to: '/challans', label: 'Challans' }} />
        <div className="vd-panel"><SkeletonRows rows={6} /></div>
      </div>
    );
  }

  if (!challan) {
    return (
      <div className="vd-page">
        <PageHead title="Challan" back={{ to: '/challans', label: 'Challans' }} />
        <div className="vd-panel">
          <ErrorState
            error={error}
            onRetry={error?.response?.status === 404 ? undefined : reload}
            title={error?.response?.status === 404 ? `Challan ${id} doesn’t exist` : 'Couldn’t load this challan'}
          />
        </div>
      </div>
    );
  }

  const steps = NEXT_STEPS[status] || [];
  // Newer challans list every offence; older ones only have the single violation
  const offences = challan.offences?.length
    ? challan.offences
    : [{ type: challan.violation_type, confidence: challan.confidence, amount: challan.fine_amount }];
  const hasCourt = offences.some((o) => o.court);
  const pdfUrl = getChallanPdfUrl(challan.challan_id);

  return (
    <div className="vd-page">
      <PageHead
        title={challan.challan_id}
        back={{ to: '/challans', label: 'Challans' }}
        badge={<StatusPill status={status} large />}
        actions={
          <>
            <a className="vd-btn" href={pdfUrl} target="_blank" rel="noreferrer">
              <Download aria-hidden="true" />
              Download PDF
            </a>
            {steps.map((step) => (
              <button
                key={step.to}
                type="button"
                className={`vd-btn${step.secondary ? '' : ' vd-btn--primary'}`}
                disabled={action.state === 'saving'}
                onClick={() => changeStatus(step)}
              >
                {action.state === 'saving' && action.to === step.to ? 'Saving…' : step.label}
              </button>
            ))}
          </>
        }
      />

      <div className="vd-split">
        <section className="vd-panel vd-panel--flush" aria-label="Challan notice">
          {pdf.state === 'loading' && <SkeletonRows rows={1} height={520} />}
          {pdf.state === 'ready' && <iframe className="vd-doc" src={pdf.url} title={`Challan notice ${challan.challan_id}`} />}
          {pdf.state === 'missing' && (
            <div className="vd-state">
              <FileText aria-hidden="true" />
              <h3>The PDF notice isn’t on the server</h3>
              <p>
                It should be in <code>inference_outputs/challans/{challan.challan_id}.pdf</code>. It may have been
                deleted, or the backend is running from a different folder.
              </p>
            </div>
          )}
        </section>

        <aside className="vd-record">
          {action.state === 'done' && (
            <div className="vd-callout" data-tone="ok" role="status" style={{ marginBottom: 18 }}>{action.message}</div>
          )}
          {action.state === 'error' && (
            <div className="vd-callout" data-tone="error" role="alert" style={{ marginBottom: 18 }}>{action.message}</div>
          )}

          <div className="vd-amount">{inr(challan.fine_amount)}{hasCourt && '*'}</div>
          <p className="vd-sub">
            Total penalty for {offences.length} {plural(offences.length, 'offence', 'offences')} under the Motor Vehicles Act.
            {hasCourt && ' * Includes a court challan, so the final amount is decided by the court.'}
          </p>

          <hr className="vd-rule" />
          <Plate plate={challan.plate_number} />
          <p className="vd-plate-note">{vehicleName(challan.vehicle_type)}</p>
          {challan.registered_at ? (
            <p className="vd-plate-note">
              Registered in <strong style={{ color: 'var(--vd-ink)' }}>{challan.registered_at}</strong>.
            </p>
          ) : (
            <RegisteredAt plate={challan.plate_number} />
          )}

          <div className="vd-findings">
            {offences.map((o) => (
              <div key={o.type}>
                <Finding
                  name={violationName(o.type)}
                  detail={o.section ? `Sec. ${o.section}` : ''}
                  confidence={o.confidence}
                />
                {Number.isFinite(Number(o.amount)) && (
                  <p className="vd-legend" style={{ marginTop: 0, marginBottom: 6 }}>
                    Penalty {inr(o.amount)}{o.court ? ' minimum, court decides' : ''}
                    {o.note && !o.court ? `. ${o.note}.` : ''}
                  </p>
                )}
              </div>
            ))}
          </div>
          <ThresholdLegend />

          <hr className="vd-rule" />
          <p className="vd-sub" style={{ marginTop: 0 }}>
            <strong style={{ color: 'var(--vd-ink)' }}>{challanStatus(status).label}.</strong> {STATUS_HELP[status]}
          </p>

          <dl className="vd-kv" style={{ marginTop: 14 }}>
            <dt>Violation recorded</dt>
            <dd>{formatDateTime(challan.timestamp)}</dd>
            <dt>Challan created</dt>
            <dd>{formatDateTime(challan.created_at)}</dd>
            {challan.location && (
              <>
                <dt>Place of offence</dt>
                <dd>{challan.location}{challan.camera_id ? `, ${challan.camera_id}` : ''}</dd>
              </>
            )}
            <dt>Evidence</dt>
            <dd><Link className="vd-link" to={`/evidence/${challan.evidence_id}`}>{challan.evidence_id}</Link></dd>
          </dl>
        </aside>
      </div>
    </div>
  );
}
