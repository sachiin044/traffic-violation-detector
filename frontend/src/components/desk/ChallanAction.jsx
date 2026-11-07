import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getChallans, manualGenerateChallan } from '../../services/api';
import { errorMessage } from '../../lib/format';
import StatusPillInline from './StatusPillInline';

/**
 * Shows the challan already created for this evidence, or a button to create one.
 * A readable plate is required; without one the button is disabled with a reason.
 */
export default function ChallanAction({ evidenceId, plate }) {
  const [challan, setChallan] = useState({ state: plate ? 'checking' : 'idle' });

  useEffect(() => {
    if (!evidenceId || !plate) return undefined;
    let cancelled = false;
    setChallan({ state: 'checking' });
    getChallans({ plate_number: plate, limit: 100 })
      .then((data) => {
        if (cancelled) return;
        const match = (data?.records || []).find((c) => c.evidence_id === evidenceId);
        setChallan(match ? { state: 'exists', id: match.challan_id, status: match.status } : { state: 'idle' });
      })
      .catch(() => { if (!cancelled) setChallan({ state: 'idle' }); });
    return () => { cancelled = true; };
  }, [evidenceId, plate]);

  const create = async () => {
    setChallan({ state: 'creating' });
    try {
      const data = await manualGenerateChallan(evidenceId);
      setChallan({ state: 'created', id: data.challan_id, status: 'GENERATED' });
    } catch (err) {
      setChallan({ state: 'error', message: errorMessage(err, 'The challan could not be created.') });
    }
  };

  if (challan.state === 'exists' || challan.state === 'created') {
    return (
      <div className="vd-callout" data-tone="ok">
        {challan.state === 'exists' ? 'Challan ' : 'Challan created: '}
        <Link className="vd-link" to={`/challan/${challan.id}`}>{challan.id}</Link>
        {challan.state === 'exists' && <> is <StatusPillInline status={challan.status} /></>}
      </div>
    );
  }

  return (
    <>
      <button
        type="button"
        className="vd-btn vd-btn--primary vd-btn--block"
        onClick={create}
        disabled={!plate || challan.state === 'creating' || challan.state === 'checking'}
        title={plate ? undefined : 'A readable plate is needed to create a challan'}
      >
        {challan.state === 'creating' ? 'Creating challan…' : 'Generate challan'}
      </button>
      {!plate && <p className="vd-legend" style={{ marginTop: 0 }}>A readable plate is needed to create a challan.</p>}
      {challan.state === 'error' && <div className="vd-callout" data-tone="error" role="alert">{challan.message}</div>}
    </>
  );
}
