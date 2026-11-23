export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details: Record<string, unknown> = {}, public requestId = '') {
    super(message);
  }
}

export async function api<T>(path: string, init: { method?: string; body?: unknown; signal?: AbortSignal } = {}): Promise<T> {
  const { body, ...options } = init;
  const response = await fetch('/api' + path, {
    ...options, credentials: 'same-origin', headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'LabLink' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (response.status === 204) return undefined as T;
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const error = data.error;
    if (response.status === 401 && path !== '/auth/me') window.dispatchEvent(new Event('lablink:expired'));
    throw new ApiError(response.status, error?.code || 'REQUEST_FAILED', error?.message || 'The request could not be completed.', error?.details, error?.request_id);
  }
  return response.json() as Promise<T>;
}

export function post<T>(path: string, body?: unknown) {
  return api<T>(path, { method: 'POST', body });
}

