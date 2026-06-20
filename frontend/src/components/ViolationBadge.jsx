import React from 'react';

export default function ViolationBadge({ type }) {
  let color = 'bg-slate-500/20 text-slate-400 border-slate-500/30';
  
  if (type === 'Helmet Non Compliance') color = 'bg-warning/20 text-warning border-warning/30';
  else if (type === 'Triple Riding') color = 'bg-danger/20 text-danger border-danger/30';
  else if (type === 'Seatbelt Non Compliance') color = 'bg-primary/20 text-primary border-primary/30';
  else if (type === 'Red Light Violation') color = 'bg-red-600/20 text-red-500 border-red-600/30';
  else if (type === 'Illegal Parking') color = 'bg-purple-500/20 text-purple-400 border-purple-500/30';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${color}`}>
      {type}
    </span>
  );
}
