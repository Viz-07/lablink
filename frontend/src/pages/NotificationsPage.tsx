import { Link } from 'react-router-dom';
import { post } from '../api/client';
import type { Notices } from '../api/types';
import { Icon } from '../components/Icon';
import { Badge, Empty, ErrorBox, Heading, Loading } from '../components/ui';
import { date, time } from '../format';
import { useAction, useApi } from '../hooks';

export default function NotificationsPage() {
  const messages = useApi<Notices>('/notifications');
  const action = useAction();
  async function read(ids: string[] | 'all') {
    await action.run(async () => {
      await post('/notifications/read', {ids});
      messages.reload();
      window.dispatchEvent(new Event('lablink:notifications'));
    });
  }
  return <>
    <Heading title="Notifications" subtitle={messages.data ? messages.data.unread_count + ' unread updates' : 'Booking, approval, and access updates.'} action={<button className="secondary" disabled={!messages.data?.unread_count || action.pending} onClick={() => void read('all')}>Mark all as read</button>}/>
    <ErrorBox error={messages.error || action.error}/>{messages.loading && <Loading/>}
    {messages.data?.items.length === 0 && <Empty title="You’re all caught up"/>}
    <ul className="plain stack">{messages.data?.items.map(item => <li className={'panel notice ' + (!item.read ? 'new' : '')} key={item.id}><div className="category-icon"><Icon name="bell" size={21}/></div>
      <div><h2><Link to={item.link} onClick={() => {if (!item.read) void read([item.id]);}}>{item.title}</Link> {!item.read && <Badge tone="success">Unread</Badge>}</h2><p>{item.body}</p><time dateTime={item.created_at}>{date(item.created_at)} · {time(item.created_at)} IST</time></div>
      {!item.read && <button className="text-button" disabled={action.pending} onClick={() => void read([item.id])}>Mark read</button>}
    </li>)}</ul>
  </>;
}

