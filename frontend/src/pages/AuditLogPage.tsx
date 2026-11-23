import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { Audit, Page } from '../api/types';
import { Empty, ErrorBox, Heading, Loading } from '../components/ui';
import { date, time } from '../format';
import { useApi } from '../hooks';

export default function AuditLogPage() {
  const [cursor, setCursor] = useState('');
  const log = useApi<Page<Audit>>('/admin/audit' + (cursor ? '?cursor=' + cursor : ''));
  return <>
    <nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/manage/equipment">Manage equipment</Link><span>/</span><span>Audit log</span></nav>
    <Heading title="Audit log" subtitle="Administrative activity and booking state changes."/>
    <ErrorBox error={log.error}/>{log.loading && <Loading/>}
    {log.data?.items.length === 0 && <Empty title="No audit entries"/>}
    {log.data?.items.length ? <div className="panel table-wrap" role="region" aria-label="Audit entries" tabIndex={0}><table><caption className="sr-only">Audit entries</caption>
      <thead><tr><th scope="col">Time (IST)</th><th scope="col">Actor</th><th scope="col">Action</th><th scope="col">Target</th><th scope="col">Details</th></tr></thead>
      <tbody>{log.data.items.map(item => <tr key={item.id}><td><time dateTime={item.at}>{date(item.at)} · {time(item.at)}</time></td><td>{item.actor_id}</td><th scope="row">{item.action}</th><td>{item.target_id}</td><td>{Object.entries(item.details).map(([key, value]) => key + ': ' + value).join(' · ') || '—'}</td></tr>)}</tbody>
    </table></div> : null}
    <div className="pagination">{cursor && <button className="secondary" onClick={() => setCursor('')}>First page</button>}{log.data?.next_cursor && <button className="secondary" onClick={() => setCursor(log.data?.next_cursor || '')}>Next page</button>}</div>
  </>;
}

