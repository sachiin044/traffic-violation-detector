import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Bike,
  Camera,
  Car,
  ImageUp,
  ParkingCircle,
  ScanLine,
  TrafficCone,
  Users,
} from 'lucide-react';
import {
  getAssetUrl,
  getChallans,
  getEvidenceDownloadUrl,
  manualGenerateChallan,
  processImage,
} from '../services/api';
import { Finding, ThresholdLegend, VehicleRecord } from '../components/desk';
import { toFindings } from '../lib/findings';
import {
  countWord,
  errorMessage,
  formatBytes,
  formatDuration,
  formatTime,
  plural,
} from '../lib/format';
import { vehicleName } from '../lib/violations';

const MAX_UPLOAD_MB = 20;
const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

const CHECKS = [
  { icon: Bike, name: 'Helmets', text: 'Every rider on a two-wheeler, including pillion riders.' },
  { icon: Users, name: 'Triple riding', text: 'More than two people on one bike or scooter.' },
  { icon: Car, name: 'Seatbelts', text: 'Drivers of cars, buses and trucks.' },
  { icon: TrafficCone, name: 'Red light', text: 'Vehicles over the stop line while the signal is red.' },
  { icon: ParkingCircle, name: 'Illegal parking', text: 'Checked across the whole scene.' },
  { icon: ScanLine, name: 'Number plate', text: 'Read for each vehicle. A challan needs a readable plate.' },
];

const getErrorMessage = (err) => errorMessage(err, 'The photo could not be checked.');

// ── Page ──────────────────────────────────────────────────────────────

