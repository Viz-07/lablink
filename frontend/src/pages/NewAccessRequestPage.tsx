import { useEffect, useId, useRef, useState, type FormEvent } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { post } from '../api/client';
import type { AccessRequest, Draft, EquipmentSummary, Page, Project } from '../api/types';
import { Icon } from '../components/Icon';
import { AI, Empty, ErrorBox, Heading, Loading, useFieldErrors } from '../components/ui';
import { date, today, word } from '../format';
import { useAction, useApi, useAuth } from '../hooks';

const steps = ['Equipment', 'Details', 'Review'];
export default function NewAccessRequestPage() {
  const [params] = useSearchParams();
  const [step, setStep] = useState(0);
  const [projectId, setProjectId] = useState(params.get('project') || '');
  const [selection, setSelection] = useState<string[]>([]);
  const [filter, setFilter] = useState('');
  const [quantity, setQuantity] = useState(4);
  const [start, setStart] = useState(today);
  const [end, setEnd] = useState(today);
  const [notes, setNotes] = useState('');
  const [draft, setDraft] = useState<Draft>();
  const [done, setDone] = useState(false);
  const [validation, setValidation] = useState<{ fields: string[]; message: string }>();
  const validationId = useId();
  const stepTitle = useRef<HTMLHeadingElement>(null);
  const projects = useApi<Project[]>('/projects/mine');
  const equipment = useApi<Page<EquipmentSummary>>('/equipment?limit=100');
  const action = useAction();
  const { errorId, fieldProps } = useFieldErrors(action.error, {
    INVALID_DATES: ['needed_from', 'needed_until'],
    AFTER_DEADLINE: ['needed_until'],
  });
  const { session } = useAuth();
  const project = projects.data?.find(item => item.id === projectId);
  const all = equipment.data?.items.filter(item => item.status === 'active') || [];
  const found = all.filter(e => (e.name + ' ' + e.lab_name + ' ' + e.capability_tags.join(' ')).toLowerCase().includes(filter.toLowerCase()));
  const selected = all.filter(item => selection.includes(item.id));

  function validationProps(name: string) {
    return fieldProps(name, undefined, validation?.fields.includes(name) ? validationId : undefined);
  }

  useEffect(() => { if (step > 0) stepTitle.current?.focus(); }, [step]);
  function toggle(id: string) { setSelection(ids => ids.includes(id) ? ids.filter(i => i !== id) : ids.length < 5 ? [...ids, id] : ids); }
  async function generate() {
    if (!project) { setValidation({ fields: ['project_id'], message: 'Choose a project first.' }); return; }
    setValidation(undefined);
    const result = await action.run(() => post<Draft>('/ai/draft-access-request', {project_id: projectId, equipment_ids: selection}));
    if (result) setDraft(result);
  }
  async function next(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidation(undefined);
    if (step === 0 && (!project || !selection.length)) {
      const fields = [...(!project ? ['project_id'] : []), ...(!selection.length ? ['equipment_ids'] : [])];
      setValidation({ fields, message: 'Choose a project and at least one item.' });
      return;
    }
    if (step === 1) {
      const datesInvalid = end < start || Boolean(project?.deadline && end > project.deadline);
      const fields = [...(datesInvalid ? ['needed_until'] : []), ...(notes.trim().length < 30 ? ['justification'] : [])];
      if (fields.length) {
        setValidation({ fields, message: 'Check your dates and enter a justification of at least 30 characters.' });
        return;
      }
    }
    if (step < 2) { setStep(step + 1); return; }
    const result = await action.run(() => post<AccessRequest>('/access-requests', {
      project_id: projectId, equipment_ids: selection, hours_requested: quantity, needed_from: start, needed_until: end, justification: notes,
    }));
    if (result) setDone(true);
  }

  if (done) return <><Heading title="Request submitted" subtitle="Your access request is available for faculty review."/><Link className="button primary" to="/projects">Back to projects</Link></>;
  return <>
    <nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/projects">Projects</Link><span>/</span><span>New access request</span></nav>
    <Heading title="Request project access" subtitle="Request shared lab time for a specific project."/>
    <ErrorBox error={projects.error || equipment.error}/>
    {(projects.loading || equipment.loading) && <Loading/>}
    {projects.data?.length === 0 && <Empty title="Create a project first"><Link className="button primary" to="/projects">Go to projects</Link></Empty>}
    {!!projects.data?.length && <div className="wizard">
      <ol className="steps">{steps.map((item, index) => <li key={item} aria-current={index === step ? 'step' : undefined}><b>{index + 1}</b>{item}</li>)}</ol>
      <form className="panel stack" onSubmit={next}>
        <h2 ref={stepTitle} tabIndex={-1}>{steps[step]}</h2><ErrorBox error={action.error} id={errorId}/>{validation && <p className="callout danger" role="alert" id={validationId}>{validation.message}</p>}
        {step === 0 && <>
          <label>Project (required)<select value={projectId} required onChange={e => {setProjectId(e.target.value); setDraft(undefined);}} {...validationProps('project_id')}><option value="">Select a project</option>{projects.data.map(p => <option key={p.id} value={p.id}>{p.title}</option>)}</select></label>
          <div className="button-row"><button type="button" className="secondary" disabled={action.pending} onClick={() => void generate()}><Icon name="spark" size={17}/>{action.pending ? 'Checking…' : 'Suggest equipment'}</button></div>
          {draft && <div className="callout"><AI source={draft.source}/><ul className="plain suggestions">{draft.suggested_equipment.flatMap(hit => {
            const item = all.find(e => e.id === hit.equipment_id);
            return item ? [<li key={item.id}><button className="secondary" type="button" aria-pressed={selection.includes(item.id)} onClick={() => toggle(item.id)}>{item.name}</button><p>{hit.reason}</p></li>] : [];
          })}</ul></div>}
          <label>Filter the catalogue<input type="search" value={filter} onChange={e => setFilter(e.target.value)} placeholder="Name, lab or capability"/></label>
          <fieldset {...validationProps('equipment_ids')}><legend>Select up to five items · {selection.length} selected</legend><div className="check-catalogue">{found.map(item => <label key={item.id} className="check-label">
            <input type="checkbox" checked={selection.includes(item.id)} disabled={selection.length >= 5 && !selection.includes(item.id)} onChange={() => toggle(item.id)}/>
            <span>{item.name}<small>{item.lab_name}{item.required_training && ' · ' + word(item.required_training) + (session?.user.certifications.includes(item.required_training) ? ' held' : ' required')}</small></span>
          </label>)}{!found.length && <p>No equipment matches.</p>}</div></fieldset>
          {selected.length > 0 && <div className="button-row">{selected.map(item => <button className="secondary" key={item.id} type="button" aria-label={'Remove ' + item.name} onClick={() => toggle(item.id)}>{item.name} ×</button>)}</div>}
        </>}
        {step === 1 && <>
          <label>Hours needed (required)<input type="number" required min={1} max={60} value={quantity} onChange={e => setQuantity(Number(e.target.value))} {...validationProps('hours_requested')}/></label>
          <div className="field-pair"><label>Needed from (required)<input type="date" min={today()} max={project?.deadline || undefined} required value={start} onChange={e => {setStart(e.target.value); if (end < e.target.value) setEnd(e.target.value);}} {...validationProps('needed_from')}/></label>
          <label>Needed until (required)<input type="date" min={start} max={project?.deadline || undefined} required value={end} onChange={e => setEnd(e.target.value)} {...validationProps('needed_until')}/></label></div>
          <label>Justification (required)<textarea value={notes} onChange={e => setNotes(e.target.value)} rows={5} required minLength={30} maxLength={2000} {...validationProps('justification')}/></label>
          <div className="button-row"><button type="button" className="secondary" disabled={action.pending} onClick={() => void generate()}><Icon name="spark" size={17}/>{action.pending ? 'Generating…' : 'Draft justification'}</button></div>
          {draft && <div className="callout"><AI source={draft.source}/><p>{draft.justification}</p><p>Estimated time: {draft.estimated_hours} h</p><ul>{draft.checklist.map(item => <li key={item}>{item}</li>)}</ul>
            <button className="secondary" type="button" onClick={() => setNotes(draft.justification)}>Use this draft</button><p className="muted">Review and edit the draft before submitting.</p></div>}
        </>}
        {step === 2 && <dl className="pairs"><div><dt>Project</dt><dd>{project?.title}</dd></div><div><dt>Equipment</dt><dd>{selected.map(item => item.name).join(', ')}</dd></div>
          <div><dt>Access window</dt><dd>{date(start)} to {date(end)} · {quantity} h</dd></div><div><dt>Justification</dt><dd>{notes}</dd></div></dl>}
        <div className="button-row end">{step > 0 && <button className="secondary" type="button" onClick={() => {setStep(step - 1); setValidation(undefined);}}>Back</button>}
          <button className="primary" disabled={action.pending}>{step < 2 ? 'Continue' : action.pending ? 'Submitting…' : 'Submit request'}</button></div>
      </form>
    </div>}
  </>;
}

