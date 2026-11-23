import { useEffect, useState } from 'react';
import { post } from '../api/client';
import type { Analytics, Department, Insights, Lab } from '../api/types';
import { Icon, type IconName } from '../components/Icon';
import { AI, Empty, ErrorBox, Heading, Loading } from '../components/ui';
import { useAction, useApi } from '../hooks';

const weekdays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const heatColors = ['var(--surface-2)', '#d5efea', '#a5ddd3', '#56ad9f', '#0b6e6e'];
type Row = Analytics['by_equipment'][number];

function Charts({ rows }: {rows: Row[]}) {
  const [table, setTable] = useState(false);
  const top = rows.slice(0, 8);
  const highest = top[0];
  const demandMax = Math.max(1, ...top.map(r => r.demand_ratio));
  return <section className="panel">
    <div className="section-heading"><div><h2>Utilisation by equipment</h2><p>Booked time as a share of opening hours and units.</p></div><button className="secondary" onClick={() => setTable(!table)}>{table ? 'Show chart' : 'Show as table'}</button></div>
    {table ? <div className="table-wrap" role="region" aria-label="Utilisation by equipment" tabIndex={0}><table><caption className="sr-only">Utilisation and demand for all equipment</caption><thead><tr><th scope="col">Equipment</th><th scope="col">Utilisation</th><th scope="col">Demand ratio</th><th scope="col">Bookings</th></tr></thead><tbody>{rows.map(row => <tr key={row.id}><th scope="row">{row.name}</th><td>{row.utilisation_pct}%</td><td>{row.demand_ratio.toFixed(2)}</td><td>{row.bookings}</td></tr>)}</tbody></table></div> :
      <div className="bar-chart" role="img" aria-label={highest ? 'Equipment utilisation and demand. Highest utilisation: ' + highest.name + ', ' + highest.utilisation_pct + '%.' : 'No bookings measured.'}>
        <div className="chart-legend"><span>Utilisation</span><span>Demand / capacity</span></div>
        {top.map(row => <div className="bar-row" key={row.id}><span>{row.name}</span><div>
          <svg aria-hidden="true" viewBox="0 0 100 5" preserveAspectRatio="none"><rect width="100" height="5" rx="1" fill="var(--surface-2)"/><rect width={Math.min(row.utilisation_pct, 100)} height="5" rx="1" fill="var(--primary)"/></svg><b>{row.utilisation_pct}%</b>
          <svg aria-hidden="true" viewBox="0 0 100 5" preserveAspectRatio="none"><rect width="100" height="5" rx="1" fill="var(--surface-2)"/><rect width={row.demand_ratio / demandMax * 100} height="5" rx="1" fill="#a47a36"/><path d={'M' + (100 / demandMax - .5) + ' 0v5'} stroke="var(--text)" strokeWidth=".6"/></svg><b>{row.demand_ratio.toFixed(2)}×</b>
        </div></div>)}
      </div>}
  </section>;
}

function Heatmap({ data }: {data: Analytics['heatmap']}) {
  const [table, setTable] = useState(false);
  const maximum = Math.max(1, ...data.cells.flat());
  return <section className="panel">
    <div className="section-heading"><div><h2>Busiest lab times</h2><p>Booking starts by weekday and hour in IST.</p></div><button className="secondary" onClick={() => setTable(!table)}>{table ? 'Show chart' : 'Show as table'}</button></div>
    <div className="table-wrap" role="region" aria-label="Hourly booking counts" tabIndex={0}>{table ?
      <table><caption>Booking starts by hour (IST)</caption><thead><tr><th scope="col">Day</th>{data.hours.map(hour => <th scope="col" key={hour}>{hour}:00</th>)}</tr></thead>
      <tbody>{data.cells.map((row, i) => <tr key={weekdays[i]}><th scope="row">{weekdays[i]}</th>{row.map((count, j) => <td key={j}>{count}</td>)}</tr>)}</tbody></table> :
      <svg className="heatmap" viewBox={'0 0 ' + (64 + data.hours.length * 55) + ' 248'} role="img" aria-label={'Booking starts by weekday and hour. Largest cell contains ' + Math.max(0, ...data.cells.flat()) + ' bookings.'}>
        {data.hours.map((hour, i) => <text key={hour} x={67 + i * 55} y={15}>{hour}:00</text>)}
        {data.cells.map((row, i) => <g key={weekdays[i]}><text x={5} y={44 + i * 30}>{weekdays[i]}</text>
          {row.map((count, j) => {
            const level = Math.ceil(count / maximum * 4);
            return <g key={j}><rect x={57 + j * 55} y={26 + i * 30} width={49} height={26} rx={4} fill={heatColors[level]}/>
              <text x={81 + j * 55} y={44 + i * 30} textAnchor="middle" className={level === 4 ? 'heat-white' : level > 0 ? 'heat-ink' : ''}>{count}</text></g>;
          })}</g>)}
      </svg>}</div>
  </section>;
}

