import React, { useState, useEffect } from 'react';
import { getChallans, updateChallanStatus, manualGenerateChallan } from '../services/api';
import { useNavigate } from 'react-router-dom';
import { FileText, Search, Filter, ShieldAlert, IndianRupee, ArrowRight, CheckCircle, Clock } from 'lucide-react';

export default function ChallanExplorer() {
  const [challans, setChallans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [plateFilter, setPlateFilter] = useState('');
  
  const navigate = useNavigate();

  const fetchChallans = async () => {
    setLoading(true);
    try {
      const data = await getChallans({ 
        limit: 50, 
        status: statusFilter || undefined,
        plate_number: plateFilter || undefined
      });
      setChallans(data.records);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChallans();
  }, [statusFilter]);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchChallans();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'GENERATED': return 'bg-blue-500/20 text-blue-400 border-blue-500/30';
      case 'REVIEW_REQUIRED': return 'bg-warning/20 text-warning border-warning/30';
      case 'ISSUED': return 'bg-primary/20 text-primary border-primary/30';
      case 'PAID': return 'bg-success/20 text-success border-success/30';
      case 'DISPUTED': return 'bg-danger/20 text-danger border-danger/30';
      default: return 'bg-slate-700/50 text-slate-400 border-slate-600';
    }
  };

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Challan Explorer</h1>
          <p className="text-slate-400">Search and manage traffic violation notices.</p>
        </div>
      </div>

      <div className="bg-dark-800 rounded-xl border border-dark-700 shadow-sm flex-1 flex flex-col overflow-hidden">
        
        {/* Filters */}
        <div className="p-4 border-b border-dark-700 flex flex-wrap gap-4 items-center justify-between">
          <form onSubmit={handleSearch} className="flex flex-1 max-w-md">
            <div className="relative w-full">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="text"
                placeholder="Search plate number..."
                value={plateFilter}
                onChange={(e) => setPlateFilter(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-dark-900 border border-dark-600 rounded-lg text-white focus:outline-none focus:border-primary transition-colors"
              />
            </div>
            <button type="submit" className="ml-2 bg-primary hover:bg-blue-600 text-white px-4 py-2 rounded-lg transition-colors font-medium">
              Search
            </button>
          </form>

          <div className="flex items-center space-x-2">
            <Filter className="w-5 h-5 text-slate-500" />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-dark-900 border border-dark-600 text-white rounded-lg px-4 py-2 focus:outline-none focus:border-primary transition-colors"
            >
              <option value="">All Statuses</option>
              <option value="REVIEW_REQUIRED">Review Required</option>
              <option value="GENERATED">Generated</option>
              <option value="ISSUED">Issued</option>
              <option value="PAID">Paid</option>
              <option value="DISPUTED">Disputed</option>
            </select>
          </div>
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          {loading ? (
            <div className="flex justify-center items-center h-full text-slate-500">Loading challans...</div>
          ) : challans.length === 0 ? (
            <div className="flex justify-center items-center h-full text-slate-500 flex-col">
              <ShieldAlert className="w-12 h-12 mb-4 opacity-50" />
              <p>No challans found matching your criteria.</p>
            </div>
          ) : (
            <table className="w-full text-left border-collapse">
              <thead className="bg-dark-900/50 sticky top-0 z-10">
                <tr>
                  <th className="p-4 text-slate-400 font-medium border-b border-dark-700">Challan ID</th>
                  <th className="p-4 text-slate-400 font-medium border-b border-dark-700">Plate Number</th>
                  <th className="p-4 text-slate-400 font-medium border-b border-dark-700">Violation</th>
                  <th className="p-4 text-slate-400 font-medium border-b border-dark-700">Fine</th>
                  <th className="p-4 text-slate-400 font-medium border-b border-dark-700">Confidence</th>
                  <th className="p-4 text-slate-400 font-medium border-b border-dark-700">Status</th>
                  <th className="p-4 text-slate-400 font-medium border-b border-dark-700">Action</th>
                </tr>
              </thead>
              <tbody>
                {challans.map((challan) => (
                  <tr key={challan.challan_id} className="border-b border-dark-700 hover:bg-dark-700/30 transition-colors">
                    <td className="p-4">
                      <div className="flex items-center text-primary font-mono text-sm">
                        <FileText className="w-4 h-4 mr-2" />
                        {challan.challan_id}
                      </div>
                      <div className="text-xs text-slate-500 mt-1">{new Date(challan.timestamp).toLocaleString()}</div>
                    </td>
                    <td className="p-4 font-bold text-white tracking-wider">{challan.plate_number}</td>
                    <td className="p-4 text-slate-300">{challan.violation_type}</td>
                    <td className="p-4 text-warning font-bold">₹{challan.fine_amount}</td>
                    <td className="p-4">
                      <span className={`px-2 py-1 rounded text-xs font-bold ${challan.confidence >= 0.85 ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}`}>
                        {(challan.confidence * 100).toFixed(1)}%
                      </span>
                    </td>
                    <td className="p-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-bold border ${getStatusColor(challan.status)}`}>
                        {challan.status}
                      </span>
                    </td>
                    <td className="p-4">
                      <button
                        onClick={() => navigate(`/challan/${challan.challan_id}`)}
                        className="text-slate-400 hover:text-primary transition-colors p-2 hover:bg-primary/10 rounded-lg flex items-center"
                      >
                        Details <ArrowRight className="w-4 h-4 ml-1" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
