import { useEffect, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { post } from '../api/client';
import type { Department, EquipmentSummary, Hit, Lab, Page, Search } from '../api/types';
import { Icon, categoryIcon } from '../components/Icon';
import { AI, Badge, Empty, ErrorBox, Heading, Loading, Status } from '../components/ui';
import { CATEGORIES, date, time, today, word } from '../format';
import { useAction, useApi } from '../hooks';

const examples = ['Measure 2.4 GHz antenna signals', 'GPU to train a vision model', '3D print a prototype'];

export function EquipmentCard({ item, hit }: { item: EquipmentSummary; hit?: Hit }) {
  return <article className="equipment-card">
    <div className="card-top"><div className={'category-icon ' + item.category}><Icon name={categoryIcon(item.category)} size={24}/></div>
      <span className="card-code">{item.department_id.toUpperCase()} <i/> {word(item.category)}</span></div>
    <h3><Link to={'/equipment/' + item.id}>{item.name}</Link></h3>
    <p className="location"><Icon name="pin" size={16}/> {item.lab_name}</p>
    <p className="spec-line">{Object.values(item.specs).slice(0, 2).join(' · ') || item.description}</p>
    <div className="badge-row">{item.status !== 'active' ? <Status value={item.status}/> : <Badge tone={item.approval_mode === 'auto' ? 'success' : 'warning'}>{item.approval_mode === 'auto' ? 'Instant booking' : 'Faculty approval'}</Badge>}
      {item.required_training && <Badge>{word(item.required_training)}</Badge>}{item.high_demand && <Badge>High demand</Badge>}</div>
    {hit && <details className="match"><summary>{hit.match}% match</summary><p>{hit.reason}</p></details>}
    <div className="card-bottom"><div><Icon name="clock" size={16}/><span>{item.next_free_slot ? <time dateTime={item.next_free_slot}>{date(item.next_free_slot)}, {time(item.next_free_slot)} IST</time> : 'No eligible slots'}<small>{item.units} {item.units === 1 ? 'unit' : 'units'}</small></span></div><Link className="book-link" to={'/equipment/' + item.id}>View &amp; book</Link></div>
  </article>;
}

export default function DiscoverPage() {
  const [filters, setFilters] = useSearchParams();
  const [query, setQuery] = useState(filters.get('q') || '');
  const [need, setNeed] = useState('');
  const [result, setResult] = useState<Search>();
  const [previous, setPrevious] = useState<string[]>([]);
  const [mobileFilters, showFilters] = useState(false);
  const action = useAction();
  const departments = useApi<Department[]>('/departments');
  const labs = useApi<Lab[]>('/labs');
  const searchParams = new URLSearchParams(filters);
  searchParams.set('limit', '12');
  const listing = useApi<Page<EquipmentSummary>>('/equipment?' + searchParams.toString());

  useEffect(() => {
    if (query === (filters.get('q') || '')) return;
    const timer = setTimeout(() => {
      setPrevious([]); setResult(undefined);
      setFilters(old => {
        const params = new URLSearchParams(old);
        params.delete('cursor');
        if (query.trim()) params.set('q', query.trim()); else params.delete('q');
        return params;
      }, { replace: true });
    }, 300);
    return () => clearTimeout(timer);
  }, [query, filters, setFilters]);

  function change(key: string, value: string) {
    setResult(undefined); setPrevious([]);
    const next = new URLSearchParams(filters);
    next.delete('cursor');
    if (value) next.set(key, value); else next.delete(key);
    if (key === 'department_id') next.delete('lab_id');
    setFilters(next);
  }
  function reset() { setQuery(''); setResult(undefined); setPrevious([]); setFilters({}); }
  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const response = await action.run(() => post<Search>('/ai/search', { query: need.trim() }));
    if (response) setResult(response);
  }
  const labChoices = (labs.data || []).filter(lab => !filters.get('department_id') || lab.department_id === filters.get('department_id'));
  const cards = result ? result.results.map(hit => <EquipmentCard key={hit.equipment.id} item={hit.equipment} hit={hit}/>) :
    listing.data?.items.map(item => <EquipmentCard item={item} key={item.id}/>);
  const count = result ? result.results.length : listing.data?.total;

  return <>
    <Heading title="Discover equipment" subtitle="Find and reserve specialist tools, development kits, and workstations across campus."/>
    <section className="ai-search" aria-labelledby="ai-title">
      <div className="search-decoration" aria-hidden="true"><i/><i/><i/></div>
      <div className="ai-search-heading"><div className="spark-tile"><Icon name="spark" size={21}/></div><div><h2 id="ai-title">Find equipment with AI</h2><p>Describe your project or what you need to do.</p></div></div>
      <form className="search-form" onSubmit={ask}><label className="sr-only" htmlFor="ai-query">Describe the equipment you need</label>
        <div><Icon name="search" size={18}/><input id="ai-query" required minLength={3} maxLength={300} value={need} onChange={event => setNeed(event.target.value)} placeholder="e.g. I need to capture 2.4 GHz signals for my antenna project"/></div>
        <button type="submit" disabled={action.pending}><Icon name="spark" size={17}/>{action.pending ? 'Searching…' : 'Ask AI'}</button>
      </form>
      <div className="examples"><span>Try:</span>{examples.map(example => <button type="button" key={example} onClick={() => setNeed(example)}>{example}</button>)}</div>
    </section>
    <ErrorBox error={action.error}/>
    <div className="catalogue"><aside className="filters panel"><div className="filter-title"><h2><Icon name="settings" size={18}/> Filters</h2><button className="text-button" onClick={reset}>Reset</button><button className="text-button filter-toggle" aria-expanded={mobileFilters} aria-controls="filter-fields" onClick={() => showFilters(!mobileFilters)}>{mobileFilters ? 'Hide' : 'Show'}</button></div>
      <div id="filter-fields" className={'filter-fields ' + (mobileFilters ? 'open' : '')}>
        <label>Search equipment<input type="search" placeholder="Equipment name" maxLength={100} value={query} onChange={e => setQuery(e.target.value)}/></label>
        <label>Department<select value={filters.get('department_id') || ''} onChange={e => change('department_id', e.target.value)}><option value="">All departments</option>{departments.data?.filter(d => d.id !== 'central').map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
        <label>Category<select value={filters.get('category') || ''} onChange={e => change('category', e.target.value)}><option value="">All categories</option>{CATEGORIES.map(value => <option value={value} key={value}>{word(value)}</option>)}</select></label>
        <label>Lab<select value={filters.get('lab_id') || ''} onChange={e => change('lab_id', e.target.value)}><option value="">All labs</option>{labChoices.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}</select></label>
        <label>Resource type<select value={filters.get('kind') || ''} onChange={e => change('kind', e.target.value)}><option value="">All resource types</option><option value="equipment">Equipment</option><option value="dev_kit">Development kits</option><option value="workstation">Workstations</option></select></label>
        <label>Available on<input type="date" min={today()} value={filters.get('available_on') || ''} onChange={e => change('available_on', e.target.value)}/></label>
        <label className="check-label"><input type="checkbox" checked={filters.get('no_training') === 'true'} onChange={e => change('no_training', e.target.checked ? 'true' : '')}/> Only equipment I can use</label>
      </div><ErrorBox error={departments.error || labs.error}/></aside>
      <section className="results" aria-labelledby="results-title"><div className="section-heading"><div><h2 id="results-title">{result ? 'Suggested equipment' : 'Equipment catalogue'}</h2><p role="status">{count !== undefined ? count + (count === 1 ? ' item' : ' items') : 'Loading equipment…'}</p></div>
        {result && <button className="secondary" onClick={() => setResult(undefined)}>Clear suggestions</button>}</div>
        {result && <p className="callout"><AI source={result.source}/> {result.source === 'fallback' ? 'Showing keyword matches for' : 'Interpreted need:'} {result.interpreted}</p>}
        {!result && <ErrorBox error={listing.error}/>}
        {!result && listing.loading && <Loading/>}
        {cards?.length ? <div className="equipment-grid">{cards}</div> : cards && <Empty title="No matching equipment"><button className="secondary" onClick={reset}>Reset filters</button></Empty>}
        {!result && listing.data && (previous.length > 0 || listing.data.next_cursor) && <div className="pagination">
          <button className="secondary" disabled={!previous.length} onClick={() => { const next = new URLSearchParams(filters); const cursor = previous[previous.length - 1]; if (cursor) next.set('cursor', cursor); else next.delete('cursor'); setPrevious(previous.slice(0, -1)); setFilters(next); }}>Previous</button>
          <span>Page {previous.length + 1}</span><button className="secondary" disabled={!listing.data.next_cursor} onClick={() => { const cursor = listing.data?.next_cursor; if (!cursor) return; const next = new URLSearchParams(filters); setPrevious([...previous, filters.get('cursor') || '']); next.set('cursor', cursor); setFilters(next); }}>Next</button>
        </div>}
      </section>
    </div>
  </>;
}

