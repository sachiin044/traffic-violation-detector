import React, { useEffect, useState } from 'react';
import { getEnforcementStats } from '../services/api';
import { FileText, Clock, CheckCircle, IndianRupee, AlertTriangle, ShieldCheck } from 'lucide-react';

export default function EnforcementCenter() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getEnforcementStats().then(setStats).catch(console.error);
  }, []);

  if (!stats) return <div className="p-8 text-slate-400">Loading enforcement data...</div>;

  return (
    <div className="p-8 h-full flex flex-col overflow-y-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Enforcement Center</h1>
        <p className="text-slate-400">Automated Challan Generation & Fine Management</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex items-center">
          <div className="p-4 rounded-full bg-primary/10 text-primary mr-4">
            <FileText className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Total Challans</p>
            <p className="text-3xl font-bold text-white">{stats.total_challans}</p>
          </div>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex items-center">
          <div className="p-4 rounded-full bg-warning/10 text-warning mr-4">
            <Clock className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Review Queue (Pending)</p>
            <p className="text-3xl font-bold text-white">{stats.review_required + stats.pending}</p>
          </div>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex items-center">
          <div className="p-4 rounded-full bg-success/10 text-success mr-4">
            <IndianRupee className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Est. Revenue</p>
            <p className="text-3xl font-bold text-white">INR {stats.estimated_fines.toLocaleString()}</p>
          </div>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex items-center">
          <div className="p-4 rounded-full bg-blue-500/10 text-blue-500 mr-4">
            <ShieldCheck className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Issued / Generated</p>
            <p className="text-3xl font-bold text-white">{stats.issued + stats.generated}</p>
          </div>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex items-center">
          <div className="p-4 rounded-full bg-emerald-500/10 text-emerald-500 mr-4">
            <CheckCircle className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Paid Challans</p>
            <p className="text-3xl font-bold text-white">{stats.paid}</p>
          </div>
        </div>

        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex items-center">
          <div className="p-4 rounded-full bg-danger/10 text-danger mr-4">
            <AlertTriangle className="w-8 h-8" />
          </div>
          <div>
            <p className="text-sm text-slate-400 font-medium">Disputed</p>
            <p className="text-3xl font-bold text-white">{stats.disputed}</p>
          </div>
        </div>
      </div>

      <div className="bg-primary/10 border border-primary/20 rounded-xl p-6 flex items-start">
        <ShieldCheck className="w-6 h-6 text-primary mt-1 mr-4 flex-shrink-0" />
        <div>
          <h3 className="text-white font-bold mb-2">Automated Enforcement Workflow</h3>
          <p className="text-slate-300 text-sm mb-2">
            Entries appear here after an uploaded image or video creates evidence with a detected license plate and qualifying violation confidence.
          </p>
          <ul className="list-disc pl-5 text-sm text-slate-400 space-y-1">
            <li><span className="text-primary font-medium">License plate required:</span> Challans are skipped when OCR cannot read a plate.</li>
            <li><span className="text-success font-medium">Confidence &gt;= 0.85:</span> Automatically generates an official Challan PDF.</li>
            <li><span className="text-warning font-medium">Confidence 0.70 - 0.84:</span> Flags evidence in the Review Queue.</li>
            <li><span className="text-danger font-medium">Confidence &lt; 0.70:</span> Records violation for analytics but suppresses challan issuance.</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
