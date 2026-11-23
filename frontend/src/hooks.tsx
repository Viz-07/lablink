import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import { api, post } from './api/client';
import type { Session } from './api/types';

export function useApi<T>(path?: string) {
  const [result, setResult] = useState<{ key?: string; data?: T; error?: Error }>({});
  const [revision, setRevision] = useState(0);
  const key = path === undefined ? undefined : path + '|' + revision;
  useEffect(() => {
    if (path === undefined) return;
    const controller = new AbortController();
    api<T>(path, { signal: controller.signal }).then(
      data => setResult({ key, data }),
      error => { if (!controller.signal.aborted) setResult({ key, error }); },
    );
    return () => controller.abort();
  }, [path, key]);
  return { data: result.key === key ? result.data : undefined, error: result.key === key ? result.error : undefined,
    loading: !!path && result.key !== key, reload: () => setRevision(n => n + 1) };
}

export function useAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  async function run<T>(operation: () => Promise<T>): Promise<T | undefined> {
    setError(null);
    setPending(true);
    try { return await operation(); }
    catch (error) { setError(error instanceof Error ? error : new Error('Something went wrong.')); }
    finally { setPending(false); }
  }
  return { pending, error, run, clear: () => setError(null) };
}

const Auth = createContext<{ session: Session | null | undefined; login: (id: string) => Promise<Session>; logout: () => Promise<void> }>({
  session: undefined, login: async () => { throw new Error('No auth provider.'); }, logout: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>();
  useEffect(() => {
    const controller = new AbortController();
    api<Session>('/auth/me', {signal: controller.signal}).then(setSession, () => {
      if (!controller.signal.aborted) setSession(null);
    });
    const expire = () => setSession(null);
    window.addEventListener('lablink:expired', expire);
    return () => { controller.abort(); window.removeEventListener('lablink:expired', expire); };
  }, []);
  async function login(id: string) {
    await post('/auth/demo', { persona_id: id });
    const session = await api<Session>('/auth/me');
    setSession(session);
    return session;
  }
  async function logout() {
    await post('/auth/logout');
    setSession(null);
  }
  return <Auth.Provider value={{ session, login, logout }}>{children}</Auth.Provider>;
}
export const useAuth = () => useContext(Auth);

const Toast = createContext<(message: string) => void>(() => {});
export function ToastProvider({ children }: { children: ReactNode }) {
  const [message, setMessage] = useState('');
  const [held, setHeld] = useState(false);
  const show = useCallback((value: string) => { setMessage(value); setHeld(false); }, []);
  useEffect(() => {
    if (!message || held) return;
    const id = window.setTimeout(() => setMessage(''), 6000);
    return () => clearTimeout(id);
  }, [message, held]);
  return <Toast.Provider value={show}>{children}<div className="toast-region" role="status" aria-live="polite">
    {message && <div className="toast" onMouseEnter={() => setHeld(true)} onMouseLeave={() => setHeld(false)} onFocus={() => setHeld(true)} onBlur={() => setHeld(false)}>{message}<button onClick={() => setMessage('')} aria-label="Dismiss message">×</button></div>}
  </div></Toast.Provider>;
}
export const useToast = () => useContext(Toast);

