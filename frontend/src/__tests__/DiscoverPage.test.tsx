import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import DiscoverPage from '../pages/DiscoverPage';
import session from './fixtures/session.json';
import { mockApi, renderAt } from './helpers';

it('preserves filters when paging and clears the cursor when a filter changes', async () => {
  mockApi({
    'GET /api/auth/me': { body: session },
    'GET /api/departments': { body: [{ id: 'ece', name: 'Electronics & Communication' }] },
    'GET /api/labs': { body: [] },
    'GET /api/equipment': { body: { items: [], total: 13, next_cursor: 'll-12' } },
  });
  const user = userEvent.setup();
  renderAt('/discover?department_id=ece', '/discover', <DiscoverPage />);

  const lastCatalogueQuery = () => {
    const calls = vi.mocked(fetch).mock.calls
      .map(([input]) => String(input))
      .filter(path => path.startsWith('/api/equipment?'));
    return new URL(calls[calls.length - 1] ?? '', 'https://lablink.test').searchParams;
  };

  await user.click(await screen.findByRole('button', { name: 'Next' }));
  await waitFor(() => expect(lastCatalogueQuery().get('cursor')).toBe('ll-12'));
  expect(lastCatalogueQuery().get('department_id')).toBe('ece');

  await user.click(await screen.findByRole('button', { name: 'Previous' }));
  await waitFor(() => expect(lastCatalogueQuery().has('cursor')).toBe(false));

  await user.click(await screen.findByRole('button', { name: 'Next' }));
  await waitFor(() => expect(lastCatalogueQuery().get('cursor')).toBe('ll-12'));
  await user.selectOptions(screen.getByLabelText('Department'), '');
  await waitFor(() => {
    const query = lastCatalogueQuery();
    expect(query.has('department_id')).toBe(false);
    expect(query.has('cursor')).toBe(false);
  });
  expect(await screen.findByRole('button', { name: 'Previous' })).toBeDisabled();
});
