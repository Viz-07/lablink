import { useId, useState, type KeyboardEvent } from 'react';
import type { Day, Interval, Slot } from '../api/types';
import { date, range, time } from '../format';

const marks = { free: '○', partial: '◐', full: '×', closed: '–', past: '–', mine: '★', outside_horizon: '–' };
function slotLabel(slot: Slot) {
  if (selectable(slot)) return slot.free_units + ' of ' + slot.total_units + ' units free';
  return slot.state === 'outside_horizon' ? 'outside the booking window' : slot.state;
}
export function selectable(slot: Slot) { return slot.state === 'free' || slot.state === 'partial'; }

export default function AvailabilityGrid({ days, selected, onSelect, duration }: {
  days: Day[]; selected?: Interval; onSelect: (value?: Interval) => void; duration: number;
}) {
  const id = useId();
  const [active, setActive] = useState<[number, number]>([0, 0]);
  const [anchor, setAnchor] = useState<[number, number]>();
  const [list, setList] = useState(() => window.matchMedia('(max-width: 640px)').matches);
  const rowCount = days[0]?.slots.length || 0;

  function pick(row: number, col: number, extend = false) {
    const day = days[col];
    const slot = day?.slots[row];
    if (!day || !slot || !selectable(slot)) return;
    const initial = extend && anchor?.[1] === col ? anchor[0] : row;
    const first = Math.min(initial, row), last = extend ? Math.max(initial, row) + 1 : row + duration / 30;
    const chosen = day.slots.slice(first, last);
    if (chosen.length !== last - first || chosen.some(cell => !selectable(cell))) return;
    const start = chosen[0], end = chosen[chosen.length - 1];
    if (start && end) { setAnchor([initial, col]); onSelect({ start: start.start, end: end.end }); }
  }

  function key(event: KeyboardEvent, row: number, col: number) {
    let nextRow = row, nextCol = col;
    switch (event.key) {
      case 'ArrowDown': nextRow++; break;
      case 'ArrowUp': nextRow--; break;
      case 'ArrowLeft': case 'PageUp': nextCol--; break;
      case 'ArrowRight': case 'PageDown': nextCol++; break;
      case 'Home': nextRow = 0; break;
      case 'End': nextRow = rowCount - 1; break;
      case 'Escape': event.preventDefault(); onSelect(); setAnchor(undefined); return;
      default: return;
    }
    event.preventDefault();
    nextRow = Math.min(rowCount - 1, Math.max(0, nextRow));
    nextCol = Math.min(days.length - 1, Math.max(0, nextCol));
    setActive([nextRow, nextCol]);
    document.getElementById(id + '-' + nextRow + '-' + nextCol)?.focus();
    if (event.shiftKey && nextCol === col && (event.key === 'ArrowDown' || event.key === 'ArrowUp')) pick(nextRow, nextCol, true);
  }

  return <>
    <div className="grid-toolbar"><p>Times shown in IST</p><button className="secondary" type="button" onClick={() => setList(!list)}><span>{list ? 'Grid view' : 'List view'}</span></button></div>
    {list ? <div className="slot-list">{days.map((day, col) => {
      const available = day.slots.filter((_, row) => {
        const cells = day.slots.slice(row, row + duration / 30);
        return cells.length === duration / 30 && cells.every(selectable);
      });
      return <details key={day.date} open={col === 0 && available.length > 0}><summary>{date(day.date)} · {available.length} start times</summary>
        {available.length ? <div className="slot-options">{available.map(slot => <button className="secondary" type="button" key={slot.start} aria-pressed={selected?.start === slot.start} onClick={() => pick(day.slots.indexOf(slot), col)}>{time(slot.start)}</button>)}</div> : <p>No available slots for this duration.</p>}
      </details>;
    })}</div> : <>
      <p id={id + '-help'} className="muted">Use arrow keys to move, Enter to select, and Shift with the up or down arrow to extend.</p>
      <div className="table-wrap schedule" role="region" aria-label="Scrollable availability calendar">
        <table role="grid" aria-labelledby="availability-title" aria-describedby={id + '-help'} aria-rowcount={rowCount + 1} aria-colcount={days.length + 1}>
          <thead><tr><th scope="col">Time</th>{days.map(day => <th scope="col" key={day.date}><time dateTime={day.date}>{date(day.date)}</time></th>)}</tr></thead>
          <tbody>{Array.from({ length: rowCount }, (_, row) => <tr key={row}>
            <th scope="row">{time(days[0]?.slots[row]?.start || '')}</th>
            {days.map((day, col) => {
              const slot = day.slots[row];
              if (!slot) return <td key={day.date}/>;
              const chosen = Boolean(selected && slot.start >= selected.start && slot.end <= selected.end);
              return <td key={day.date} role="gridcell" aria-selected={chosen}><button
                id={id + '-' + row + '-' + col} type="button" className={'slot ' + slot.state}
                aria-disabled={!selectable(slot)} tabIndex={active[0] === row && active[1] === col ? 0 : -1}
                aria-label={range(slot) + ', ' + slotLabel(slot)}
                onFocus={() => setActive([row, col])} onKeyDown={event => key(event, row, col)}
                onClick={event => pick(row, col, event.shiftKey)}>{chosen ? '✓' : marks[slot.state]}</button></td>;
            })}
          </tr>)}</tbody>
        </table>
      </div>
      <div className="legend"><span>○ Free</span><span>◐ Partly booked</span><span>× Full</span><span>★ My booking</span><span>– Closed, past, or outside the booking window</span></div>
    </>}
    <div className="selection" role="status">{selected ? <><strong>Selected slot</strong><time dateTime={selected.start}>{range(selected)}</time><button type="button" className="text-button" onClick={() => { onSelect(); setAnchor(undefined); }}>Clear selection</button></> : 'Select a start time or choose a suggested slot.'}</div>
  </>;
}

