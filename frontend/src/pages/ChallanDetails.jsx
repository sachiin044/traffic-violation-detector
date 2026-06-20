import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getChallanDetails, updateChallanStatus, getChallanPdfUrl } from '../services/api';
import { ArrowLeft, FileText, Download, CheckCircle, AlertTriangle, Clock, Activity, FileBadge, IndianRupee } from 'lucide-react';

export default function ChallanDetails() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [challan, setChallan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchChallan = async () => {
    try {
      const data = await getChallanDetails(id);
      setChallan(data);
    } catch (err) {
      setError("Failed to load challan. " + err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChallan();
  }, [id]);

  const handleStatusUpdate = async (newStatus) => {
    try {
      await updateChallanStatus(id, newStatus);
      setChallan({ ...challan, status: newStatus });
    } catch (err) {
      alert("Failed to update status");
    }
  };

  if (loading) return <div className="p-8 text-slate-400">Loading challan details...</div>;
  if (error) return <div className="p-8 text-danger">{error}</div>;
  if (!challan) return <div className="p-8 text-slate-400">Challan not found.</div>;

  return (
    <div className="p-8 h-full flex flex-col overflow-y-auto">
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center">
          <button 
            onClick={() => navigate('/enforcement')}
            className="mr-4 p-2 rounded-full hover:bg-dark-700 transition-colors text-slate-400"
          >
            <ArrowLeft className="w-6 h-6" />
          </button>
          <div>
            <h1 className="text-3xl font-bold text-white flex items-center">
              {challan.challan_id}
              <span className="ml-4 px-3 py-1 bg-dark-800 border border-dark-600 rounded-full text-sm text-slate-300 font-mono">
                Evidence: {challan.evidence_id}
              </span>
            </h1>
          </div>
        </div>
        
        <div className="flex space-x-3">
          <a
            href={getChallanPdfUrl(challan.challan_id)}
            target="_blank"
            rel="noreferrer"
            className="flex items-center px-4 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-600 text-white rounded-lg transition-colors font-medium"
          >
            <Download className="w-4 h-4 mr-2" /> Download PDF
          </a>
          
          {challan.status === 'REVIEW_REQUIRED' && (
            <button 
              onClick={() => handleStatusUpdate('GENERATED')}
              className="flex items-center px-4 py-2 bg-success/20 hover:bg-success/30 text-success border border-success/50 rounded-lg font-bold transition-colors"
            >
              <CheckCircle className="w-4 h-4 mr-2" /> Approve Review
            </button>
          )}
          
          {challan.status === 'GENERATED' && (
            <button 
              onClick={() => handleStatusUpdate('ISSUED')}
              className="flex items-center px-4 py-2 bg-primary/20 hover:bg-primary/30 text-primary border border-primary/50 rounded-lg font-bold transition-colors"
            >
              <FileBadge className="w-4 h-4 mr-2" /> Issue Notice
            </button>
          )}
          
          {challan.status === 'ISSUED' && (
            <button 
              onClick={() => handleStatusUpdate('PAID')}
              className="flex items-center px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-500 border border-emerald-500/50 rounded-lg font-bold transition-colors"
            >
              <IndianRupee className="w-4 h-4 mr-2" /> Mark as Paid
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-8">
        {/* Left Column: Metadata */}
        <div className="space-y-8">
          
          {/* Status Card */}
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm">
            <h2 className="text-lg font-bold text-white mb-4">Current Status</h2>
            <div className="flex items-center mb-2">
              {challan.status === 'REVIEW_REQUIRED' ? <Clock className="w-6 h-6 text-warning mr-3" /> :
               challan.status === 'GENERATED' ? <Activity className="w-6 h-6 text-blue-400 mr-3" /> :
               challan.status === 'ISSUED' ? <FileBadge className="w-6 h-6 text-primary mr-3" /> :
               challan.status === 'PAID' ? <CheckCircle className="w-6 h-6 text-emerald-500 mr-3" /> :
               <AlertTriangle className="w-6 h-6 text-danger mr-3" />}
              <span className="text-xl font-bold text-white tracking-wide">{challan.status}</span>
            </div>
            {challan.status === 'REVIEW_REQUIRED' && (
              <p className="text-sm text-slate-400 mt-2 border-l-2 border-warning pl-3">
                AI Confidence is {(challan.confidence * 100).toFixed(1)}%, which is below the auto-issue threshold (85%). Human review is required.
              </p>
            )}
          </div>
          
          {/* Offender Info */}
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm">
            <h2 className="text-lg font-bold text-white mb-4 flex items-center">
              <FileText className="w-5 h-5 mr-2 text-primary" /> Offender Details
            </h2>
            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">License Plate</p>
                <p className="text-2xl font-bold text-white font-mono">{challan.plate_number}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Vehicle Type</p>
                <p className="text-white">{challan.vehicle_type}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider font-semibold">Violation Type</p>
                <p className="text-white text-lg font-medium">{challan.violation_type}</p>
              </div>
              <div className="bg-danger/10 p-4 rounded-lg border border-danger/20 mt-4">
                <p className="text-xs text-danger uppercase tracking-wider font-semibold mb-1">Fine Amount</p>
                <p className="text-3xl font-bold text-danger flex items-center">
                  <IndianRupee className="w-6 h-6 mr-1" /> {challan.fine_amount}
                </p>
              </div>
            </div>
          </div>
          
          {/* Timeline Info */}
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm">
            <h2 className="text-lg font-bold text-white mb-4">Timeline</h2>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between border-b border-dark-700 pb-2">
                <span className="text-slate-400">Violation Occurred</span>
                <span className="text-white">{new Date(challan.timestamp).toLocaleString()}</span>
              </div>
              <div className="flex justify-between pb-2">
                <span className="text-slate-400">Challan Created</span>
                <span className="text-white">{new Date(challan.created_at).toLocaleString()}</span>
              </div>
            </div>
          </div>
          
        </div>

        {/* Right Column: PDF Preview / Evidence */}
        <div className="lg:col-span-2 space-y-8 flex flex-col h-full">
          <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex-1 flex flex-col">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-white">Official Notice Document</h2>
              <span className="px-3 py-1 bg-primary/10 text-primary rounded-full text-xs font-bold border border-primary/20">
                PDF Ready
              </span>
            </div>
            
            <div className="flex-1 bg-dark-900 rounded-lg border border-dark-700 overflow-hidden min-h-[600px] flex items-center justify-center relative group">
               <object 
                 data={getChallanPdfUrl(challan.challan_id)} 
                 type="application/pdf" 
                 width="100%" 
                 height="100%"
                 className="absolute inset-0 z-0"
               >
                 <p className="text-slate-400 text-center">Your browser does not support embedded PDFs. <br/><br/> 
                   <a href={getChallanPdfUrl(challan.challan_id)} className="text-primary underline">Download it here</a>
                 </p>
               </object>
               
               {/* Overlay fallback if object fails to load visually */}
               <div className="z-10 bg-dark-900/80 p-6 rounded-xl backdrop-blur-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none absolute bottom-10 left-1/2 -translate-x-1/2 flex items-center shadow-2xl border border-dark-700">
                  <FileBadge className="w-8 h-8 text-primary mr-4" />
                  <div>
                    <h3 className="text-white font-bold">Challan PDF Rendered</h3>
                    <p className="text-slate-400 text-sm">Generated by AI-Assisted System using ReportLab</p>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
