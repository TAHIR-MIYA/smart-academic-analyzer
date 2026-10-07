import { useCallback, useEffect, useRef, useState } from "react";

/** Load data when the component mounts (or deps change). `reload()` fetches again without clearing the screen. */
export function useApi(fetcher, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const latest = useRef(0);

  const load = useCallback(async () => {
    const ticket = ++latest.current;
    try {
      const data = await fetcher();
      if (ticket === latest.current) setState({ data, error: null, loading: false });
    } catch (error) {
      if (ticket === latest.current) setState((s) => ({ data: s.data, error, loading: false }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  useEffect(() => {
    setState((s) => ({ ...s, loading: true }));
    load();
    return () => {
      latest.current++; // ignore a response that arrives after unmount or after deps changed
    };
  }, [load]);

  return { ...state, reload: load };
}