export default function AnalyticsPage() {
  const [days, setDays] = useState(7);
  const [department, setDepartment] = useState('');
  const [lab, setLab] = useState('');
  const [insights, setInsights] = useState<Insights>();
  const action = useAction();
  const departments = useApi<Department[]>('/departments');
  const labs = useApi<Lab[]>('/labs');
  const params = new URLSearchParams({ range_days: String(days) });
  if (department) params.set('department_id', department);
  if (lab) params.set('lab_id', lab);
  const state = useApi<Analytics>('/analytics/overview?' + params);
  const data = state.data;
  useEffect(() => { setInsights(undefined); }, [days]);

  async function generate() {
    const result = await action.run(() => post<Insights>('/ai/insights', {range_days: days}));
    if (result) setInsights(result);
  }
  const tiles: [IconName, string, string | number][] = data ? [
    ['chart', 'Utilisation', data.kpis.utilisation_pct + '%'], ['calendar', 'Bookings', data.kpis.bookings],
    ['user', 'Students served', data.kpis.unique_students], ['balance', 'Contested', data.kpis.contested],
    ['clock', 'No-show rate', data.kpis.no_show_pct + '%'],
  ] : [];

  return <>
    <Heading title="Utilisation analytics" subtitle="See how lab capacity is used and where more time is needed."/>
    <div className="panel inline-form analytics-controls"><label>Date range<select value={days} disabled={action.pending} onChange={e => setDays(Number(e.target.value))}>{[7, 14, 30].map(n => <option key={n} value={n}>Last {n} days</option>)}</select></label>
      <label>Department<select value={department} onChange={e => {setDepartment(e.target.value); setLab('');}}><option value="">All departments</option>{departments.data?.filter(d => d.id !== 'central').map(d => <option value={d.id} key={d.id}>{d.name}</option>)}</select></label>
      <label>Lab<select value={lab} onChange={e => setLab(e.target.value)}><option value="">All labs</option>{labs.data?.filter(item => !department || item.department_id === department).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
    </div>
    <ErrorBox error={state.error || departments.error || labs.error}/>
    {state.loading && <Loading/>}
    {data && <div className="stack">
      <div className="tiles">{tiles.map(([icon, title, value]) => <div className="tile" key={title}><Icon name={icon} size={18}/><span>{title}</span><strong>{value}</strong></div>)}</div>
      <section className="panel insight-panel"><div className="section-heading"><div><h2><Icon name="spark" size={20}/> Utilisation insights</h2><p>Patterns and actions across labs you can review.</p></div>
        <button className="secondary" disabled={action.pending} onClick={() => void generate()}>{action.pending ? 'Generating…' : insights ? 'Refresh insights' : 'Generate insights'}</button></div>
        <ErrorBox error={action.error}/>
        {insights && <><AI source={insights.source}/>{!insights.insights.length && <p>No notable patterns were found in this range.</p>}<div className="insight-grid">{insights.insights.map(item => <article key={item.title + item.detail}><h3>{item.title}</h3><p>{item.detail}</p><p><strong>Action</strong> · {item.action}</p></article>)}</div></>}
      </section>
      {data.by_equipment.length > 0 ? <><Charts rows={data.by_equipment}/><Heatmap data={data.heatmap}/>
        <section className="panel"><h2>Under-used resources</h2><ul className="plain list-lines">{[...data.by_equipment].filter(row => row.utilisation_pct < 15).sort((a,b) => a.utilisation_pct - b.utilisation_pct).slice(0, 5).map(row => <li key={row.id}>{row.name}<strong>{row.utilisation_pct}%</strong></li>)}</ul></section></> :
        <Empty title="No equipment in this scope"><p>Try another lab or department.</p></Empty>}
    </div>}
  </>;
}

