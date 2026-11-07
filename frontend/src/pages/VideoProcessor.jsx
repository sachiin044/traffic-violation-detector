import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Video } from 'lucide-react';
import { getAssetUrl, getVideoResult, getVideoStatus, processVideo } from '../services/api';
import { vehicleName } from '../lib/violations';
import { errorMessage, formatBytes, formatNumber, plural } from '../lib/format';
import { PageHead, Plate, ViolationTags } from '../components/desk';

const ACCEPT = 'video/mp4,video/x-msvideo,video/avi,video/quicktime,.mp4,.avi,.mov';
const POLL_MS = 2000;
const TASK_KEY = 'vd-video-task';

// Cameras seeded by database/seed_cameras.py
const CAMERAS = [
  { id: 'CAM_001', name: 'Main Junction North' },
  { id: 'CAM_002', name: 'Highway A Exit' },
];

const storage = {
  get: () => { try { return sessionStorage.getItem(TASK_KEY); } catch { return null; } },
  set: (v) => { try { sessionStorage.setItem(TASK_KEY, v); } catch { /* storage unavailable */ } },
  clear: () => { try { sessionStorage.removeItem(TASK_KEY); } catch { /* storage unavailable */ } },
};

export default function VideoProcessor() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [camera, setCamera] = useState(CAMERAS[0].id);
  const [taskId, setTaskId] = useState(() => storage.get());
  const [status, setStatus] = useState(() => (storage.get() ? 'processing' : 'empty'));
  const [upload, setUpload] = useState(0);
  const [progress, setProgress] = useState(0);
  const [found, setFound] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [view, setView] = useState('processed');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const acceptFile = useCallback((f) => {
    if (!f) return;
    const okType = /\.(mp4|avi|mov)$/i.test(f.name) || f.type.startsWith('video/');
    if (!okType) {
      setError('That file isn’t a supported video. Use MP4, AVI or MOV.');
      return;
    }
    storage.clear();
    setFile(f);
    setPreview(URL.createObjectURL(f));
    setTaskId(null);
    setResult(null);
    setError('');
    setProgress(0);
    setFound(0);
    setView('processed');
    setStatus('ready');
  }, []);

  const start = async () => {
    if (!file) return;
    setStatus('uploading');
    setUpload(0);
    setError('');
    try {
      const data = await processVideo(file, camera, (e) => {
        if (e.total) setUpload(Math.round((e.loaded / e.total) * 100));
      });
      storage.set(data.task_id);
      setTaskId(data.task_id);
      setStatus('processing');
    } catch (err) {
      setError(errorMessage(err, 'The video could not be uploaded.'));
      setStatus('error');
    }
  };

  // Poll the background task until it finishes
  useEffect(() => {
    if (status !== 'processing' || !taskId) return undefined;
    let stopped = false;
    const poll = async () => {
      try {
        const task = await getVideoStatus(taskId);
        if (stopped) return;
        setProgress(task.progress || 0);
        setFound(task.violations_found || 0);
        if (task.status === 'completed') {
          const res = await getVideoResult(taskId);
          if (stopped) return;
          storage.clear();
          setResult(res);
          setStatus('done');
        } else if (task.status === 'error') {
          storage.clear();
          setError(task.error ? `Processing failed: ${task.error}` : 'Processing failed. Check the backend log for details.');
          setStatus('error');
        }
      } catch (err) {
        if (stopped) return;
        if (err?.response?.status === 404) {
          storage.clear();
          setTaskId(null);
          setError('That processing job no longer exists. Upload the video again.');
          setStatus(file ? 'ready' : 'empty');
        }
        // Network blips: keep polling
      }
    };
    poll();
    const timer = setInterval(poll, POLL_MS);
    return () => { stopped = true; clearInterval(timer); };
  }, [status, taskId, file]);

  const drop = {
    onDragOver: (e) => { e.preventDefault(); if (status !== 'uploading' && status !== 'processing') setDragging(true); },
    onDragLeave: () => setDragging(false),
    onDrop: (e) => {
      e.preventDefault();
      setDragging(false);
      if (status === 'uploading' || status === 'processing') return;
      acceptFile(e.dataTransfer.files?.[0]);
    },
  };

  const busy = status === 'uploading' || status === 'processing';
  const processedSrc = getAssetUrl(result?.processed_video);
  const violators = result?.violation_details || [];
  const showProcessed = status === 'done' && processedSrc && view === 'processed';
  const stageSrc = showProcessed ? processedSrc : preview;

  return (
    <div className="vd-page">
      <PageHead
        title="Check a video"
        lede="Upload camera footage. Each vehicle is tracked across frames, so wrong-side driving and red-light jumps can be caught too."
        actions={file && (
          <button type="button" className="vd-btn" onClick={() => inputRef.current?.click()} disabled={busy}>
            Upload another video
          </button>
        )}
      />
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT}
        className="vd-sr"
        tabIndex={-1}
        aria-hidden="true"
        onChange={(e) => { acceptFile(e.target.files?.[0]); e.target.value = ''; }}
      />

      <div className="vd-split">
        <section className={`vd-stage${dragging && stageSrc ? ' is-over' : ''}`} aria-label="Video" {...drop}>
          {!stageSrc ? (
            status === 'processing' ? (
              <div className="vd-drop" style={{ cursor: 'default' }}>
                <span className="vd-drop-glyph" aria-hidden="true"><Video /></span>
                <span className="vd-drop-title">A video is being processed</span>
                <p>This job was started earlier. Results appear here when it finishes.</p>
              </div>
            ) : (
              <label className={`vd-drop${dragging ? ' is-over' : ''}`}>
                <span className="vd-drop-glyph" aria-hidden="true"><Video /></span>
                <span className="vd-drop-title">Drop a traffic video here</span>
                <p>Or choose one from your computer. MP4, AVI or MOV. Longer videos take longer to check.</p>
                <span className="vd-btn vd-btn--primary">Choose a video</span>
                <input type="file" accept={ACCEPT} className="vd-sr" onChange={(e) => acceptFile(e.target.files?.[0])} />
              </label>
            )
          ) : (
            <>
              <div className="vd-stage-bar">
                {status === 'done' && processedSrc ? (
                  <div className="vd-seg" role="group" aria-label="Video view">
                    <button type="button" aria-pressed={view === 'processed'} onClick={() => setView('processed')}>Tracked</button>
                    <button type="button" aria-pressed={view === 'original'} onClick={() => setView('original')} disabled={!preview}>Original</button>
                  </div>
                ) : (
                  <span>{busy ? 'Original video, processing in the background' : 'Original video'}</span>
                )}
                {file && <span>{formatBytes(file.size)}</span>}
              </div>
              <video key={stageSrc} src={stageSrc} controls playsInline preload="metadata" />
            </>
          )}
        </section>

        <aside className="vd-record" aria-live="polite">
          {status === 'empty' && (
            <>
              <h2 className="vd-heading">How video checks work</h2>
              <p className="vd-sub">
                Every vehicle gets a track number and is followed frame by frame. Helmets, riders and seatbelts are
                checked every fifth frame. A vehicle is flagged once, the first time a violation is found.
              </p>
              <p className="vd-sub">
                Wrong-side and red-light checks need a camera that has been set up with its stop line and traffic
                direction.
              </p>
              {error && <div className="vd-callout" data-tone="error" style={{ marginTop: 16 }}>{error}</div>}
            </>
          )}

          {(status === 'ready' || (status === 'error' && file)) && (
            <>
              <h2 className="vd-heading">Ready to check</h2>
              <div className="vd-file"><b title={file.name}>{file.name}</b><span>{formatBytes(file.size)}</span></div>
              <label className="vd-field" style={{ marginTop: 18 }}>
                Camera
                <select className="vd-select" value={camera} onChange={(e) => setCamera(e.target.value)}>
                  {CAMERAS.map((c) => <option key={c.id} value={c.id}>{c.id}, {c.name}</option>)}
                </select>
              </label>
              <p className="vd-legend">
                The camera decides the stop line and allowed direction. If it hasn’t been set up, those two checks are skipped.
              </p>
              {error && <div className="vd-callout" data-tone="error" style={{ marginTop: 14 }}>{error}</div>}
              <div className="vd-actions">
                <button type="button" className="vd-btn vd-btn--primary vd-btn--block" onClick={start}>
                  {status === 'error' ? 'Try again' : 'Check video'}
                </button>
              </div>
            </>
          )}

          {status === 'error' && !file && (
            <>
              <h2 className="vd-heading">Processing stopped</h2>
              <div className="vd-callout" data-tone="error" style={{ marginTop: 14 }}>{error}</div>
              <div className="vd-actions">
                <button type="button" className="vd-btn vd-btn--block" onClick={() => inputRef.current?.click()}>Upload a video</button>
              </div>
            </>
          )}

          {status === 'uploading' && (
            <>
              <h2 className="vd-heading">Uploading</h2>
              <div className="vd-progress" role="progressbar" aria-valuenow={upload} aria-valuemin={0} aria-valuemax={100}>
                <span style={{ width: `${upload}%` }} />
              </div>
              <div className="vd-progress-row"><span>Sending the video to the server</span><b>{upload}%</b></div>
            </>
          )}

          {status === 'processing' && (
            <>
              <h2 className="vd-heading">Checking the video</h2>
              <div className="vd-progress" role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
                <span style={{ width: `${progress}%` }} />
              </div>
              <div className="vd-progress-row">
                <span>{formatNumber(found)} {plural(found, 'violation', 'violations')} so far</span>
                <b>{progress}%</b>
              </div>
              <p className="vd-sub">You can leave this page. The job keeps running and this page picks it up again when you come back.</p>
            </>
          )}

          {status === 'done' && result && (
            <>
              <div className="vd-verdict" data-tone={result.violations ? 'violation' : 'clear'}>
                <span className="vd-verdict-n">{result.violations || 0}</span>
                <span className="vd-verdict-text">
                  {plural(result.violations || 0, 'violation', 'violations')}
                  {violators.length > 0 && <><br />on {violators.length} {plural(violators.length, 'vehicle', 'vehicles')}</>}
                </span>
              </div>
              <p className="vd-sub">
                {violators.length
                  ? 'Each flagged vehicle was saved as its own evidence record.'
                  : 'No tracked vehicle broke a rule in this video.'}
                {!processedSrc && ' The tracked video file wasn’t saved, so only the original is shown.'}
              </p>

              {violators.length > 0 && (
                <>
                  <hr className="vd-rule" />
                  {violators.map((v) => (
                    <div className="vd-violator" key={`${v.track_id}-${v.evidence_id}`}>
                      <div className="vd-violator-head">
                        <span>{vehicleName(v.vehicle_type)}, track #{v.track_id}</span>
                        <Plate plate={v.license_plate} size="sm" />
                      </div>
                      <ViolationTags types={v.violations} />
                      {v.evidence_id && (
                        <span className="vd-violator-foot">
                          <Link className="vd-link" to={`/evidence/${v.evidence_id}`}>Open evidence {v.evidence_id}</Link>
                        </span>
                      )}
                    </div>
                  ))}
                </>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
