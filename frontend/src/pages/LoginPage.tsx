import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import type { Persona } from '../api/types';
import { Icon } from '../components/Icon';
import { ErrorBox, Loading } from '../components/ui';
import { roleName } from '../format';
import { useAction, useApi, useAuth } from '../hooks';

export default function LoginPage() {
  const personas = useApi<Persona[]>('/auth/personas');
  const auth = useAuth();
  const action = useAction();
  const [selected, setSelected] = useState('');
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { document.title = 'Welcome to LabLink'; heading.current?.focus({ preventScroll: true }); }, []);
  async function login(persona: Persona) {
    setSelected(persona.id);
    const session = await action.run(() => auth.login(persona.id));
    if (session) {
      const next = search.get('next');
      const role = session.user.role;
      navigate(next && /^\/(?![\/\\])[^\\]*$/.test(next) ? next : role === 'student' ? '/discover' : role === 'faculty' ? '/approvals' : '/analytics', {replace: true});
    }
  }

  function personaCard(persona: Persona) {
    return <li key={persona.id}><button className="persona" disabled={action.pending} onClick={() => void login(persona)} aria-label={'Continue as ' + persona.name + ', ' + roleName(persona.role) + ', ' + persona.department}>
      <span className={'persona-icon ' + persona.role}><Icon name={persona.role === 'student' ? 'user' : persona.role === 'faculty' ? 'checks' : 'chart'} size={23}/></span>
      <span><strong>{persona.name}</strong><small>{roleName(persona.role)} · {persona.department}</small><span className="persona-blurb">{persona.blurb}</span></span>
      <span className="persona-continue">{selected === persona.id && action.pending ? 'Signing in…' : 'Continue'}</span>
    </button></li>;
  }

  return <div className="login-layout">
    <section className="login-hero">
      <div className="hero-art" aria-hidden="true"><svg viewBox="0 0 360 300" fill="none"><g stroke="currentColor"><circle cx="180" cy="150" r="110"/><circle cx="180" cy="150" r="87" strokeDasharray="3 7"/><circle cx="180" cy="150" r="57"/><path d="M17 150h326M180 8v284M103 73l154 154m0-154L103 227"/><path d="M145 154h13l10-22 16 43 13-22h18" strokeWidth="3"/><circle cx="180" cy="40" r="5" fill="currentColor"/><circle cx="290" cy="150" r="5" fill="currentColor"/><circle cx="103" cy="227" r="5" fill="currentColor"/></g></svg></div>
      <span className="hero-label"><Icon name="flask" size={17}/> Shared campus laboratories</span>
      <h1 ref={heading} tabIndex={-1}>Find the right lab.<br/>Make time to build.</h1>
      <p>Discover specialist equipment, reserve lab time, and get access for your project across campus.</p>
      <ul className="plain hero-features"><li><Icon name="grid" size={18}/> Cross-department catalogue</li><li><Icon name="calendar" size={18}/> Live availability</li><li><Icon name="balance" size={18}/> Fair slot allocation</li></ul>
    </section>
    <section className="sign-in"><h2>Choose a demo profile</h2><p className="muted">Explore LabLink as a student, faculty member, or lab administrator.</p>
      <ErrorBox error={personas.error || action.error}/>
      {personas.loading && <Loading/>}
      {personas.data && <><ul className="plain persona-list">{personas.data.slice(0, 3).map(personaCard)}</ul>
        <details className="more-personas"><summary>More demo profiles</summary><ul className="plain persona-list">{personas.data.slice(3).map(personaCard)}</ul></details></>}
      <details className="tour"><summary>Take the 60-second tour</summary><ol>
        <li>As Aarav, search for “measure 2.4 GHz antenna signals”.</li><li>As Dr. Meera, open Conflicts and review the spectrum analyser allocation.</li>
        <li>As Sneha, go to My bookings and choose an alternative.</li><li>As Ravi, open Analytics for campus utilisation.</li>
      </ol></details>
    </section>
  </div>;
}

