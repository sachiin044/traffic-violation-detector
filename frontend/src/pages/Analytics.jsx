import React, { useEffect, useState } from 'react';
import { getDashboardSummary, getTopPlates, getTrends, getHotspots } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend, LineChart, Line } from 'recharts';
import { MapPin } from 'lucide-react';

const CustomTooltip = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-dark-900 border border-dark-700 p-3 rounded shadow-lg">
        <p className="text-white font-medium mb-1">{label}</p>
        {payload.map(p => (
           <p key={p.name} className="text-sm" style={{color: p.color}}>
             {p.name}: <span className="font-bold">{p.value}</span>
           </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function Analytics() {
  const [summary, setSummary] = useState(null);
  const [topPlates, setTopPlates] = useState([]);
  const [trends, setTrends] = useState([]);
  const [hotspots, setHotspots] = useState([]);

  useEffect(() => {
    getDashboardSummary().then(setSummary).catch(console.error);
    getTopPlates(5).then(setTopPlates).catch(console.error);
    getTrends().then(setTrends).catch(console.error);
    getHotspots().then(setHotspots).catch(console.error);
  }, []);

  if (!summary) return <div className="p-8 text-slate-400">Loading analytics...</div>;

  const pieData = [
    { name: 'Helmet', value: summary.helmet, color: '#f59e0b' },
    { name: 'Triple Riding', value: summary.triple_riding, color: '#ef4444' },
    { name: 'Seatbelt', value: summary.seatbelt, color: '#3b82f6' },
    { name: 'Red Light', value: summary.red_light, color: '#dc2626' },
    { name: 'Illegal Parking', value: summary.illegal_parking, color: '#a855f7' },
  ].filter(d => d.value > 0);



  return (
    <div className="p-8 h-full flex flex-col overflow-y-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Advanced Analytics</h1>
        <p className="text-slate-400">Temporal trends, hotspots, and violation distribution</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
        {/* Trend Graph */}
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex flex-col lg:col-span-2">
          <h2 className="text-lg font-bold text-white mb-6">Daily Violations Trend</h2>
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trends} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="date" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip content={<CustomTooltip />} />
                <Legend />
                <Line type="monotone" dataKey="helmet" stroke="#f59e0b" strokeWidth={3} dot={{r:4}} />
                <Line type="monotone" dataKey="triple_riding" stroke="#ef4444" strokeWidth={3} dot={{r:4}} />
                <Line type="monotone" dataKey="red_light" stroke="#dc2626" strokeWidth={3} dot={{r:4}} />
                <Line type="monotone" dataKey="wrong_side" stroke="#10b981" strokeWidth={3} dot={{r:4}} />
                <Line type="monotone" dataKey="seatbelt" stroke="#3b82f6" strokeWidth={3} dot={{r:4}} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Violations by Type (Pie) */}
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex flex-col">
          <h2 className="text-lg font-bold text-white mb-6">Violations Breakdown</h2>
          <div className="flex-1 min-h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} cx="50%" cy="50%" innerRadius={80} outerRadius={120} paddingAngle={5} dataKey="value" stroke="none">
                  {pieData.map((entry, index) => <Cell key={`cell-${index}`} fill={entry.color} />)}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
                <Legend verticalAlign="bottom" height={36} iconType="circle" />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Hotspots */}
        <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex flex-col">
          <h2 className="text-lg font-bold text-white mb-6">Camera Hotspots</h2>
          <div className="flex-1 overflow-y-auto">
            <div className="space-y-4">
              {hotspots.map((spot, idx) => (
                <div key={idx} className="flex items-center justify-between p-4 bg-dark-900 rounded-lg border border-dark-700">
                  <div className="flex items-center">
                    <div className="p-2 bg-danger/10 text-danger rounded-lg mr-4">
                      <MapPin className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-white font-bold">{spot.location || spot.camera_id}</h4>
                      <p className="text-xs text-slate-500 font-mono">{spot.latitude}, {spot.longitude}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-xl font-bold text-white">{spot.total_violations}</span>
                    <p className="text-xs text-slate-400">violations</p>
                  </div>
                </div>
              ))}
              {hotspots.length === 0 && <p className="text-slate-500">No hotspot data available.</p>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
