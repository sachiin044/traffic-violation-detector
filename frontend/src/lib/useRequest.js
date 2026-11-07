import { useCallback, useEffect, useRef, useState } from 'react';

/**
 * Load data from the API with loading / error state.
 * `load` is called again whenever `deps` change; `interval` (ms) polls quietly.
 */
export default function useRequest(load, deps = [], { interval } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const loadRef = useRef(load);
  loadRef.current = load;
  const seq = useRef(0);

  const run = useCallback(async ({ quiet = false } = {}) => {
    const id = ++seq.current;
    if (!quiet) setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await loadRef.current();
      if (id === seq.current) setState({ data, error: null, loading: false });
    } catch (error) {
      // A failed background refresh keeps the data already on screen
      if (id === seq.current) setState((s) => ({ data: quiet ? s.data : null, error, loading: false }));
    }
  }, []);

  useEffect(() => {
    run();
    if (!interval) return undefined;
    const timer = setInterval(() => run({ quiet: true }), interval);
    return () => clearInterval(timer);
  }, [run, interval, ...deps]);

  return { ...state, reload: run };
}
