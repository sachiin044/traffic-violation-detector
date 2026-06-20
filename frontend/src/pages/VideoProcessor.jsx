import React, { useState, useEffect } from 'react';
import { processVideo, getVideoStatus, getVideoResult } from '../services/api';
import { Video, UploadCloud, AlertCircle, CheckCircle2, PlayCircle, ShieldAlert } from 'lucide-react';
import ViolationBadge from '../components/ViolationBadge';

export default function VideoProcessor() {
  const [file, setFile] = useState(null);
  const [taskId, setTaskId] = useState(null);
  const [status, setStatus] = useState(null); // 'idle', 'uploading', 'processing', 'completed', 'error'
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);

  const handleUpload = async () => {
    if (!file) return;
    setStatus('uploading');
    
    try {
      const data = await processVideo(file, "CAM_001");
      setTaskId(data.task_id);
      setStatus('processing');
    } catch (err) {
      console.error(err);
      setStatus('error');
    }
  };

  useEffect(() => {
    if (status !== 'processing' || !taskId) return;

    const interval = setInterval(async () => {
      try {
        const taskStatus = await getVideoStatus(taskId);
        setProgress(taskStatus.progress || 0);
        
        if (taskStatus.status === 'completed') {
          setStatus('completed');
          const res = await getVideoResult(taskId);
          setResult(res);
          clearInterval(interval);
        } else if (taskStatus.status === 'error') {
          setStatus('error');
          clearInterval(interval);
        }
      } catch (err) {
        console.error(err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [status, taskId]);

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Video Processing</h1>
        <p className="text-slate-400">Upload traffic footage for temporal violation detection</p>
      </div>

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Upload Card */}
        <div className="bg-dark-800 rounded-xl p-8 border border-dark-700 shadow-sm flex flex-col items-center justify-center text-center">
          <div className="w-20 h-20 bg-primary/10 rounded-full flex items-center justify-center mb-6">
            <UploadCloud className="w-10 h-10 text-primary" />
          </div>
          
          <h2 className="text-xl font-bold text-white mb-2">Upload Traffic Video</h2>
          <p className="text-slate-400 mb-8 max-w-sm">
            Supports MP4, AVI, and MOV. Video will be processed using ByteTrack to track vehicle identities and detect stateful violations like red-light crossing.
          </p>
          
          <input 
            type="file" 
            accept="video/mp4,video/avi,video/quicktime"
            onChange={e => setFile(e.target.files[0])}
            className="mb-6 block w-full text-sm text-slate-400 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary file:text-white hover:file:bg-blue-600"
            disabled={status === 'processing' || status === 'uploading'}
          />
          
          <button 
            onClick={handleUpload}
            disabled={!file || status === 'processing' || status === 'uploading'}
            className="bg-primary hover:bg-blue-600 text-white px-8 py-3 rounded-lg font-medium shadow-lg transition-colors disabled:opacity-50"
          >
            {status === 'uploading' ? 'Uploading...' : 'Start Processing'}
          </button>
        </div>

        {/* Status Card */}
        <div className="bg-dark-800 rounded-xl p-8 border border-dark-700 shadow-sm flex flex-col">
          <h2 className="text-xl font-bold text-white mb-6">Job Status</h2>
          
          {status === 'idle' || !status ? (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-500">
              <Video className="w-12 h-12 mb-4 opacity-50" />
              <p>No active job. Upload a video to begin.</p>
            </div>
          ) : (
            <div className="flex-1 flex flex-col">
              <div className="flex justify-between items-center mb-2">
                <span className="text-slate-300 font-medium tracking-wide">
                  {status === 'processing' ? 'Processing Video...' : status === 'completed' ? 'Processing Complete' : status}
                </span>
                <span className="text-primary font-bold">{progress}%</span>
              </div>
              
              <div className="w-full bg-dark-900 rounded-full h-3 mb-8 border border-dark-700">
                <div 
                  className={`h-3 rounded-full ${status === 'completed' ? 'bg-success' : status === 'error' ? 'bg-danger' : 'bg-primary'}`}
                  style={{ width: `${progress}%`, transition: 'width 0.5s ease-in-out' }}
                ></div>
              </div>

              {status === 'processing' && (
                <div className="flex items-center text-warning bg-warning/10 p-4 rounded-lg border border-warning/20">
                  <PlayCircle className="w-6 h-6 mr-3 animate-pulse" />
                  <p className="text-sm">Running ByteTrack and evaluating temporal rule engine over frames...</p>
                </div>
              )}

              {status === 'completed' && result && (
                <div className="bg-success/10 border border-success/20 rounded-lg p-6 flex flex-col items-center text-center">
                  <CheckCircle2 className="w-12 h-12 text-success mb-4" />
                  <h3 className="text-white font-bold text-xl mb-2">Success!</h3>
                  <p className="text-slate-300 mb-6">Found <span className="text-danger font-bold text-lg">{result.violations}</span> violations in this video.</p>
                  
                  {result.processed_video ? (
                    <a href={`http://localhost:8000${result.processed_video}`} target="_blank" rel="noreferrer" className="text-primary hover:text-blue-400 font-medium underline mb-6 inline-block">
                      Watch Annotated Output Video
                    </a>
                  ) : (
                    <p className="text-slate-400 text-sm mb-6">Processed video file is not available.</p>
                  )}

                  {result.violation_details && result.violation_details.length > 0 && (
                    <div className="w-full text-left mt-2">
                      <h4 className="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider">Detected Violators</h4>
                      <div className="space-y-3 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
                        {result.violation_details.map((vDetail, idx) => (
                          <div key={idx} className="bg-dark-900 border border-dark-700 rounded-lg p-4">
                            <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
                              <div>
                                <p className="text-white font-bold">
                                  Track #{vDetail.track_id} - {(vDetail.vehicle_type || 'vehicle').toUpperCase()}
                                </p>
                                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3">
                                  <div>
                                    <p className="text-xs uppercase tracking-wider text-slate-500">License Plate</p>
                                    <p className="font-mono text-white">{vDetail.license_plate || 'Not detected'}</p>
                                  </div>
                                  <div>
                                    <p className="text-xs uppercase tracking-wider text-slate-500">Evidence ID</p>
                                    <p className="font-mono text-white">{vDetail.evidence_id || 'N/A'}</p>
                                  </div>
                                </div>
                              </div>
                              <div className="flex items-center gap-2 text-slate-400">
                                <ShieldAlert className="w-4 h-4 text-danger" />
                                <span className="text-sm">{vDetail.violations.length} flagged</span>
                              </div>
                            </div>
                            <div className="flex flex-wrap gap-2 mt-4">
                              {vDetail.violations.map((violType, vIdx) => (
                                <ViolationBadge key={vIdx} type={violType} />
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {status === 'error' && (
                <div className="flex items-center text-danger bg-danger/10 p-4 rounded-lg border border-danger/20">
                  <AlertCircle className="w-6 h-6 mr-3 shrink-0" />
                  <p className="text-sm">An error occurred while processing the video. Check server logs for details.</p>
                </div>
              )}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
