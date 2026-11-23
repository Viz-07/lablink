import { useState, type FormEvent } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ApiError, post } from '../api/client';
import type { Availability, Booking, EquipmentDetail, Grant, Interval, Option, Project, Suggestion } from '../api/types';
import AvailabilityGrid from '../components/AvailabilityGrid';
import { Icon, categoryIcon } from '../components/Icon';
import { Alternatives, Badge, Dialog, ErrorBox, Heading, Loading, useFieldErrors } from '../components/ui';
import { date, hours, range, shiftDay, today, word } from '../format';
import { useAction, useApi, useToast } from '../hooks';

function BookingDialog({ item, interval, projects, grants, onClose, onBooked }: {
  item: EquipmentDetail; interval: Interval; projects: Project[]; grants: Grant[]; onClose: () => void; onBooked: (booking: Booking) => void;
}) {
  const [purpose, setPurpose] = useState('');
  const [project, setProject] = useState('');
  const [target, setTarget] = useState<Interval & {equipment_id: string; equipment_name: string}>({ ...interval, equipment_id: item.id, equipment_name: item.name });
  const action = useAction();
  const bookingErrors = useFieldErrors(action.error, { PROJECT_REQUIRED: ['project_id'] });
  const alternatives = action.error instanceof ApiError && Array.isArray(action.error.details.alternatives) ? action.error.details.alternatives as Option[] : [];
  const grant = grants.find(g => g.project_id === project && g.equipment_ids.includes(target.equipment_id) && g.valid_until >= target.start.slice(0, 10)
    && g.remaining_minutes >= (Date.parse(target.end) - Date.parse(target.start)) / 60_000);
  const needsProject = target.equipment_id === item.id && item.approval_mode === 'faculty';
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const booking = await action.run(() => post<Booking>('/bookings', {
      equipment_id: target.equipment_id, start: target.start, end: target.end,
      purpose: purpose.trim(), project_id: project || null,
    }));
    if (booking) onBooked(booking);
  }
  return <Dialog title="Review your booking" onClose={onClose}>
    <form onSubmit={submit} className="stack">
      <div className="callout"><strong>{target.equipment_name}</strong><p><time dateTime={target.start}>{range(target)}</time></p></div>
      <ErrorBox error={action.error} id={bookingErrors.errorId}/>
      {alternatives.length > 0 && <Alternatives options={alternatives} pending={action.pending} onAccept={option => { setTarget(option); action.clear(); }}/>}
      <label>Purpose (required)<textarea required minLength={5} maxLength={300} rows={3} value={purpose} onChange={event => setPurpose(event.target.value)} {...bookingErrors.fieldProps('purpose', 'purpose-count')} placeholder="What will you use this equipment for?"/></label>
      <small id="purpose-count">{300 - purpose.length} characters left</small>
      <label>Project {needsProject ? '(required)' : '(optional)'}<select {...bookingErrors.fieldProps('project_id')} required={needsProject} value={project} onChange={event => setProject(event.target.value)}><option value="">Select a project</option>{projects.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
      {needsProject && !projects.length && <Link to="/projects">Create a project</Link>}
      <p className="muted">{grant ? 'This booking can use your access grant.' : needsProject ? 'Faculty will review the request.' : 'The slot will be confirmed if capacity is available.'}</p>
      <div className="button-row end"><button className="secondary" onClick={onClose} type="button">Close</button><button className="primary" disabled={action.pending}>{action.pending ? 'Submitting…' : 'Submit booking'}</button></div>
    </form>
  </Dialog>;
}

