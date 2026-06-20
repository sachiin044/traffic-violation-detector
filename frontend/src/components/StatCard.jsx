import React from 'react';

export default function StatCard({ title, value, icon: Icon, colorClass }) {
  return (
    <div className="bg-dark-800 rounded-xl p-6 border border-dark-700 shadow-sm flex items-center justify-between">
      <div>
        <p className="text-sm font-medium text-slate-400 mb-1">{title}</p>
        <p className="text-3xl font-bold text-white">{value}</p>
      </div>
      <div className={`p-4 rounded-lg ${colorClass} bg-opacity-10`}>
        <Icon className={`w-8 h-8 ${colorClass.replace('bg-', 'text-')}`} />
      </div>
    </div>
  );
}
