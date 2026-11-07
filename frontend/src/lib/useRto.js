import { useEffect, useState } from 'react';
import { getRto } from '../services/api';

// Plates repeat across pages, so remember answers for the session
const cache = new Map();

/** RTO registration info for a plate: undefined while loading, null if unknown. */
export default function useRto(plate) {
  const key = (plate || '').replace(/[^A-Z0-9]/gi, '').toUpperCase();
  const [info, setInfo] = useState(() => (key ? cache.get(key) : null));

  useEffect(() => {
    if (!key) { setInfo(null); return undefined; }
    if (cache.has(key)) { setInfo(cache.get(key)); return undefined; }
    let cancelled = false;
    setInfo(undefined);
    getRto(key)
      .then((data) => { cache.set(key, data); if (!cancelled) setInfo(data); })
      .catch((err) => {
        // 404 = code not in the list; remember that too. Other errors: try again next time.
        if (err?.response?.status === 404) cache.set(key, null);
        if (!cancelled) setInfo(null);
      });
    return () => { cancelled = true; };
  }, [key]);

  return info;
}
