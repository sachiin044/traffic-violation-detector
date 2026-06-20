import React, { useEffect, useState } from 'react';
import { searchEvidence } from '../services/api';
import ViolationBadge from '../components/ViolationBadge';
import { Search, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function EvidenceExplorer() {
  const navigate = useNavigate();
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const limit = 10;
  
  const [searchPlate, setSearchPlate] = useState('');
  const [searchType, setSearchType] = useState('');

  const loadData = async () => {
    try {
      const data = await searchEvidence({
        skip: page * limit,
        limit,
        plate_number: searchPlate || undefined,
        violation_type: searchType || undefined
      });
      setRecords(data.records);
      setTotal(data.total);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadData();
  }, [page, searchPlate, searchType]);

  return (
    <div className="p-8 h-full flex flex-col">
      <div className="mb-6 flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Evidence Explorer</h1>
          <p className="text-slate-400">Browse and filter violation records ({total} total)</p>
        </div>
        
        <div className="flex gap-4">
          <div className="relative">
            <Search className="w-5 h-5 absolute left-3 top-2.5 text-slate-500" />
            <input 
              type="text" 
              placeholder="Search plate..." 
              value={searchPlate}
              onChange={(e) => setSearchPlate(e.target.value)}
              className="pl-10 pr-4 py-2 bg-dark-800 border border-dark-700 rounded-lg text-white focus:outline-none focus:border-primary transition-colors"
            />
          </div>
          <div className="relative">
            <Filter className="w-5 h-5 absolute left-3 top-2.5 text-slate-500" />
            <select 
              value={searchType}
              onChange={(e) => setSearchType(e.target.value)}
              className="pl-10 pr-8 py-2 bg-dark-800 border border-dark-700 rounded-lg text-white focus:outline-none focus:border-primary appearance-none transition-colors"
            >
              <option value="">All Violations</option>
              <option value="Helmet Non Compliance">Helmet</option>
              <option value="Triple Riding">Triple Riding</option>
              <option value="Seatbelt Non Compliance">Seatbelt</option>
              <option value="Red Light Violation">Red Light</option>
              <option value="Illegal Parking">Illegal Parking</option>
            </select>
          </div>
        </div>
      </div>

      <div className="flex-1 bg-dark-800 rounded-xl border border-dark-700 shadow-sm overflow-hidden flex flex-col">
        <div className="overflow-x-auto flex-1">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-dark-900 border-b border-dark-700 text-slate-400 text-sm uppercase tracking-wider">
                <th className="p-4 font-semibold">Evidence ID</th>
                <th className="p-4 font-semibold">Plate</th>
                <th className="p-4 font-semibold">Type</th>
                <th className="p-4 font-semibold">Violations</th>
                <th className="p-4 font-semibold">Date & Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-dark-700">
              {records.map((r) => (
                <tr 
                  key={r.evidence_id} 
                  onClick={() => navigate(`/evidence/${r.evidence_id}`)}
                  className="hover:bg-dark-700/50 cursor-pointer transition-colors"
                >
                  <td className="p-4 font-mono text-sm text-primary">{r.evidence_id}</td>
                  <td className="p-4 text-white font-medium">{r.plate_number || '-'}</td>
                  <td className="p-4 text-slate-300 capitalize">{r.vehicle_type}</td>
                  <td className="p-4 flex gap-1 flex-wrap">
                    {r.violations.map(v => <ViolationBadge key={v} type={v} />)}
                  </td>
                  <td className="p-4 text-slate-400 text-sm">
                    {new Date(r.timestamp).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className="p-4 border-t border-dark-700 flex justify-between items-center text-sm text-slate-400 bg-dark-900/50">
          <span>Showing {page * limit + 1} to {Math.min((page + 1) * limit, total)} of {total}</span>
          <div className="flex gap-2">
            <button 
              disabled={page === 0}
              onClick={() => setPage(p => p - 1)}
              className="p-2 rounded hover:bg-dark-700 disabled:opacity-50 transition-colors"
            >
              <ChevronLeft className="w-5 h-5" />
            </button>
            <button 
              disabled={(page + 1) * limit >= total}
              onClick={() => setPage(p => p + 1)}
              className="p-2 rounded hover:bg-dark-700 disabled:opacity-50 transition-colors"
            >
              <ChevronRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
