import { describe, expect, it, vi } from 'vitest';
import { ApiError, api, post } from '../api/client';
import { mockApi } from './helpers';

describe('api client', () => {
  it('sends the CSRF header and JSON body', async () => {
    const calls = mockApi({ 'POST /api/auth/demo': { body: { ok: true } } });
    await post('/auth/demo', { persona_id: 'u-aarav' });
    expect(calls[0]?.headers['X-Requested-With']).toBe('LabLink');
    expect(calls[0]?.body).toEqual({ persona_id: 'u-aarav' });
  });

  it('turns the error envelope into an ApiError', async () => {
    mockApi({ 'GET /api/bookings/x': { status: 409, body: { error: { code: 'SLOT_UNAVAILABLE', message: 'Taken', request_id: 'r1' } } } });
    const error = await api('/bookings/x').catch(e => e);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 409, code: 'SLOT_UNAVAILABLE', message: 'Taken', requestId: 'r1' });
  });

  it('announces an expired session on 401', async () => {
    mockApi({ 'GET /api/bookings/mine': { status: 401, body: { error: { code: 'UNAUTHORIZED', message: 'Sign in' } } } });
    const listener = vi.fn();
    window.addEventListener('lablink:expired', listener);
    await api('/bookings/mine').catch(() => undefined);
    expect(listener).toHaveBeenCalledOnce();
  });

  it('returns undefined for 204 responses', async () => {
    mockApi({ 'POST /api/auth/logout': { status: 204 } });
    await expect(post('/auth/logout')).resolves.toBeUndefined();
  });
});
