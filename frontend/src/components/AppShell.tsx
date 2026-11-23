import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { roleName } from '../format';
import { useAuth } from '../hooks';
import { Icon, type IconName } from './Icon';

const links: [string, string, IconName][] = [
  ['discover', 'Discover', 'grid'], ['bookings', 'My bookings', 'calendar'], ['projects', 'Projects', 'folder'],
  ['approvals', 'Approvals', 'checks'], ['conflicts', 'Conflicts', 'balance'], ['analytics', 'Analytics', 'chart'],
  ['manage/equipment', 'Manage', 'settings'],
];

export function Brand() {
  return <Link className="brand" to="/"><span className="brand-mark"><Icon name="flask" size={24}/></span><span>Lab<span>Link</span><small>CAMPUS LAB ACCESS</small></span></Link>;
}

export function AppShell() {
  const { session, logout } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const menu = useRef<HTMLButtonElement>(null);
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState(0);
  const [theme, setTheme] = useState(() => localStorage.getItem('lablink-theme') || 'system');
  const [fairness, setFairness] = useState(false);
  useEffect(() => {
    window.scrollTo(0, 0);
    setOpen(false);
  }, [location.pathname]);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('lablink-theme', theme);
  }, [theme]);
  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    const poll = () => {
      if (document.visibilityState === 'visible') api<{unread_count: number}>('/notifications/unread-count', {signal: controller.signal}).then(data => setUnread(data.unread_count), () => {});
    };
    poll();
    const timer = window.setInterval(poll, 60_000);
    window.addEventListener('lablink:notifications', poll);
    return () => { controller.abort(); window.clearInterval(timer); window.removeEventListener('lablink:notifications', poll); };
  }, [session, location.pathname]);

  return <div className={session ? 'shell' : 'public-shell'}>
    <a className="skip" href="#main">Skip to main content</a>
    <header className="site-header"><div className="header-inner"><Brand/>
      {session ? <>
        <button ref={menu} className="mobile-menu secondary" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="navigation"><Icon name="menu"/> Menu</button>
        <nav id="navigation" aria-label="Primary" className={open ? 'navigation open' : 'navigation'} onKeyDown={event => { if (event.key === 'Escape') { setOpen(false); menu.current?.focus(); } }}>
          {links.filter(([key]) => session.permissions.includes(key.split('/')[0] || '')).map(([key, label, icon]) =>
            <NavLink key={key} to={'/' + key}><Icon name={icon} size={17}/>{label}</NavLink>)}
        </nav>
        <div className="user-area"><Link className="icon-button notice-link" to="/notifications" aria-label={'Notifications, ' + unread + ' unread'}><Icon name="bell"/>{unread > 0 && <b>{unread > 9 ? '9+' : unread}</b>}</Link>
          <details className="profile"><summary><span className="avatar">{session.user.name.split(' ').filter(s => !s.endsWith('.')).slice(0, 2).map(s => s[0]).join('')}</span><span className="profile-name">{session.user.name.split(' ').find(s => !s.endsWith('.'))}<small>{roleName(session.user.role)}</small></span><Icon name="chevron" size={14}/></summary>
            <div className="profile-panel"><strong>{session.user.name}</strong><small>{roleName(session.user.role)} · {session.user.department_id.toUpperCase()}</small>
              <label>Appearance<select value={theme} onChange={e => setTheme(e.target.value)}><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></label>
              {session.demo_mode && <Link to="/login" onClick={event => event.currentTarget.closest('details')?.removeAttribute('open')}>Switch persona</Link>}
              <button className="secondary" onClick={() => void logout().then(() => navigate('/login')).catch(() => { window.location.assign('/login'); })}>Sign out</button>
            </div>
          </details>
        </div>
      </> : <span className="demo-label"><span/> Campus demo</span>}
    </div></header>
    <main id="main" className={location.pathname === '/login' ? 'main login-main' : 'main'} tabIndex={-1}><Outlet/></main>
    <footer className="footer"><div><span><strong>LabLink</strong> · Campus laboratory resource sharing</span><div>
      <button className="text-button" type="button" aria-expanded={fairness} onClick={() => setFairness(!fairness)}>How fairness works</button>
      {session?.demo_mode && <span>Demo mode</span>}
    </div></div>{fairness && <p>Eligible requests are ranked by deadline urgency (35%), recent usage (25%), project type (20%), approval (10%), and waiting time (10%). Training, availability, and usage limits are checked before any slot is assigned.</p>}</footer>
  </div>;
}

