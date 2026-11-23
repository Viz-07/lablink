import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, post } from '../api/client';
import type { Equipment, Lab, User } from '../api/types';
import { Icon } from '../components/Icon';
import { Dialog, Empty, ErrorBox, Heading, Loading, Status } from '../components/ui';
import { CATEGORIES, CERTIFICATIONS, word } from '../format';
import { useAction, useApi, useAuth, useToast } from '../hooks';

function EquipmentForm({ item, labs, onClose, onSaved }: {item?: Equipment; labs: Lab[]; onClose: () => void; onSaved: () => void}) {
  const [specs, setSpecs] = useState<[string, string][]>(() => item ? Object.entries(item.specs) : [['', '']]);
  const [status, setStatus] = useState(item?.status || 'active');
  const action = useAction();

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const body = Object.fromEntries(data);
    const updated = await action.run(() => api<Equipment>(item ? '/admin/equipment/' + item.id : '/admin/equipment', {
      method: item ? 'PATCH' : 'POST', body: {
        ...body, required_training: body.required_training || null, units: Number(body.units),
        max_booking_minutes: Number(body.max_booking_minutes), weekly_limit_minutes_per_user: Number(body.weekly_limit_minutes_per_user),
        specs: Object.fromEntries(specs.filter(([key, value]) => key.trim() && value.trim())),
        capability_tags: String(body.capability_tags || '').split(',').map(tag => tag.trim()).filter(Boolean),
      },
    }));
    if (updated) onSaved();
  }
  return <Dialog title={item ? 'Edit equipment' : 'Add equipment'} onClose={onClose}>
    <form className="stack" onSubmit={save}>
      <ErrorBox error={action.error}/>
      <label>Name (required)<input name="name" required minLength={3} maxLength={120} defaultValue={item?.name}/></label>
      <label>Lab (required)<select name="lab_id" required defaultValue={item?.lab_id || ''}><option value="">Choose a lab</option>{labs.map(lab => <option value={lab.id} key={lab.id}>{lab.name}</option>)}</select></label>
      <div className="field-pair"><label>Category<select name="category" defaultValue={item?.category}>{CATEGORIES.map(key => <option value={key} key={key}>{word(key)}</option>)}</select></label>
        <label>Resource type<select name="kind" defaultValue={item?.kind}>{['equipment', 'dev_kit', 'workstation'].map(key => <option value={key} key={key}>{word(key)}</option>)}</select></label></div>
      <label>Description (required)<textarea name="description" required minLength={10} maxLength={500} rows={3} defaultValue={item?.description}/></label>
      <fieldset className="stack"><legend>Specifications</legend>
        {specs.map(([key, value], index) => <div className="spec-entry" key={index}>
          <label>Name<input maxLength={30} value={key} onChange={e => setSpecs(specs.map((entry, n) => n === index ? [e.target.value, value] : entry))}/></label>
          <label>Value<input maxLength={90} value={value} onChange={e => setSpecs(specs.map((entry, n) => n === index ? [key, e.target.value] : entry))}/></label>
          <button className="text-button" aria-label={'Remove specification ' + (index + 1)} type="button" onClick={() => setSpecs(specs.filter((_, n) => n !== index))}>Remove</button>
        </div>)}<button className="secondary" type="button" disabled={specs.length >= 10} onClick={() => setSpecs([...specs, ['', '']])}>Add specification</button>
      </fieldset>
      <label>Capability tags, separated by commas<input name="capability_tags" maxLength={600} defaultValue={item?.capability_tags.join(', ')}/></label>
      <div className="field-pair"><label>Approval mode<select name="approval_mode" defaultValue={item?.approval_mode}><option value="auto">Instant confirmation</option><option value="faculty">Faculty approval</option></select></label>
        <label>Training<select name="required_training" defaultValue={item?.required_training || ''}><option value="">None required</option>{CERTIFICATIONS.map(value => <option key={value} value={value}>{word(value)}</option>)}</select></label></div>
      <div className="field-pair"><label>Maximum minutes per booking<input name="max_booking_minutes" type="number" min={30} max={480} step={30} required defaultValue={item?.max_booking_minutes || 240}/></label>
        <label>Weekly minutes per user<input name="weekly_limit_minutes_per_user" type="number" min={30} max={2400} step={30} required defaultValue={item?.weekly_limit_minutes_per_user || 600}/></label></div>
      <div className="field-pair"><label>Unit count<input name="units" type="number" min={1} max={30} required defaultValue={item?.unit_ids.length || 1}/></label>
        <label>Status<select name="status" value={status} onChange={e => setStatus(e.target.value as Equipment['status'])}>{['active', 'maintenance', 'retired'].map(value => <option value={value} key={value}>{word(value)}</option>)}</select></label></div>
      {item?.status === 'active' && status !== 'active' && <p className="callout warning">Upcoming bookings will be moved to Needs action. All affected users will receive a notification.</p>}
      <div className="button-row end"><button className="secondary" type="button" onClick={onClose}>Cancel</button><button className="primary" disabled={action.pending}>{action.pending ? 'Saving…' : 'Save equipment'}</button></div>
    </form>
  </Dialog>;
}

