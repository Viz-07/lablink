import { useState } from 'react';
import { Link } from 'react-router-dom';
import { post } from '../api/client';
import type { Approval, Summary } from '../api/types';
import { Icon } from '../components/Icon';
import { AI, Badge, Empty, ErrorBox, Heading, Loading, Tabs, useFieldErrors } from '../components/ui';
import { date, range, word } from '../format';
import { useAction, useApi, useToast } from '../hooks';

function ApprovalCard({ item, onReviewed }: {item: Approval; onReviewed: () => void}) {
  const [comment, setComment] = useState('');
  const [quantity, setQuantity] = useState(item.hours);
  const [showSummary, setShowSummary] = useState(false);
  const [validation, setValidation] = useState<{ field: 'comment' | 'hours_approved'; message: string }>();
  const action = useAction();
  const { errorId, fieldProps } = useFieldErrors(action.error, { INVALID_QUOTA: ['hours_approved'] });
  const validationId = item.id + '-validation';
  const toast = useToast();
  const endpoint = '/approvals/' + item.type + '/' + item.id;
  const summary = useApi<Summary>(showSummary ? endpoint + '/summary' : undefined);

  async function review(approve: boolean) {
    setValidation(undefined);
    if (!approve && comment.trim().length < 5) {
      setValidation({ field: 'comment', message: 'Enter a comment of at least five characters before declining.' });
      return;
    }
    if (approve && item.type === 'access' && (quantity < 1 || quantity > item.hours || !Number.isInteger(quantity))) {
      setValidation({ field: 'hours_approved', message: 'Enter whole hours between 1 and the requested total.' });
      return;
    }
    const changed = await action.run(() => post<object>(endpoint + (approve ? '/approve' : '/decline'), { comment, ...(approve && item.type === 'access' ? { hours_approved: quantity } : {}) }));
    if (changed) { toast((approve ? 'Approved. ' : 'Declined. ') + item.requester + ' has been notified.'); onReviewed(); }
  }

  return <article className="panel approval-card">
    <div className="section-heading"><div><p className="eyebrow">{item.type === 'booking' ? 'Booking request' : 'Project access request'}</p><h2>{item.requester}</h2></div><Badge>{item.hours} h requested</Badge></div>
    <p><strong>{item.equipment.join(' · ')}</strong></p>
    <p className="muted">{item.project?.title || 'No linked project'} · {item.type === 'booking' ? range(item) : date(item.start) + ' to ' + date(item.end)}</p>
    <div className="badge-row">{item.flags.map(flag => <Badge tone="warning" key={flag.code}>{flag.message}</Badge>)}</div>
    <details><summary>Read full justification</summary><p>{item.justification}</p></details>
    <button className="secondary" onClick={() => setShowSummary(!showSummary)} aria-expanded={showSummary}><Icon name="spark" size={17}/>{showSummary ? 'Hide review summary' : 'Generate review summary'}</button>
    {showSummary && <div className="callout"><ErrorBox error={summary.error}/>{summary.loading && <Loading/>}{summary.data && <><AI source={summary.data.source}/><p>{summary.data.summary}</p><p><strong>Suggestion</strong> · {word(summary.data.recommendation)}</p></>}</div>}
    <div className="review-form"><label>Reviewer comment<textarea value={comment} onChange={e => setComment(e.target.value)} rows={2} maxLength={500} {...fieldProps('comment', undefined, validation?.field === 'comment' ? validationId : undefined)}/></label>
      {item.type === 'access' && <label>Hours to approve<input type="number" min={1} max={item.hours} value={quantity} onChange={event => setQuantity(Number(event.target.value))} {...fieldProps('hours_approved', undefined, validation?.field === 'hours_approved' ? validationId : undefined)}/></label>}
    </div>
    {validation && <p className="callout danger" id={validationId} role="alert">{validation.message}</p>}<ErrorBox error={action.error} id={errorId}/>
    <div className="button-row">{item.conflict_id ? <Link className="button primary" to={'/conflicts/' + item.conflict_id}>Review conflict</Link> :
      <button className="primary" disabled={action.pending} onClick={() => void review(true)}>Approve</button>}
      <button className="secondary" disabled={action.pending} onClick={() => void review(false)}>Decline</button></div>
  </article>;
}

export default function ApprovalsPage() {
  const [type, setType] = useState('all');
  const list = useApi<Approval[]>('/approvals');
  const shown = list.data?.filter(item => type === 'all' || item.type === type);
  const tabs = [['all', 'All requests'], ['booking', 'Bookings'], ['access', 'Project access']].map(([id, title]) => ({
    id: id!, label: title + (list.data ? ' (' + list.data.filter(item => id === 'all' || item.type === id).length + ')' : ''),
  }));
  return <>
    <Heading title="Approvals" subtitle="Review bookings and project access requests within your faculty scope."/>
    <Tabs label="Request type" tabs={tabs} active={type} onChange={setType}/>
    <section role="tabpanel" id="tab-results" aria-labelledby={'tab-' + type}><ErrorBox error={list.error}/>{list.loading && <Loading/>}
      {shown?.length === 0 && <Empty title="No pending requests"/>}
      <div className="stack">{shown?.map(item => <ApprovalCard item={item} key={item.id} onReviewed={list.reload}/>)}</div>
    </section>
  </>;
}

