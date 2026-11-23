import { useState } from 'react';
import { Link } from 'react-router-dom';
import { post } from '../api/client';
import type { Booking, Page } from '../api/types';
import { Icon } from '../components/Icon';
import { Alternatives, Dialog, Empty, ErrorBox, Heading, Loading, Score, Status, Tabs } from '../components/ui';
import { range } from '../format';
import { useAction, useApi, useToast } from '../hooks';

const tabs = [{id: 'upcoming', label: 'Upcoming'}, {id: 'action', label: 'Needs action'}, {id: 'past', label: 'Past'}];
export default function MyBookingsPage() {
  const [tab, setTab] = useState('upcoming');
  const [cursor, setCursor] = useState<string>();
  const [cancel, setCancel] = useState<Booking>();
  const list = useApi<Page<Booking>>('/bookings/mine?when=' + tab + (cursor ? '&cursor=' + cursor : ''));
  const action = useAction();
  const toast = useToast();

  async function update(path: string, body: unknown, message: string) {
    const updated = await action.run(() => post<Booking>(path, body));
    if (updated) { setCancel(undefined); list.reload(); toast(message); }
  }
  return <>
    <Heading title="My bookings" subtitle="Manage your reservations, approvals, and alternative slots." action={<Link className="button primary" to="/discover"><Icon name="plus" size={18}/> Find equipment</Link>}/>
    <Tabs label="Booking status" tabs={tabs} active={tab} onChange={value => { setTab(value); setCursor(undefined); action.clear(); }}/>
    <section role="tabpanel" id="tab-results" aria-labelledby={'tab-' + tab}>
      {!cancel && <ErrorBox error={action.error}/>}<ErrorBox error={list.error}/>
      {list.loading && <Loading/>}
      {list.data?.items.length === 0 && <Empty title={tab === 'action' ? 'No bookings need action' : 'No ' + tab + ' bookings'}><Link to="/discover">Discover equipment</Link></Empty>}
      <div className="stack">{list.data?.items.map(booking => <article className="panel booking-card" key={booking.id}>
        <div className="section-heading"><div><h2><Link to={'/equipment/' + booking.equipment_id}>{booking.equipment_name}</Link></h2><p>{booking.lab_name}</p></div><Status value={booking.status}/></div>
        <p className="location"><Icon name="calendar" size={18}/> <time dateTime={booking.start}>{range(booking)}</time></p>
        <p>{booking.purpose}</p>
        {booking.message && <p className="callout">{booking.message}</p>}
        {tab === 'action' && booking.status !== 'reallocated' && <p className="callout warning">This request is in the fair allocation queue. You’ll receive a notification after review.</p>}
        {booking.priority_snapshot && <Score score={booking.priority_snapshot}/>}
        {booking.status === 'reallocated' && <div className="callout"><h3>Alternative slots</h3><Alternatives options={booking.alternatives} pending={action.pending} onAccept={(_, index) => void update('/bookings/' + booking.id + '/accept-alternative', {index}, 'Alternative booked')}/></div>}
        {tab !== 'past' && Date.parse(booking.start) > Date.now() && <button className="secondary" onClick={() => { action.clear(); setCancel(booking); }}>Cancel booking</button>}
      </article>)}</div>
      {list.data?.next_cursor && <button className="secondary" onClick={() => setCursor(list.data?.next_cursor || undefined)}>Next page</button>}
      {cursor && <button className="secondary" onClick={() => setCursor(undefined)}>First page</button>}
    </section>
    {cancel && <Dialog title="Cancel this booking?" onClose={() => setCancel(undefined)}><p>{cancel.equipment_name} · {range(cancel)}</p><ErrorBox error={action.error}/><div className="button-row end"><button className="secondary" onClick={() => setCancel(undefined)}>Keep booking</button><button className="destructive" disabled={action.pending} onClick={() => void update('/bookings/' + cancel.id + '/cancel', {}, 'Booking cancelled')}>Cancel booking</button></div></Dialog>}
  </>;
}

