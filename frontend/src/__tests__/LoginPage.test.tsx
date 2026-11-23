import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import LoginPage from '../pages/LoginPage';
import personas from './fixtures/personas.json';
import session from './fixtures/session.json';
import { mockApi, renderAt } from './helpers';

describe('LoginPage', () => {
  it('lists personas with descriptive names and has no axe violations', async () => {
    mockApi({ 'GET /api/auth/personas': { body: personas }, 'GET /api/auth/me': { status: 401, body: {} } });
    const { container } = renderAt('/login', '/login', <LoginPage/>);
    expect(await screen.findByRole('button', { name: /Continue as Aarav Shetty, Student/ })).toBeInTheDocument();
    expect(screen.getByRole('heading', { level: 1 })).toHaveFocus();
    expect(await axe(container)).toHaveNoViolations();
  });

  it('signs in and leaves the login page', async () => {
    const calls = mockApi({
      'GET /api/auth/personas': { body: personas },
      'GET /api/auth/me': { body: session },
      'POST /api/auth/demo': { body: { user: session.user } },
    });
    renderAt('/login', '/login', <LoginPage/>);
    await userEvent.click(await screen.findByRole('button', { name: /Continue as Dr. Meera Kulkarni/ }));
    await waitFor(() => expect(screen.getByText('Navigated away')).toBeInTheDocument());
    expect(calls.some(c => c.method === 'POST' && c.body && (c.body as { persona_id: string }).persona_id === 'u-meera')).toBe(true);
  });
});
