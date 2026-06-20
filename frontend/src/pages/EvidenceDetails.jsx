import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getAssetUrl, getEvidenceDetails, getEvidenceDownloadUrl } from '../services/api';
import ViolationBadge from '../components/ViolationBadge';
import { ArrowLeft, Download, ShieldCheck, Clock, Hash, Car } from 'lucide-react';

export default function EvidenceDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [record, setRecord] = useState(null);

  useEffect(() => {
    getEvidenceDetails(id).then(setRecord).catch(console.error);
  }, [id]);

  if (!record) return <div className="p-8 text-slate-400">Loading evidence {id}...</div>;

  const annotatedSrc = getAssetUrl(record.annotated_path || `/evidence/${record.evidence_id}/annotated.jpg`);
  const originalSrc = getAssetUrl(record.image_path || record.original_image_path || `/evidence/${record.evidence_id}/original.jpg`);

  return (
    <div className="p-8">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate(-1)} className="p-2 bg-dark-800 hover:bg-dark-700 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-white" />
          </button>
          <div>
            <h1 className="text-2xl font-bold text-white font-mono">{record.evidence_id}</h1>
            <p className="text-slate-400">Generated on {new Date(record.timestamp).toLocaleString()}</p>
          </div>
        </div>
        
        <a 
          href={getEvidenceDownloadUrl(record.evidence_id)}
          className="flex items-center gap-2 bg-primary hover:bg-blue-600 text-white px-6 py-2.5 rounded-lg font-medium shadow-lg transition-colors"
        >
          <Download className="w-5 h-5" />
          Download Package (ZIP)
        </a>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Col: Metadata */}
        <div className="space-y-6">
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm">
            <h2 className="text-lg font-bold text-white mb-6 border-b border-dark-700 pb-2">Violation Details</h2>
            
            <div className="space-y-4">
              <div className="flex items-start gap-4">
                <Hash className="w-5 h-5 text-slate-400 mt-0.5" />
                <div>
                  <p className="text-sm text-slate-400 mb-1">License Plate (OCR)</p>
                  <p className="text-xl font-bold text-white">{record.plate_number || 'N/A'}</p>
                  {record.ocr_confidence && <p className="text-xs text-success mt-1">{(record.ocr_confidence * 100).toFixed(1)}% OCR Confidence</p>}
                </div>
              </div>

              <div className="flex items-start gap-4">
                <Car className="w-5 h-5 text-slate-400 mt-0.5" />
                <div>
                  <p className="text-sm text-slate-400 mb-1">Vehicle Type</p>
                  <p className="text-white capitalize font-medium">{record.vehicle_type}</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <ShieldCheck className="w-5 h-5 text-slate-400 mt-0.5" />
                <div>
                  <p className="text-sm text-slate-400 mb-2">Detected Violations</p>
                  <div className="flex flex-col gap-2 items-start">
                    {record.violations.map(v => <ViolationBadge key={v} type={v} />)}
                  </div>
                  <p className="text-xs text-success mt-2">Max Confidence: {(record.confidence * 100).toFixed(1)}%</p>
                </div>
              </div>

              <div className="flex items-start gap-4">
                <Clock className="w-5 h-5 text-slate-400 mt-0.5" />
                <div>
                  <p className="text-sm text-slate-400 mb-1">Processing Time</p>
                  <p className="text-white font-medium">{record.processing_time_ms} ms</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Col: Images */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-dark-800 rounded-xl overflow-hidden border border-dark-700 shadow-sm relative group">
            <div className="absolute top-4 left-4 bg-black/70 backdrop-blur px-3 py-1.5 rounded-lg text-white text-sm font-medium border border-white/10 shadow-lg">
              Annotated Evidence
            </div>
            {annotatedSrc ? (
              <img
                src={annotatedSrc}
                alt="Annotated Evidence"
                className="w-full h-auto object-contain bg-black"
              />
            ) : (
              <div className="min-h-64 flex items-center justify-center text-slate-400 bg-black">Annotated image unavailable</div>
            )}
          </div>
          
          <div className="bg-dark-800 rounded-xl overflow-hidden border border-dark-700 shadow-sm relative">
            <div className="absolute top-4 left-4 bg-black/70 backdrop-blur px-3 py-1.5 rounded-lg text-white text-sm font-medium border border-white/10 shadow-lg">
              Original Capture
            </div>
            {originalSrc ? (
              <img
                src={originalSrc}
                alt="Original Capture"
                className="w-full h-auto object-contain bg-black opacity-80"
              />
            ) : (
              <div className="min-h-64 flex items-center justify-center text-slate-400 bg-black">Original image unavailable</div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
