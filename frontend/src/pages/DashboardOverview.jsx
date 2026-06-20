import React, { useEffect, useState } from 'react';
import { getDashboardSummary, searchEvidence } from '../services/api';
import StatCard from '../components/StatCard';
import ViolationBadge from '../components/ViolationBadge';
import { Activity, ShieldAlert, Users, CarFront, AlertOctagon, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function DashboardOverview() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [recent, setRecent] = useState([]);

  const fetchData = async () => {
    try {
      const summary = await getDashboardSummary();
      setStats(summary);
      
      const latest = await searchEvidence({ limit: 5 });
      setRecent(latest.records || []);
    } catch (err) {
      console.error("Failed to fetch dashboard data", err);
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 5000); // 5s live polling
    return () => clearInterval(interval);
  }, []);

  if (!stats) {
    return <div className="p-8 text-slate-400">Loading live data...</div>;
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white">Live Monitoring</h1>
          <p className="text-slate-400 mt-1">Real-time traffic violation analytics</p>
        </div>
        <div className="flex items-center text-success bg-success/10 px-4 py-2 rounded-lg border border-success/20 shadow-[0_0_15px_rgba(34,197,94,0.2)]">
          <Activity className="w-5 h-5 mr-2 animate-pulse" />
          <span className="font-semibold tracking-wide uppercase text-sm">System Active</span>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6 mb-8">
        <StatCard title="Total Violations" value={stats.total} icon={ShieldAlert} colorClass="bg-primary" />
        <StatCard title="Helmet Non-Compliance" value={stats.helmet} icon={Users} colorClass="bg-warning" />
        <StatCard title="Triple Riding" value={stats.triple_riding} icon={Users} colorClass="bg-danger" />
        <StatCard title="Seatbelt Violations" value={stats.seatbelt} icon={CarFront} colorClass="bg-primary" />
        <StatCard title="Red Light Crossed" value={stats.red_light} icon={AlertOctagon} colorClass="bg-red-500" />
        <StatCard title="Illegal Parking" value={stats.illegal_parking} icon={Zap} colorClass="bg-purple-500" />
      </div>

      {/* Recent Activity Feed */}
      <div className="bg-dark-800 rounded-xl border border-dark-700 shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-dark-700 flex justify-between items-center">
          <h2 className="text-lg font-bold text-white">Latest Detections</h2>
          <button onClick={() => navigate('/evidence')} className="text-sm text-primary hover:text-blue-400 transition-colors font-medium">View All</button>
        </div>
        <div className="divide-y divide-dark-700">
          {recent.map((record) => (
            <div key={record.evidence_id} className="p-4 hover:bg-dark-700/50 transition-colors cursor-pointer" onClick={() => navigate(`/evidence/${record.evidence_id}`)}>
              <div className="flex justify-between items-center">
                <div className="flex space-x-4 items-center">
                  <img 
                    src={`http://localhost:8000${record.thumbnail_path}`} 
                    className="w-16 h-12 object-cover rounded bg-dark-900 border border-dark-700"
                    alt="thumbnail"
                  />
                  <div>
                    <div className="flex items-center space-x-3 mb-1">
                      <span className="text-white font-semibold">{record.plate_number || 'UNKNOWN'}</span>
                      <span className="text-xs text-slate-400">{new Date(record.timestamp).toLocaleTimeString()}</span>
                    </div>
                    <div className="flex gap-2">
                      {record.violations.map(v => <ViolationBadge key={v} type={v} />)}
                    </div>
                  </div>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-500 font-mono block mb-1">{record.evidence_id}</span>
                  <span className="text-sm text-success font-medium">{(record.confidence * 100).toFixed(1)}% Conf</span>
                </div>
              </div>
            </div>
          ))}
          {recent.length === 0 && (
            <div className="p-8 text-center text-slate-500">No recent detections found.</div>
          )}
        </div>
      </div>
    </div>
  );
}
