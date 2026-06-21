import React, { useState } from 'react';
import {
  AlertCircle,
  Camera,
  CheckCircle2,
  Clock3,
  FileText,
  Gauge,
  Image as ImageIcon,
  ShieldAlert,
  UploadCloud,
} from 'lucide-react';
import { processImage } from '../services/api';
import ViolationBadge from '../components/ViolationBadge';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const getErrorMessage = (err) => (
  err?.response?.data?.detail
  || err?.message
  || 'Unable to analyze the image. Please try again.'
);

const assetUrl = (path) => {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${API_URL}${path}`;
};

const formatMs = (ms) => {
  if (!Number.isFinite(ms)) return 'N/A';
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${Math.round(ms)}ms`;
};

const formatConfidence = (value) => (
  Number.isFinite(value) ? `${(value * 100).toFixed(1)}%` : 'N/A'
);

const normalizeResult = (data) => {
  const vehicles = data?.vehicles || data?.violations || [];
  const annotatedImage = data?.annotated_image_path
    || data?.annotated_image
    || (data?.evidence_id ? `/evidence/${data.evidence_id}/annotated.jpg` : null);

  return {
    ...data,
    vehicles,
    vehicleCount: data?.total_vehicles ?? data?.vehicles_detected ?? vehicles.length,
    violationCount: data?.total_violations ?? vehicles.reduce((count, vehicle) => count + (vehicle.violations?.length || 0), 0),
    annotatedImage,
    sceneViolations: data?.scene_violations || [],
  };
};

function MetricTile({ icon: Icon, label, value, tone = 'primary' }) {
  const toneClass = {
    primary: 'text-primary bg-primary/10 border-primary/20',
    danger: 'text-danger bg-danger/10 border-danger/20',
    success: 'text-success bg-success/10 border-success/20',
    warning: 'text-warning bg-warning/10 border-warning/20',
  }[tone];

  return (
    <div className="bg-dark-900 border border-dark-700 rounded-lg p-4">
      <div className={`w-9 h-9 rounded-lg border flex items-center justify-center mb-3 ${toneClass}`}>
        <Icon className="w-5 h-5" />
      </div>
      <p className="text-2xl font-bold text-white leading-none">{value}</p>
      <p className="text-xs uppercase tracking-wider text-slate-400 mt-2">{label}</p>
    </div>
  );
}

function ImageReviewFrame({ title, src, alt, onError }) {
  return (
    <div className="bg-dark-900 border border-dark-700 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-700 flex items-center justify-between">
        <p className="text-sm font-semibold text-white">{title}</p>
        <span className="text-[11px] uppercase tracking-wider text-slate-500">Full Frame</span>
      </div>
      <div className="h-[360px] bg-slate-950 flex items-center justify-center p-3">
        <img
          src={src}
          alt={alt}
          className="max-w-full max-h-full object-contain rounded border border-dark-700/70"
          onError={onError}
        />
      </div>
    </div>
  );
}

