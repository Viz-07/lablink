import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { post } from '../api/client';
import type { Conflict } from '../api/types';
import { Icon } from '../components/Icon';
import {
  AI,
  Badge,
  Dialog,
  Empty,
  ErrorBox,
  Heading,
  Loading,
  Score,
  Status,
  Tabs,
  useFieldErrors,
} from '../components/ui';
import { range, word } from '../format';
import { useAction, useApi, useAuth, useToast } from '../hooks';

const tabs = [
  { id: 'open', label: 'Open' },
  { id: 'resolved', label: 'Resolved' },
];
const windowLabel = (item: Conflict) => range({ start: item.window_start, end: item.window_end });

type ConflictAction =
  | { kind: 'recommend'; payload?: never }
  | { kind: 'apply'; payload: { overrides: { promote: string; demote: string; reason: string }[] } }
  | { kind: 'dismiss'; payload: { reason: string } };

const successMessages = {
  apply: 'Allocation applied and students notified.',
  dismiss: 'Conflict dismissed.',
};

function List() {
  const [status, setStatus] = useState('open');
  const list = useApi<Conflict[]>('/conflicts?status=' + status);
  return (
    <>
      <Heading
        title="Conflict center"
        subtitle="Review competing booking requests and assign scarce slots using transparent priorities."
      />
      <Tabs label="Conflict status" tabs={tabs} active={status} onChange={setStatus} />
      <section role="tabpanel" id="tab-results" aria-labelledby={'tab-' + status}>
        <ErrorBox error={list.error} />
        {list.loading && <Loading />}
        {list.data?.length === 0 && <Empty title={'No ' + status + ' conflicts'} />}
        <div className="stack">
          {list.data?.map((item) => (
            <article className="panel conflict-card" key={item.id}>
              <div className="category-icon">
                <Icon name="balance" size={25} />
              </div>
              <div>
                <h2>
                  <Link to={'/conflicts/' + item.id}>{item.equipment_name}</Link>
                </h2>
                <p>
                  {item.lab_name} · {windowLabel(item)}
                </p>
                <div className="badge-row">
                  <Badge tone="warning">
                    {item.n_requests} requests · {item.capacity} {item.capacity === 1 ? 'unit' : 'units'}
                  </Badge>
                  <Status value={item.status} />
                </div>
              </div>
              <Link className="button secondary" to={'/conflicts/' + item.id}>
                Review conflict
              </Link>
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

function Review({ id }: { id: string }) {
  const record = useApi<Conflict>('/conflicts/' + id);
  const [changed, setChanged] = useState<Conflict>();
  const [showApply, setShowApply] = useState(false);
  const [showDismiss, setShowDismiss] = useState(false);
  const [promote, setPromote] = useState('');
  const [demote, setDemote] = useState('');
  const [reason, setReason] = useState('');
  const action = useAction();
  const { errorId, fieldProps } = useFieldErrors(action.error, {
    BAD_OVERRIDE: ['overrides.0.promote', 'overrides.0.demote'],
  });
  const toast = useToast();
  const auth = useAuth();
  const item = changed || record.data;
  const rows = item?.recommendation;

  async function send({ kind, payload }: ConflictAction) {
    const result = await action.run(() => post<Conflict>('/conflicts/' + id + '/' + kind, payload));
    if (!result) return;
    setChanged(result);
    setShowApply(false);
    setShowDismiss(false);
    if (kind !== 'recommend') toast(successMessages[kind]);
  }
  if (!item)
    return (
      <>
        <Heading title="Review conflict" />
        <ErrorBox error={record.error} />
        {record.loading && <Loading />}
      </>
    );
  const winners = rows?.filter((row) => row.unit_id) || [];
  const losers = rows?.filter((row) => !row.unit_id) || [];
  const eligibleAlternatives = losers.filter((row) => row.reason === 'CAPACITY');
  const requests = rows ?? item.requests ?? [];
  return (
    <>
      <nav className="breadcrumbs" aria-label="Breadcrumb">
        <Link to="/conflicts">Conflict center</Link>
        <span>/</span>
        <span>Review</span>
      </nav>
      <Heading
        title={item.equipment_name}
        subtitle={item.lab_name + ' · ' + windowLabel(item)}
        action={<Status value={item.status} />}
      />
      <div className="callout conflict-context">
        <Icon name="balance" size={24} />
        <span>
          <strong>{item.n_requests} competing requests</strong>
          <br />
          {item.capacity} {item.capacity === 1 ? 'unit' : 'units'} available in this window
        </span>
      </div>
      {!showApply && !showDismiss && <ErrorBox error={action.error} />}
      {item.status === 'open' && (
        <div className="button-row toolbar">
          <button
            className="primary"
            disabled={action.pending}
            onClick={() => void send({ kind: 'recommend' })}
          >
            <Icon name="spark" size={17} />
            {action.pending ? 'Evaluating…' : rows ? 'Refresh recommendation' : 'Recommend fair allocation'}
          </button>
          {rows && (
            <button
              className="secondary"
              onClick={() => {
                action.clear();
                setShowApply(true);
              }}
            >
              Apply allocation
            </button>
          )}
          {auth.session?.user.role === 'lab_admin' && (
            <button
              className="text-button"
              onClick={() => {
                setReason('');
                action.clear();
                setShowDismiss(true);
              }}
            >
              Dismiss conflict
            </button>
          )}
        </div>
      )}
      {item.status === 'resolved' && (
        <p className="callout success" role="status">
          {winners.length} confirmed · {losers.length} offered alternative options
        </p>
      )}
      {item.ai_explanation && (
        <div className="callout">
          <AI source={item.explanation_source || 'fallback'} />
          <p>{item.ai_explanation}</p>
          <details>
            <summary>How it was generated</summary>
            <p>
              The explanation describes a deterministic schedule. The reviewer applies the final allocation.
            </p>
          </details>
        </div>
      )}
      <section className="panel">
        <h2>{rows ? 'Ranked allocation' : 'Competing requests'}</h2>
        <div className="table-wrap" role="region" aria-label="Conflict requests" tabIndex={0}>
          <table>
            <caption className="sr-only">{rows ? 'Ranked allocation' : 'Competing requests'}</caption>
            <thead>
              <tr>
                {rows && <th scope="col">Rank</th>}
                <th scope="col">Student</th>
                <th scope="col">Project</th>
                <th scope="col">Priority</th>
                {rows && <th scope="col">Outcome</th>}
              </tr>
            </thead>
            <tbody>
              {requests.map((row, index) => (
                <tr key={row.booking_id}>
                  {rows && <td>{index + 1}</td>}
                  <th scope="row">{row.student}</th>
                  <td>{row.project || 'No linked project'}</td>
                  <td>
                    <strong>{row.breakdown.score.toFixed(4)}</strong>
                    <Score score={row.breakdown} />
                  </td>
                  {'unit_id' in row && (
                    <td>
                      <AllocationOutcome row={row} />
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {Object.keys(item.messages).length > 0 && (
        <details className="panel">
          <summary>Preview student messages</summary>
          <dl className="pairs">
            {rows?.map((row) => (
              <div key={row.booking_id}>
                <dt>{row.student}</dt>
                <dd>{item.messages[row.booking_id]}</dd>
              </div>
            ))}
          </dl>
        </details>
      )}
      {showApply && (
        <Dialog title="Apply this allocation?" onClose={() => setShowApply(false)}>
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              void send({
                kind: 'apply',
                payload: { overrides: promote && demote ? [{ promote, demote, reason }] : [] },
              });
            }}
          >
            <p>
              {winners.length} bookings will be confirmed and {losers.length} students will be notified of the
              remaining options.
            </p>
            <ErrorBox error={action.error} id={errorId} />
            {winners.length > 0 && eligibleAlternatives.length > 0 && (
              <details>
                <summary>Adjust an outcome</summary>
                <div className="stack">
                  <label>
                    Assign a slot to
                    <select
                      value={promote}
                      onChange={(e) => {
                        setPromote(e.target.value);
                        if (!e.target.value) setDemote('');
                      }}
                      {...fieldProps('overrides.0.promote')}
                    >
                      <option value="">Use recommendation</option>
                      {eligibleAlternatives.map((row) => (
                        <option key={row.booking_id} value={row.booking_id}>
                          {row.student}
                        </option>
                      ))}
                    </select>
                  </label>
                  {promote && (
                    <>
                      <label>
                        Student who receives alternatives (required)
                        <select
                          required
                          value={demote}
                          onChange={(e) => setDemote(e.target.value)}
                          {...fieldProps('overrides.0.demote')}
                        >
                          <option value="">Choose student</option>
                          {winners.map((row) => (
                            <option key={row.booking_id} value={row.booking_id}>
                              {row.student}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Reason (required)
                        <textarea
                          minLength={10}
                          maxLength={500}
                          required
                          value={reason}
                          onChange={(e) => setReason(e.target.value)}
                          {...fieldProps('overrides.0.reason')}
                        />
                      </label>
                    </>
                  )}
                </div>
              </details>
            )}
            <div className="button-row end">
              <button className="secondary" type="button" onClick={() => setShowApply(false)}>
                Cancel
              </button>
              <button className="primary" disabled={action.pending}>
                Apply and notify
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {showDismiss && (
        <Dialog title="Dismiss conflict" onClose={() => setShowDismiss(false)}>
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              void send({ kind: 'dismiss', payload: { reason } });
            }}
          >
            <p>The competing requests will be declined.</p>
            <label>
              Reason (required)
              <textarea
                required
                minLength={5}
                maxLength={500}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                {...fieldProps('reason')}
              />
            </label>
            <ErrorBox error={action.error} id={errorId} />
            <button className="destructive" disabled={action.pending}>
              Dismiss and notify
            </button>
          </form>
        </Dialog>
      )}
    </>
  );
}

function AllocationOutcome({ row }: { row: NonNullable<Conflict['recommendation']>[number] }) {
  if (row.unit_id) {
    return <Badge tone="success">Assigned unit {row.unit_id.split('-').slice(-1)[0]}</Badge>;
  }
  const alternative = row.alternatives[0];
  return (
    <>
      <Badge tone="warning">{word(row.reason || 'Alternative')}</Badge>
      {alternative && (
        <p>
          {alternative.equipment_name}
          <br />
          {range(alternative)}
        </p>
      )}
    </>
  );
}

export default function ConflictsPage() {
  const { id } = useParams();
  return id ? <Review id={id} key={id} /> : <List />;
}
