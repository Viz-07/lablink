import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { Day, Interval } from '../api/types';
import AvailabilityGrid from '../components/AvailabilityGrid';
import availability from './fixtures/availability.json';

const days = availability.days as Day[];

function Harness({ onSelect }: { onSelect: (value?: Interval) => void }) {
  const [selected, setSelected] = useState<Interval>();
  return <><h2 id="availability-title">Availability</h2>
    <AvailabilityGrid days={days} duration={30} selected={selected} onSelect={value => { setSelected(value); onSelect(value); }}/></>;
}

describe('AvailabilityGrid', () => {
  it('uses a roving tabindex and moves focus with arrow keys', () => {
    render(<Harness onSelect={() => {}}/>);
    const cells = screen.getAllByRole('gridcell').map(cell => cell.querySelector('button')!);
    expect(cells.filter(button => button.tabIndex === 0)).toHaveLength(1);
    const first = cells.find(button => button.tabIndex === 0)!;
    first.focus();
    fireEvent.keyDown(first, { key: 'ArrowDown' });
    expect(document.activeElement).not.toBe(first);
    expect((document.activeElement as HTMLButtonElement).tabIndex).toBe(0);
  });

  it('selects free slots and ignores closed or past ones', () => {
    const onSelect = vi.fn();
    render(<Harness onSelect={onSelect}/>);
    const buttons = screen.getAllByRole('gridcell').map(cell => cell.querySelector('button')!);
    const blocked = buttons.find(button => button.getAttribute('aria-disabled') === 'true')!;
    fireEvent.click(blocked);
    expect(onSelect).not.toHaveBeenCalled();
    const free = buttons.find(button => button.getAttribute('aria-disabled') === 'false')!;
    fireEvent.click(free);
    expect(onSelect).toHaveBeenCalledWith(expect.objectContaining({ start: expect.any(String), end: expect.any(String) }));
    expect(screen.getByRole('status')).toHaveTextContent('Selected slot');
  });

  it('describes every cell for screen readers and passes axe', async () => {
    const { container } = render(<Harness onSelect={() => {}}/>);
    const labelled = screen.getAllByRole('gridcell').map(cell => cell.querySelector('button')!.getAttribute('aria-label'));
    expect(labelled.every(Boolean)).toBe(true);
    expect(await axe(container)).toHaveNoViolations();
  });
});
