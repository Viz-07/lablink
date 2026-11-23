import { render } from '@testing-library/react';
import type { ReactElement } from 'react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';
import { AuthProvider, ToastProvider } from '../hooks';

type Reply = { status?: number; body?: unknown };

/** Stub fetch with a route table: keys are "METHOD /api/path" (query string ignored). */
export function mockApi(routes: Record<string, Reply | ((body: unknown) => Reply)>) {
  const calls: { method: string; path: string; headers: Record<string, string>; body: unknown }[] = [];
  const fetchMock = vi.fn(async (input: string, init: RequestInit = {}) => {
    const method = init.method || 'GET';
    const path = input.split('?')[0] ?? input;
    const body = typeof init.body === 'string' ? JSON.parse(init.body) : undefined;
    calls.push({ method, path, headers: (init.headers || {}) as Record<string, string>, body });
    const entry = routes[method + ' ' + path];
    const reply = typeof entry === 'function' ? entry(body) : entry ?? { status: 404, body: { error: { code: 'NOT_FOUND', message: 'Not found' } } };
    const status = reply.status ?? 200;
    return new Response(status === 204 ? null : JSON.stringify(reply.body ?? {}), { status, headers: { 'Content-Type': 'application/json' } });
  });
  vi.stubGlobal('fetch', fetchMock);
  return calls;
}

export function renderAt(path: string, pattern: string, element: ReactElement) {
  return render(<MemoryRouter initialEntries={[path]}><AuthProvider><ToastProvider>
    <Routes><Route path={pattern} element={element}/><Route path="*" element={<p>Navigated away</p>}/></Routes>
  </ToastProvider></AuthProvider></MemoryRouter>);
}