function Certifications({ onClose }: {onClose: () => void}) {
  const users = useApi<User[]>('/admin/users');
  const [person, setPerson] = useState('');
  const [selected, setSelected] = useState<string[]>([]);
  const action = useAction();
  const toast = useToast();
  async function save() {
    const baseline = users.data?.find(u => u.id === person)?.certifications || [];
    const result = await action.run(() => post<User>('/admin/users/' + person + '/certifications', {
      add: selected.filter(item => !baseline.includes(item)), remove: baseline.filter(item => !selected.includes(item)),
    }));
    if (result) { toast('Certifications updated'); onClose(); }
  }
  return <Dialog title="Manage certifications" onClose={onClose}><div className="stack">
    <ErrorBox error={users.error || action.error}/><label>User<select value={person} onChange={e => {setPerson(e.target.value); setSelected(users.data?.find(user => user.id === e.target.value)?.certifications || []);}}><option value="">Choose a user</option>
      {users.data?.map(u => <option key={u.id} value={u.id}>{u.name}</option>)}</select></label>
    {person && <fieldset><legend>Current certifications</legend>{CERTIFICATIONS.map(cert => <label className="check-label" key={cert}><input type="checkbox" checked={selected.includes(cert)} onChange={e => setSelected(e.target.checked ? [...selected, cert] : selected.filter(item => item !== cert))}/>{word(cert)}</label>)}</fieldset>}
    <button className="primary" disabled={!person || action.pending} onClick={() => void save()}>Save certifications</button>
  </div></Dialog>;
}

export default function ManageEquipmentPage() {
  const inventory = useApi<Equipment[]>('/admin/equipment');
  const labs = useApi<Lab[]>('/labs');
  const [editing, setEditing] = useState<'new' | Equipment>();
  const [reset, setReset] = useState(false);
  const [training, setTraining] = useState(false);
  const [filter, setFilter] = useState('');
  const action = useAction();
  const auth = useAuth();
  const toast = useToast();
  const rows = inventory.data?.filter(item => item.name.toLowerCase().includes(filter.toLowerCase()));
  async function resetDemo() {
    const result = await action.run(() => post<{reset: boolean}>('/admin/demo/reset'));
    if (result?.reset) {setReset(false); inventory.reload(); toast('Demo data reset');}
  }
  return <>
    <Heading title="Manage equipment" subtitle="Keep the catalogue, capacity, and access requirements up to date." action={<button className="primary" onClick={() => setEditing('new')}><Icon name="plus" size={18}/> Add equipment</button>}/>
    <div className="button-row toolbar"><Link className="button secondary" to="/manage/audit">Audit log</Link><button className="secondary" onClick={() => setTraining(true)}>Certifications</button>
      {auth.session?.demo_mode && <button className="text-button" onClick={() => {action.clear(); setReset(true);}}>Reset demo data</button>}</div>
    <ErrorBox error={inventory.error || labs.error}/>{(inventory.loading || labs.loading) && <Loading/>}
    {rows && <section className="panel"><div className="section-heading"><div><h2>Campus inventory</h2><p>{rows.length} resources</p></div><label>Filter equipment<input type="search" value={filter} onChange={e => setFilter(e.target.value)}/></label></div>
      {!rows.length ? <Empty title="No equipment matches"/> : <div className="table-wrap" role="region" aria-label="Equipment inventory" tabIndex={0}><table><caption className="sr-only">Equipment inventory</caption>
      <thead><tr><th scope="col">Name</th><th scope="col">Lab</th><th scope="col">Category</th><th scope="col">Approval</th><th scope="col">Units</th><th scope="col">Status</th><th scope="col">Actions</th></tr></thead>
      <tbody>{rows.map(item => <tr key={item.id}><th scope="row">{item.name}</th><td>{labs.data?.find(lab => lab.id === item.lab_id)?.name}</td><td>{word(item.category)}</td><td>{item.approval_mode === 'auto' ? 'Instant' : 'Faculty'}</td>
      <td>{item.unit_ids.length}</td><td><Status value={item.status}/></td><td><button className="text-button" aria-label={'Edit ' + item.name} onClick={() => setEditing(item)}>Edit</button></td></tr>)}</tbody></table></div>}
    </section>}
    {editing && <EquipmentForm item={editing === 'new' ? undefined : editing} labs={labs.data || []} onClose={() => setEditing(undefined)} onSaved={() => {setEditing(undefined); inventory.reload(); toast('Equipment saved');}}/>}
    {training && <Certifications onClose={() => setTraining(false)}/>}
    {reset && <Dialog title="Reset all demo data?" onClose={() => setReset(false)}><p>Demo bookings, equipment changes, and project requests will be replaced by the initial demo records.</p><ErrorBox error={action.error}/>
      <div className="button-row end"><button className="secondary" onClick={() => setReset(false)}>Cancel</button><button className="destructive" disabled={action.pending} onClick={() => void resetDemo()}>Reset data</button></div></Dialog>}
  </>;
}

