import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Download, ImageOff } from 'lucide-react';
import { getAssetUrl, getEvidenceDetails, getEvidenceDownloadUrl } from '../services/api';
import useRequest from '../lib/useRequest';
import { toFindings } from '../lib/findings';
import { vehicleName } from '../lib/violations';
import { countWord, formatDateTime, formatDuration, plural } from '../lib/format';
import {
  ErrorState,
  Finding,
  PageHead,
  PlateBlock,
  SkeletonRows,
  ThresholdLegend,
  VehicleRecord,
  ViolationTags,
} from '../components/desk';
import ChallanAction from '../components/desk/ChallanAction';

function EvidenceStage({ record }) {
  const [view, setView] = useState('annotated');
  const [failed, setFailed] = useState({});
  const id = record.evidence_id;
  const sources = {
    annotated: getAssetUrl(record.annotated_path || `/evidence/${id}/annotated.jpg`),
    original: getAssetUrl(record.image_path || record.original_image_path || `/evidence/${id}/original.jpg`),
  };
  const src = sources[view];

  return (
    <section className="vd-stage" aria-label="Evidence photo">
      <div className="vd-stage-bar">
        <div className="vd-seg" role="group" aria-label="Photo view">
          <button type="button" aria-pressed={view === 'annotated'} onClick={() => setView('annotated')}>Annotated</button>
          <button type="button" aria-pressed={view === 'original'} onClick={() => setView('original')}>Original</button>
        </div>
        {record.camera_id && <span>{record.camera_id}{record.location ? `, ${record.location}` : ''}</span>}
      </div>
      <div className="vd-stage-frame">
        {failed[view] ? (
          <div className="vd-state" style={{ color: 'var(--vd-stage-text)' }}>
            <ImageOff aria-hidden="true" />
            <h3 style={{ color: '#fff' }}>This image isn’t on the server</h3>
            <p>Expected in <code>evidence/{id}/</code>. It may have been deleted.</p>
          </div>
        ) : (
          <img
            src={src}
            alt={view === 'annotated' ? 'Evidence photo with violations marked' : 'Original evidence photo'}
            onError={() => setFailed((f) => ({ ...f, [view]: true }))}
          />
        )}
      </div>
      <div className="vd-stage-meta">
        <span>Recorded <b>{formatDateTime(record.timestamp)}</b></span>
        {Number.isFinite(record.processing_time_ms) && (
          <span>Analysed in <b>{formatDuration(record.processing_time_ms)}</b></span>
        )}
        {record.track_id != null && <span>Video track <b>#{record.track_id}</b></span>}
      </div>
    </section>
  );
}

export default function EvidenceDetails() {
  const { id } = useParams();
  const { data: record, error, loading, reload } = useRequest(() => getEvidenceDetails(id), [id]);

  if (loading && !record) {
    return (
      <div className="vd-page">
        <PageHead title={id} back={{ to: '/evidence', label: 'Evidence' }} />
        <div className="vd-split">
          <div className="vd-panel"><SkeletonRows rows={1} height={420} /></div>
          <div className="vd-panel"><SkeletonRows rows={5} height={24} /></div>
        </div>
      </div>
    );
  }

  if (!record) {
    return (
      <div className="vd-page">
        <PageHead title={id} back={{ to: '/evidence', label: 'Evidence' }} />
        <div className="vd-panel">
          <ErrorState
            error={error}
            onRetry={error?.response?.status === 404 ? undefined : reload}
            title={error?.response?.status === 404 ? 'This evidence record doesn’t exist' : 'Couldn’t load this evidence'}
          />
        </div>
      </div>
    );
  }

  const vehicles = record.vehicles || [];
  const flagged = vehicles.filter((v) => v.violations?.length);
  const scene = record.scene_violations || [];
  const hasDetail = vehicles.length > 0 || scene.length > 0;
  const count = hasDetail
    ? flagged.reduce((n, v) => n + v.violations.length, 0) + scene.length
    : (record.violations || []).length;
  const plate = flagged.find((v) => v.license_plate)?.license_plate || record.plate_number;
  const where = flagged.length === 1
    ? `one ${vehicleName(flagged[0].vehicle_type).toLowerCase()}`
    : flagged.length > 1 ? `${countWord(flagged.length)} vehicles` : null;

  return (
    <div className="vd-page">
      <PageHead
        title={record.evidence_id}
        back={{ to: '/evidence', label: 'Evidence' }}
        lede={`Recorded ${formatDateTime(record.timestamp)}.`}
        actions={
          <a className="vd-btn" href={getEvidenceDownloadUrl(record.evidence_id)}>
            <Download aria-hidden="true" />
            Download evidence (.zip)
          </a>
        }
      />

      <div className="vd-split">
        <EvidenceStage record={record} />

        <aside className="vd-record">
          <div className="vd-verdict" data-tone={count ? 'violation' : 'neutral'}>
            <span className="vd-verdict-n">{count}</span>
            <span className="vd-verdict-text">
              {plural(count, 'violation', 'violations')}
              {where && <><br />on {where}</>}
            </span>
          </div>

          {hasDetail ? (
            <>
              {flagged.length > 0 && <hr className="vd-rule" />}
              {flagged.map((v) => <VehicleRecord key={v.vehicle_id ?? v.track_id} vehicle={v} />)}
              {scene.length > 0 && (
                <>
                  <hr className="vd-rule" />
                  <p className="vd-section-label">Whole scene</p>
                  <div className="vd-findings" style={{ marginTop: 0 }}>
                    {toFindings(scene).map((f) => <Finding key={f.key} {...f} />)}
                  </div>
                </>
              )}
              {count > 0 && <ThresholdLegend />}
            </>
          ) : (
            <>
              <hr className="vd-rule" />
              <PlateBlock plate={record.plate_number} confidence={record.ocr_confidence} />
              <div style={{ marginTop: 16 }}><ViolationTags types={record.violations} /></div>
              <p className="vd-legend">Per-vehicle detail isn’t available for this record, only the summary.</p>
            </>
          )}

          <div className="vd-actions">
            <ChallanAction evidenceId={record.evidence_id} plate={plate} />
          </div>
        </aside>
      </div>
    </div>
  );
}
