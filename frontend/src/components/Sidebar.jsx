import React, { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import {
  BarChart3,
  Camera,
  FileBadge,
  FileText,
  LayoutDashboard,
  ShieldCheck,
  Video,
} from 'lucide-react';
import { getHealth } from '../services/api';

const NAV_GROUPS = [
  {
    label: 'Review',
    items: [
      { name: 'Check a photo', path: '/image', icon: Camera },
      { name: 'Check a video', path: '/video', icon: Video },
      { name: 'Evidence', path: '/evidence', icon: FileText },
      { name: 'Challans', path: '/challans', icon: FileBadge },
    ],
  },
  {
    label: 'Insights',
    items: [
      { name: 'Overview', path: '/', icon: LayoutDashboard, end: true },
      { name: 'Analytics', path: '/analytics', icon: BarChart3 },
      { name: 'Enforcement', path: '/enforcement', icon: ShieldCheck },
    ],
  },
];

const EXPECTED_MODELS = 7;

function useBackendStatus() {
  const [status, setStatus] = useState({ state: 'checking' });

  useEffect(() => {
    let cancelled = false;

    const check = async () => {
      try {
        const health = await getHealth();
        if (cancelled) return;
        const loaded = health.models_loaded ?? 0;
        let state = 'ready';
        if (health.status !== 'healthy') state = 'loading';
        else if (loaded < EXPECTED_MODELS) state = 'degraded';
        setStatus({ state, loaded, gpu: health.gpu_name });
      } catch {
        if (!cancelled) setStatus({ state: 'offline' });
      }
    };

    check();
    const timer = setInterval(check, 30000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, []);

  return status;
}

function StatusLine({ status }) {
  const { state, loaded, gpu } = status;
  const copy = {
    checking: ['Connecting to the API', 'Checking which models are loaded'],
    loading: ['Models are loading', 'Detection starts once they finish'],
    ready: ['Models ready', `${loaded} detectors on ${gpu ? 'GPU' : 'CPU'}`],
    degraded: ['Some models missing', `${loaded} of ${EXPECTED_MODELS} detectors loaded`],
    offline: ['API not reachable', 'Start the backend on port 8000'],
  }[state];

  return (
    <div className="vd-rail-status" data-state={state} role="status">
      <strong>{copy[0]}</strong>
      {copy[1]}
    </div>
  );
}

export default function Sidebar() {
  const status = useBackendStatus();

  return (
    <aside className="vd-rail" aria-label="Main navigation">
      <NavLink to="/" className="vd-brand" aria-label="Violation Desk home">
        <span className="vd-brand-mark" aria-hidden="true" />
        Violation Desk
      </NavLink>

      {NAV_GROUPS.map((group) => (
        <nav key={group.label} className="vd-nav-group" aria-label={group.label}>
          <p>{group.label}</p>
          {group.items.map(({ name, path, icon: Icon, end }) => (
            <NavLink
              key={path}
              to={path}
              end={end}
              title={name}
              className={({ isActive }) => `vd-nav-link${isActive ? ' is-active' : ''}`}
            >
              <Icon aria-hidden="true" />
              <span>{name}</span>
            </NavLink>
          ))}
        </nav>
      ))}

      <StatusLine status={status} />
    </aside>
  );
}