export default function ImageProcessor() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [dimensions, setDimensions] = useState(null);
  const [status, setStatus] = useState('empty'); // empty | ready | checking | done | error
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [view, setView] = useState('annotated');
  const [annotatedFailed, setAnnotatedFailed] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [challan, setChallan] = useState({ state: 'idle' }); // idle | checking | exists | creating | created | error
  const inputRef = useRef(null);
  const dragDepth = useRef(0);

  // Free the object URL when the preview changes
  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const acceptFile = useCallback((selected) => {
    if (!selected) return;
    if (!ACCEPTED_TYPES.includes(selected.type)) {
      setError('That file type is not supported. Use a JPEG, PNG or WebP photo.');
      setStatus(file ? 'ready' : 'error');
      return;
    }
    if (selected.size > MAX_UPLOAD_MB * 1024 * 1024) {
      setError(`That photo is ${formatBytes(selected.size)}. The limit is ${MAX_UPLOAD_MB} MB.`);
      setStatus(file ? 'ready' : 'error');
      return;
    }
    setFile(selected);
    setPreview(URL.createObjectURL(selected));
    setDimensions(null);
    setResult(null);
    setError('');
    setView('annotated');
    setAnnotatedFailed(false);
    setChallan({ state: 'idle' });
    setStatus('ready');
  }, [file]);

  const openPicker = () => inputRef.current?.click();

  const onInputChange = (e) => {
    acceptFile(e.target.files?.[0]);
    e.target.value = '';
  };

  const checkPhoto = async () => {
    if (!file || status === 'checking') return;
    setStatus('checking');
    setError('');
    try {
      const data = await processImage(file);
      setResult(data);
      setView('annotated');
      setAnnotatedFailed(false);
      setStatus('done');
    } catch (err) {
      setError(getErrorMessage(err));
      setStatus('error');
    }
  };

  // Drag and drop anywhere on the stage
  const dropHandlers = {
    onDragEnter: (e) => {
      e.preventDefault();
      if (status === 'checking') return;
      dragDepth.current += 1;
      setDragging(true);
    },
    onDragOver: (e) => e.preventDefault(),
    onDragLeave: () => {
      dragDepth.current = Math.max(0, dragDepth.current - 1);
      if (dragDepth.current === 0) setDragging(false);
    },
    onDrop: (e) => {
      e.preventDefault();
      dragDepth.current = 0;
      setDragging(false);
      if (status === 'checking') return;
      acceptFile(e.dataTransfer.files?.[0]);
    },
  };

  // ── Derived result data ──
  const vehicles = useMemo(() => result?.vehicles || [], [result]);
  const sceneViolations = result?.scene_violations || [];
  const violationTotal = result?.total_violations
    ?? vehicles.reduce((n, v) => n + (v.violations?.length || 0), 0) + sceneViolations.length;
  const flaggedVehicles = vehicles.filter((v) => v.violations?.length);
  const evidenceId = result?.evidence_id;
  const annotatedSrc = getAssetUrl(result?.annotated_image_path);
  const canShowAnnotated = Boolean(annotatedSrc && !annotatedFailed);
  const showingAnnotated = status === 'done' && view === 'annotated' && canShowAnnotated;
  const plateVehicle = flaggedVehicles.find((v) => v.license_plate);

  // Was a challan already created automatically for this evidence?
  useEffect(() => {
    if (!evidenceId || !plateVehicle) return undefined;
    let cancelled = false;
    setChallan({ state: 'checking' });
    getChallans({ plate_number: plateVehicle.license_plate, limit: 50 })
      .then((data) => {
        if (cancelled) return;
        const match = (data?.records || []).find((c) => c.evidence_id === evidenceId);
        setChallan(match ? { state: 'exists', id: match.challan_id, status: match.status } : { state: 'idle' });
      })
      .catch(() => { if (!cancelled) setChallan({ state: 'idle' }); });
    return () => { cancelled = true; };
  }, [evidenceId, plateVehicle]);

  const generateChallan = async () => {
    if (!evidenceId) return;
    setChallan({ state: 'creating' });
    try {
      const data = await manualGenerateChallan(evidenceId);
      setChallan({ state: 'created', id: data.challan_id });
    } catch (err) {
      setChallan({ state: 'error', message: getErrorMessage(err) });
    }
  };

  // ── Verdict copy ──
  let verdict = null;
  if (status === 'done') {
    if (vehicles.length === 0 && violationTotal === 0) {
      verdict = {
        tone: 'neutral',
        n: '0',
        text: <>vehicles<br />found</>,
        sub: 'Nothing on the road was recognised as a vehicle, so no checks ran. Try a photo where vehicles are clearly visible.',
      };
    } else if (violationTotal === 0) {
      verdict = {
        tone: 'clear',
        n: '0',
        text: <>violations<br />found</>,
        sub: `${vehicles.length} ${plural(vehicles.length, 'vehicle was', 'vehicles were')} checked. Nothing was saved as evidence.`,
      };
    } else {
      const vehicleText = flaggedVehicles.length === 1
        ? `one ${vehicleName(flaggedVehicles[0].vehicle_type).toLowerCase()}`
        : `${countWord(flaggedVehicles.length)} vehicles`;
      const where = flaggedVehicles.length ? <>on {vehicleText}</> : <>in the scene</>;
      verdict = {
        tone: 'violation',
        n: String(violationTotal),
        text: <>{plural(violationTotal, 'violation', 'violations')}<br />{where}</>,
        sub: plateVehicle
          ? 'The plate was read, so this can become a challan.'
          : 'No plate could be read, so a challan can’t be created from this photo yet.',
      };
    }
  }

  const stageImage = showingAnnotated ? annotatedSrc : preview;

  return (
    <div className="vd-page">
      <header className="vd-page-head">
        <div>
          <h1 className="vd-title">Check a photo</h1>
          <p className="vd-lede">
            Upload a road photo. Any violations are saved as evidence you can turn into a challan.
          </p>
        </div>
        {file && (
          <button type="button" className="vd-btn" onClick={openPicker} disabled={status === 'checking'}>
            <ImageUp aria-hidden="true" />
            Upload another photo
          </button>
        )}
      </header>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_TYPES.join(',')}
        onChange={onInputChange}
        className="vd-sr"
        tabIndex={-1}
        aria-hidden="true"
      />

      <div className="vd-split">
        {/* ── Stage ── */}
        <section
          className={`vd-stage${dragging && preview ? ' is-over' : ''}`}
          aria-label="Photo"
          {...dropHandlers}
        >
          {!preview ? (
            <label className={`vd-drop${dragging ? ' is-over' : ''}`}>
              <span className="vd-drop-glyph" aria-hidden="true"><Camera /></span>
              <span className="vd-drop-title">Drop a road photo here</span>
              <p>Or choose one from your computer. JPEG, PNG or WebP, up to {MAX_UPLOAD_MB} MB.</p>
              <span className="vd-btn vd-btn--primary">Choose a photo</span>
              <input
                type="file"
                accept={ACCEPTED_TYPES.join(',')}
                onChange={onInputChange}
                className="vd-sr"
              />
            </label>
          ) : (
            <>
              <div className="vd-stage-bar">
                {status === 'done' && canShowAnnotated ? (
                  <div className="vd-seg" role="group" aria-label="Photo view">
                    <button type="button" aria-pressed={view === 'annotated'} onClick={() => setView('annotated')}>
                      Annotated
                    </button>
                    <button type="button" aria-pressed={view === 'original'} onClick={() => setView('original')}>
                      Original
                    </button>
                  </div>
                ) : (
                  <span>{status === 'checking' ? 'Checking for vehicles, riders and plates' : 'Original photo'}</span>
                )}
                <span>
                  {result?.image_width
                    ? `${result.image_width} × ${result.image_height} px`
                    : dimensions && `${dimensions.w} × ${dimensions.h} px`}
                </span>
              </div>

              <div className="vd-stage-frame">
                <span className="vd-stage-media">
                  <img
                    src={stageImage}
                    alt={showingAnnotated ? 'Photo with detected vehicles and violations marked' : 'Uploaded road photo'}
                    onLoad={(e) => {
                      if (!showingAnnotated) setDimensions({ w: e.target.naturalWidth, h: e.target.naturalHeight });
                    }}
                    onError={() => { if (showingAnnotated) setAnnotatedFailed(true); }}
                  />
                  {status === 'checking' && <span className="vd-scan" aria-hidden="true" />}
                </span>
              </div>

              {status === 'done' && (
                <div className="vd-stage-meta">
                  {evidenceId && <span>Evidence <b>{evidenceId}</b></span>}
                  {evidenceId && <span>Saved <b>{formatTime(result.timestamp)}</b></span>}
                  <span>Analysed in <b>{formatDuration(result.processing_time_ms)}</b></span>
                  {!evidenceId && <span>Not saved, since nothing was flagged</span>}
                </div>
              )}
            </>
          )}
        </section>

        {/* ── Record panel ── */}
        <aside className="vd-record" aria-live="polite">
          {status === 'empty' && (
            <>
              <h2 className="vd-heading">What gets checked</h2>
              <p className="vd-sub">Each vehicle in the photo goes through the checks that apply to it.</p>
              <ul className="vd-checks">
                {CHECKS.map(({ icon: Icon, name, text }) => (
                  <li key={name}>
                    <Icon aria-hidden="true" />
                    <b>{name}</b>
                    <span>{text}</span>
                  </li>
                ))}
              </ul>
            </>
          )}

          {(status === 'ready' || (status === 'error' && file)) && (
            <>
              <h2 className="vd-heading">Ready to check</h2>
              <div className="vd-file">
                <b title={file.name}>{file.name}</b>
                <span>{formatBytes(file.size)}</span>
              </div>
              <p className="vd-sub">
                The check usually takes 5 to 15 seconds. If anything is flagged, the photo is saved as evidence.
              </p>
              {error && <div className="vd-callout" data-tone="error" style={{ marginTop: 16 }}>{error}</div>}
              <div className="vd-actions">
                <button type="button" className="vd-btn vd-btn--primary vd-btn--block" onClick={checkPhoto}>
                  {status === 'error' ? 'Try again' : 'Check photo'}
                </button>
                <button type="button" className="vd-btn vd-btn--block" onClick={openPicker}>
                  Choose a different photo
                </button>
              </div>
            </>
          )}

          {status === 'error' && !file && (
            <div className="vd-callout" data-tone="error">{error}</div>
          )}

          {status === 'checking' && (
            <>
              <h2 className="vd-heading">Checking the photo</h2>
              <p className="vd-sub">
                Finding vehicles first, then checking helmets, riders, seatbelts and signals for each one,
                and reading number plates. This usually takes 5 to 15 seconds.
              </p>
            </>
          )}

          {status === 'done' && verdict && (
            <>
              <div className="vd-verdict" data-tone={verdict.tone}>
                <span className="vd-verdict-n">{verdict.n}</span>
                <span className="vd-verdict-text">{verdict.text}</span>
              </div>
              <p className="vd-sub">{verdict.sub}</p>

              {flaggedVehicles.length > 0 && <hr className="vd-rule" />}
              {flaggedVehicles.map((vehicle) => (
                <VehicleRecord key={vehicle.vehicle_id} vehicle={vehicle} showPlate />
              ))}

              {sceneViolations.length > 0 && (
                <>
                  <hr className="vd-rule" />
                  <p className="vd-section-label">Whole scene</p>
                  <div className="vd-findings" style={{ marginTop: 0 }}>
                    {toFindings(sceneViolations).map((f) => <Finding key={f.key} {...f} />)}
                  </div>
                </>
              )}

              {violationTotal > 0 && <ThresholdLegend />}

              {vehicles.length > flaggedVehicles.length && violationTotal > 0 && (
                <p className="vd-legend" style={{ marginTop: 6 }}>
                  {vehicles.length - flaggedVehicles.length} other{' '}
                  {plural(vehicles.length - flaggedVehicles.length, 'vehicle', 'vehicles')} had no violations.
                </p>
              )}

              {evidenceId && (
                <div className="vd-actions">
                  {challan.state === 'exists' || challan.state === 'created' ? (
                    <div className="vd-callout" data-tone="ok">
                      {challan.state === 'exists' ? 'A challan was created automatically: ' : 'Challan created: '}
                      <Link className="vd-link" to={`/challan/${challan.id}`}>{challan.id}</Link>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="vd-btn vd-btn--primary vd-btn--block"
                      onClick={generateChallan}
                      disabled={!plateVehicle || challan.state === 'creating' || challan.state === 'checking'}
                      title={plateVehicle ? undefined : 'A readable plate is needed to create a challan'}
                    >
                      {challan.state === 'creating' ? 'Creating challan…' : 'Generate challan'}
                    </button>
                  )}
                  {challan.state === 'error' && (
                    <div className="vd-callout" data-tone="error">{challan.message}</div>
                  )}
                  <a className="vd-btn vd-btn--block" href={getEvidenceDownloadUrl(evidenceId)}>
                    Download evidence (.zip)
                  </a>
                  <Link className="vd-btn vd-btn--block" to={`/evidence/${evidenceId}`}>
                    Open evidence record
                  </Link>
                </div>
              )}

              {!evidenceId && (
                <div className="vd-actions">
                  <button type="button" className="vd-btn vd-btn--block" onClick={openPicker}>
                    Check another photo
                  </button>
                </div>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