export default function ImageProcessor() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [status, setStatus] = useState('idle');
  const [result, setResult] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [annotatedImageError, setAnnotatedImageError] = useState(false);

  const handleFileChange = (e) => {
    const selected = e.target.files[0];
    if (selected) {
      setFile(selected);
      setPreview(URL.createObjectURL(selected));
      setStatus('idle');
      setResult(null);
      setErrorMessage('');
      setAnnotatedImageError(false);
    }
  };

  const resetUpload = () => {
    setFile(null);
    setPreview(null);
    setResult(null);
    setErrorMessage('');
    setAnnotatedImageError(false);
    setStatus('idle');
  };

  const handleUpload = async (e) => {
    e?.preventDefault();
    if (!file) return;
    setStatus('processing');
    setErrorMessage('');
    setAnnotatedImageError(false);

    try {
      const data = await processImage(file);
      setResult(normalizeResult(data));
      setStatus('completed');
    } catch (err) {
      console.error(err);
      setErrorMessage(getErrorMessage(err));
      setStatus('error');
    }
  };

  const hasViolations = Boolean(
    result?.vehicles?.some(vehicle => vehicle.violations?.length > 0)
    || result?.sceneViolations?.length > 0
  );
  const annotatedSrc = assetUrl(result?.annotatedImage);

  return (
    <div className="p-8 h-full flex flex-col overflow-y-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Image Processing</h1>
        <p className="text-slate-400">Upload single traffic images for instant AI violation detection</p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[400px_1fr] gap-8 items-start">
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm xl:sticky xl:top-8">
          <h2 className="text-xl font-bold text-white mb-2">Upload Traffic Photo</h2>
          <p className="text-sm text-slate-400 mb-6">
            Supports JPEG, PNG, and WebP. The AI will analyze vehicles, plates, and violations.
          </p>

          {preview ? (
            <div className="relative w-full h-[260px] mb-5 rounded-lg overflow-hidden border border-dark-600 bg-slate-950 flex items-center justify-center p-2">
              <img src={preview} alt="Upload preview" className="max-w-full max-h-full object-contain rounded" />
              <button
                type="button"
                onClick={resetUpload}
                className="absolute top-2 right-2 bg-dark-900/80 text-white w-8 h-8 rounded-full hover:bg-danger transition-colors"
                aria-label="Remove selected image"
              >
                &times;
              </button>
            </div>
          ) : (
            <label className="min-h-56 mb-5 border border-dashed border-dark-600 rounded-lg flex flex-col items-center justify-center text-center cursor-pointer hover:border-primary/70 hover:bg-primary/5 transition-colors">
              <UploadCloud className="w-12 h-12 text-primary mb-3" />
              <span className="text-white font-semibold">Choose image</span>
              <span className="text-sm text-slate-500 mt-1">JPEG, PNG, WebP</span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileChange}
                className="sr-only"
                disabled={status === 'processing'}
              />
            </label>
          )}

          <button
            type="button"
            onClick={handleUpload}
            disabled={!file || status === 'processing'}
            className="w-full bg-primary hover:bg-blue-600 text-white px-5 py-3 rounded-lg font-medium shadow-lg transition-colors disabled:opacity-50 flex items-center justify-center"
          >
            {status === 'processing' ? (
              <>Processing AI Models...</>
            ) : (
              <><Camera className="w-5 h-5 mr-2" /> Detect Violations</>
            )}
          </button>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm min-h-[640px]">
          <div className="flex items-center justify-between gap-4 mb-6">
            <div>
              <h2 className="text-xl font-bold text-white">Analysis Results</h2>
              <p className="text-sm text-slate-400 mt-1">Evidence package, detections, and vehicle-level details</p>
            </div>
            {result?.evidence_id && (
              <div className="text-right">
                <p className="text-xs uppercase tracking-wider text-slate-500">Evidence ID</p>
                <p className="font-mono text-sm text-white">{result.evidence_id}</p>
              </div>
            )}
          </div>

          {status === 'idle' || !status ? (
            <div className="min-h-[520px] flex flex-col items-center justify-center text-slate-500">
              <ImageIcon className="w-12 h-12 mb-4 opacity-50" />
              <p>No active scan. Upload an image to begin.</p>
            </div>
          ) : status === 'processing' ? (
            <div className="min-h-[520px] flex flex-col items-center justify-center">
              <div className="w-16 h-16 border-4 border-primary border-t-transparent rounded-full animate-spin mb-4"></div>
              <p className="text-primary font-medium">Running YOLOv11 & OCR Models...</p>
            </div>
          ) : status === 'error' ? (
            <div className="flex items-center text-danger bg-danger/10 p-4 rounded-lg border border-danger/20">
              <AlertCircle className="w-6 h-6 mr-3" />
              <p className="text-sm">{errorMessage}</p>
            </div>
          ) : status === 'completed' && result ? (
            <div className="space-y-6">
              <div className="bg-success/10 border border-success/20 rounded-lg p-4 flex items-center">
                <CheckCircle2 className="w-8 h-8 text-success mr-4 shrink-0" />
                <div>
                  <h3 className="text-white font-bold">Analysis Complete</h3>
                  <p className="text-slate-300 text-sm">
                    Found {result.vehicleCount} vehicles and {result.violationCount} violations.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricTile icon={Camera} label="Vehicles" value={result.vehicleCount} />
                <MetricTile icon={ShieldAlert} label="Violations" value={result.violationCount} tone={result.violationCount > 0 ? 'danger' : 'success'} />
                <MetricTile icon={Clock3} label="Processing" value={formatMs(result.processing_time_ms)} tone="warning" />
                <MetricTile icon={FileText} label="Evidence" value={result.evidence_id ? 'Saved' : 'N/A'} tone={result.evidence_id ? 'success' : 'primary'} />
              </div>

              <div>
                <div className="flex items-end justify-between gap-4 mb-3">
                  <div>
                    <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Evidence Images</h4>
                    <p className="text-xs text-slate-500 mt-1">Images are contained to show the full frame without cropping.</p>
                  </div>
                </div>
                {annotatedSrc && !annotatedImageError ? (
                  <div className="grid grid-cols-1 2xl:grid-cols-2 gap-4">
                    {preview && (
                      <ImageReviewFrame title="Original Upload" src={preview} alt="Original upload" />
                    )}
                    <ImageReviewFrame
                      title="AI Annotated Evidence"
                      src={annotatedSrc}
                      alt="Annotated result"
                      onError={() => setAnnotatedImageError(true)}
                    />
                  </div>
                ) : (
                  <div className="p-5 bg-dark-900 border border-dark-700 rounded-lg text-slate-400">
                    Annotated image is not available. Restart the FastAPI backend after this update so `/evidence` files are served.
                  </div>
                )}
              </div>

              <div>
                <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Vehicle Details</h4>
                {result.vehicles.length > 0 ? (
                  <div className="space-y-3">
                    {result.vehicles.map((vehicle) => {
                      const vehicleViolations = vehicle.violations || [];
                      const bestConfidence = vehicleViolations[0]?.confidence ?? vehicle.confidence;

                      return (
                        <div key={vehicle.vehicle_id} className="bg-dark-900 border border-dark-700 rounded-lg p-4">
                          <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                            <div>
                              <p className="text-white font-bold">
                                Vehicle #{vehicle.vehicle_id ?? '-'} - {(vehicle.vehicle_type || 'vehicle').toUpperCase()}
                              </p>
                              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3">
                                <div>
                                  <p className="text-xs uppercase tracking-wider text-slate-500">License Plate</p>
                                  <p className="font-mono text-white">{vehicle.license_plate || vehicle.plate_number || 'Not detected'}</p>
                                </div>
                                <div>
                                  <p className="text-xs uppercase tracking-wider text-slate-500">Plate Confidence</p>
                                  <p className="text-white">{formatConfidence(vehicle.plate_confidence)}</p>
                                </div>
                                <div>
                                  <p className="text-xs uppercase tracking-wider text-slate-500">Violation Confidence</p>
                                  <p className="text-white">{formatConfidence(bestConfidence)}</p>
                                </div>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 text-slate-400">
                              <Gauge className="w-4 h-4" />
                              <span className="text-sm">{vehicleViolations.length} flagged</span>
                            </div>
                          </div>

                          <div className="flex flex-wrap gap-2 mt-4">
                            {vehicleViolations.length > 0 ? (
                              vehicleViolations.map((viol, idx) => (
                                <ViolationBadge key={`${viol.type || viol}-${idx}`} type={viol.type || viol} />
                              ))
                            ) : (
                              <span className="text-sm text-success">No violations</span>
                            )}
                          </div>
                        </div>
                      );
                    })}

                    {result.sceneViolations.length > 0 && (
                      <div className="bg-dark-900 border border-dark-700 rounded-lg p-4">
                        <p className="text-white font-bold mb-3">Scene Violations</p>
                        <div className="flex flex-wrap gap-2">
                          {result.sceneViolations.map((viol, idx) => (
                            <ViolationBadge key={`${viol.type}-${idx}`} type={viol.type} />
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="p-4 bg-dark-900 border border-dark-700 rounded-lg text-slate-400 text-center">
                    No vehicles detected in this image.
                  </div>
                )}
              </div>

              {!hasViolations && (
                <div className="p-4 bg-success/10 border border-success/20 rounded-lg text-success text-center">
                  No traffic violations detected in this image.
                </div>
              )}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
