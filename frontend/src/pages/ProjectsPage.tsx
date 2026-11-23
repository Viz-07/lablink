import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, post } from '../api/client';
import type { AccessRequest, EquipmentSummary, Grant, Named, Page, Project } from '../api/types';
import { Icon } from '../components/Icon';
import { Badge, Dialog, Empty, ErrorBox, Heading, Loading, Status } from '../components/ui';
import { date, hours, PROJECT_TYPES, today, word } from '../format';
import { useAction, useApi, useAuth, useToast } from '../hooks';

function ProjectForm({ project, onClose, onSaved }: { project?: Project; onClose: () => void; onSaved: () => void }) {
  const faculty = useApi<Named[]>('/faculty');
  const action = useAction();
  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const values = new FormData(event.currentTarget);
    const body = { title: values.get('title'), description: values.get('description'), type: values.get('type'),
      deadline: values.get('deadline') || null, supervisor_id: values.get('supervisor_id') || null };
    const result = await action.run(() => api<Project>(project ? '/projects/' + project.id : '/projects', { method: project ? 'PATCH' : 'POST', body }));
    if (result) onSaved();
  }
  return <Dialog title={project ? 'Edit project' : 'New project'} onClose={onClose}><form className="stack" onSubmit={save}>
    <ErrorBox error={action.error || faculty.error}/>
    <label>Title (required)<input name="title" required minLength={3} maxLength={120} defaultValue={project?.title}/></label>
    <div className="field-pair"><label>Project type<select name="type" defaultValue={project?.type || 'course_lab'}>{PROJECT_TYPES.map(value => <option key={value} value={value}>{word(value)}</option>)}</select></label>
      <label>Deadline<input name="deadline" type="date" min={today()} defaultValue={project?.deadline || ''}/></label></div>
    <label>Faculty supervisor<select name="supervisor_id" defaultValue={project?.supervisor_id || ''}><option value="">Select a supervisor</option>{faculty.data?.map(member => <option key={member.id} value={member.id}>{member.name}</option>)}</select></label>
    <label>Description (required)<textarea name="description" rows={4} required minLength={20} maxLength={2000} defaultValue={project?.description}/></label>
    <div className="button-row end"><button type="button" className="secondary" onClick={onClose}>Close</button><button className="primary" disabled={action.pending}>{action.pending ? 'Saving…' : 'Save project'}</button></div>
  </form></Dialog>;
}

export default function ProjectsPage() {
  const projects = useApi<Project[]>('/projects/mine');
  const requests = useApi<AccessRequest[]>('/access-requests/mine');
  const grants = useApi<Grant[]>('/access-grants/mine');
  const faculty = useApi<Named[]>('/faculty');
  const equipment = useApi<Page<EquipmentSummary>>('/equipment?limit=100');
  const auth = useAuth();
  const toast = useToast();
  const action = useAction();
  const [editing, setEditing] = useState<Project | 'new'>();
  const names = Object.fromEntries((equipment.data?.items || []).map(item => [item.id, item.name]));

  async function withdraw(request: AccessRequest) {
    const updated = await action.run(() => post<AccessRequest>('/access-requests/' + request.id + '/withdraw'));
    if (updated) { requests.reload(); toast('Access request withdrawn'); }
  }
  return <>
    <Heading title="Projects" subtitle="Keep your lab work, equipment access, and approvals in one place." action={<button className="primary" onClick={() => setEditing('new')}><Icon name="plus" size={18}/> New project</button>}/>
    <ErrorBox error={projects.error || requests.error || grants.error || faculty.error || equipment.error || action.error}/>
    {projects.loading && <Loading/>}
    {projects.data?.length === 0 && <Empty title="Start your first project"><p>Create a project to request equipment access or include it in a booking.</p><button className="primary" onClick={() => setEditing('new')}>Create project</button></Empty>}
    <div className="stack">{projects.data?.map(project => <article className="panel" key={project.id}>
      <div className="section-heading"><div><h2>{project.title}</h2><p>{project.deadline ? 'Due ' + date(project.deadline) : 'No deadline'} · {faculty.data?.find(item => item.id === project.supervisor_id)?.name || 'No supervisor assigned'}</p></div><Badge>{word(project.type)}</Badge></div>
      <p>{project.description}</p>
      {grants.data?.filter(g => g.project_id === project.id).map(grant => <div className="callout success" key={grant.id}>
        <strong>Approved access · {hours(grant.remaining_minutes)} of {hours(grant.minutes_quota)} remaining</strong><p>{grant.equipment_ids.map(id => names[id] || id).join(' · ')} · Until {date(grant.valid_until)}</p>
        <meter aria-label="Remaining access time" min={0} max={grant.minutes_quota} value={grant.remaining_minutes}/></div>)}
      {requests.data?.filter(r => r.project_id === project.id).map(request => <div className="request-line" key={request.id}>
        <div><strong>{request.equipment_ids.map(id => names[id] || id).join(' · ')}</strong><small>{request.hours_requested} h requested{request.reviewer_comment && ' · ' + request.reviewer_comment}</small></div>
        <Status value={request.status}/>{request.status === 'pending' && <button className="text-button" disabled={action.pending} onClick={() => void withdraw(request)}>Withdraw</button>}
      </div>)}
      <div className="button-row">
        <Link className="button primary" to={'/projects/new-request?project=' + project.id}>Request project access</Link>
        {project.owner_id === auth.session?.user.id && <button className="secondary" onClick={() => setEditing(project)}>Edit project</button>}
      </div>
    </article>)}</div>
    {editing && <ProjectForm project={editing === 'new' ? undefined : editing} onClose={() => setEditing(undefined)} onSaved={() => { setEditing(undefined); projects.reload(); toast('Project saved'); }}/>}
  </>;
}