export default function EquipmentDetailPage() {
  const { id } = useParams();
  const equipment = useApi<EquipmentDetail>('/equipment/' + id);
  const projects = useApi<Project[]>('/projects/mine');
  const grants = useApi<Grant[]>('/access-grants/mine');
  const toast = useToast();
  const [from, setFrom] = useState(today);
  const [duration, setDuration] = useState(60);
  const [before, setBefore] = useState('');
  const [period, setPeriod] = useState('');
  const [selected, setSelected] = useState<Interval>();
  const [booking, setBooking] = useState(false);
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const calendar = useApi<Availability>('/equipment/' + id + '/availability?from=' + from + '&days=7');
  const action = useAction();
  const slotErrors = useFieldErrors(action.error);
  const item = equipment.data;

  async function suggest(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const params = new URLSearchParams({ duration_minutes: String(duration) });
    if (before) params.set('latest', before);
    if (period) params.set('part_of_day', period);
    const answer = await action.run(async () => {
      const { api } = await import('../api/client');
      return api<{suggestions: Suggestion[]}>('/equipment/' + id + '/suggest-slots?' + params);
    });
    if (answer) { setSuggestions(answer.suggestions); if (!answer.suggestions.length) toast('No slots match these preferences.'); }
  }

  function week(step: number) { setFrom(shiftDay(from, step * 7)); setSelected(undefined); }
  if (equipment.loading) return <><Heading title="Equipment"/><Loading/></>;
  if (!item) return <><Heading title="Equipment"/><ErrorBox error={equipment.error}/><Link to="/discover">Back to discovery</Link></>;
  const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  return <>
    <nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/discover">Discover</Link><span>/</span><Link to={'/discover?department_id=' + item.department_id}>{item.department_id.toUpperCase()}</Link><span>/</span><span>{item.lab_name}</span></nav>
    <div className="detail-title"><div className={'category-icon large ' + item.category}><Icon name={categoryIcon(item.category)} size={30}/></div>
      <Heading title={item.name} subtitle={item.lab_name + ' · Room ' + item.lab.room + ' · ' + item.lab.building} action={item.high_demand && <Badge tone="warning">High demand</Badge>}/></div>
    <p className="detail-description">{item.description}</p>
    <div className="two-columns">
      <section className="panel"><h2>Specifications</h2><dl className="pairs">{Object.entries(item.specs).map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{value}</dd></div>)}</dl>
        <details><summary>Lab hours and accessibility</summary><ul className="plain">{weekdays.map((d, i) => <li key={d}>{d} · {item.lab.opening_hours[String(i)]?.map(w => w.open + '–' + w.close).join(', ') || 'Closed'}</li>)}</ul><p>{item.lab.accessibility_notes}</p></details></section>
      <section className="panel"><h2>Booking rules</h2><ul className="rule-list">
        <li>{item.approval_mode === 'auto' ? 'Instant booking when a unit is available' : 'Faculty approval or a valid project access grant'}</li>
        <li>{item.required_training ? 'Certification: ' + word(item.required_training) : 'No certification required'}</li>
        <li>{hours(item.max_booking_minutes)} per booking · {hours(item.weekly_limit_minutes_per_user)} per week</li>
        <li>{item.units} {item.units === 1 ? 'unit' : 'units'} available to reserve</li></ul>
        {item.eligibility.reasons.map(reason => <p className="callout warning" key={reason}>{reason}</p>)}
      </section>
    </div>
    <section className="panel availability-panel">
      <div className="section-heading"><div><h2 id="availability-title">Availability</h2><p>{date(from)} to {date(shiftDay(from, 6))}</p></div>
        <div className="button-row"><button className="secondary" disabled={from <= today()} onClick={() => week(-1)}>Previous week</button><button className="secondary" disabled={from >= shiftDay(today(), 7)} onClick={() => week(1)}>Next week</button></div></div>
      <form className="inline-form slot-finder" onSubmit={suggest}>
        <label>Duration<select {...slotErrors.fieldProps('duration_minutes')} value={duration} onChange={event => { setDuration(Number(event.target.value)); setSelected(undefined); setSuggestions([]); }}>{Array.from({length: item.max_booking_minutes / 30}, (_, i) => (i + 1) * 30).map(min => <option value={min} key={min}>{hours(min)}</option>)}</select></label>
        <label>By date<input {...slotErrors.fieldProps('latest')} type="date" min={today()} value={before} onChange={e => setBefore(e.target.value)}/></label>
        <label>Time of day<select {...slotErrors.fieldProps('part_of_day')} value={period} onChange={e => setPeriod(e.target.value)}><option value="">Any time</option><option value="morning">Morning</option><option value="afternoon">Afternoon</option><option value="evening">Evening</option></select></label>
        <button className="primary" disabled={action.pending || !item.eligibility.can_book}>{action.pending ? 'Checking…' : 'Suggest slots'}</button>
      </form>
      <ErrorBox error={action.error || calendar.error} id={slotErrors.errorId}/>
      {suggestions.length > 0 && <div className="slot-options" aria-live="polite">{suggestions.map(option => <button key={option.start} className="secondary" aria-pressed={option.start === selected?.start} onClick={() => setSelected(option)}>{range(option)}</button>)}</div>}
      {calendar.loading && <Loading/>}
      {calendar.data && <AvailabilityGrid key={from} days={calendar.data.days} selected={selected} onSelect={setSelected} duration={duration}/>}
      <button className="primary book-selection" disabled={!selected || !item.eligibility.can_book || projects.loading} onClick={() => setBooking(true)}>Book selected slot</button>
    </section>
    {booking && selected && <BookingDialog item={item} interval={selected} projects={projects.data || []} grants={grants.data || []} onClose={() => setBooking(false)} onBooked={entry => { setBooking(false); setSelected(undefined); setSuggestions([]); calendar.reload(); grants.reload(); toast('Booking request submitted · ' + word(entry.status)); }}/>}
  </>;
}

