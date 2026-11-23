import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import ConflictsPage from '../pages/ConflictsPage';
import conflict from './fixtures/conflict.json';
import recommended from './fixtures/recommended.json';
import session from './fixtures/session.json';
import { mockApi, renderAt } from './helpers';

describe('ConflictsPage review', () => {
  it('shows the ranked fair allocation after Recommend and passes axe', async () => {
    mockApi({
      'GET /api/auth/me': { body: session },
      'GET /api/conflicts/cf-demo-spectrum': { body: conflict },
      'POST /api/conflicts/cf-demo-spectrum/recommend': { body: recommended },
    });
    const { container } = renderAt('/conflicts/cf-demo-spectrum', '/conflicts/:id', <ConflictsPage/>);
    await userEvent.click(await screen.findByRole('button', { name: /Recommend fair allocation/ }));
    const table = await screen.findByRole('table', { name: 'Ranked allocation' });
    const rows = within(table).getAllByRole('row').slice(1);
    expect(rows).toHaveLength(3);
    expect(rows[0]).toHaveTextContent('Aarav Shetty');
    expect(rows[0]).toHaveTextContent('Assigned unit');
    expect(screen.getByRole('button', { name: 'Apply allocation' })).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });
});
