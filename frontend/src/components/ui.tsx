import { useEffect, useId, useRef, type KeyboardEvent, type ReactNode } from 'react';
import { ApiError } from '../api/client';
import type { Breakdown, Option, Source } from '../api/types';
import { range, word } from '../format';
import { Icon } from './Icon';

export function Heading({ label, title, subtitle, action }: { label?: string; title: string; subtitle?: string; action?: ReactNode }) {
  const ref = useRef<HTMLHeadingElement>(null);
  useEffect(() => { document.title = title + ' · LabLink'; ref.current?.focus({ preventScroll: true }); }, [title]);
  return <div className="page-heading"><div>{label && <p className="eyebrow">{label}</p>}<h1 ref={ref} tabIndex={-1}>{title}</h1>{subtitle && <p className="lead">{subtitle}</p>}</div>{action}</div>;
}
export function ErrorBox({ error }: { error?: Error | null }) {
  if (!error) return null;
  const fields = error instanceof ApiError && Array.isArray(error.details.fields) ? error.details.fields as {field: string; message: string}[] : [];
  return <div className="callout danger" role="alert"><strong>{error.message}</strong>{fields.length > 0 && <ul>{fields.map(field => <li key={field.field}>{word(field.field.split('.').slice(-1)[0] || field.field)}: {field.message}</li>)}</ul>}{error instanceof ApiError && error.requestId && <small>Request ID {error.requestId}</small>}</div>;
}
export function Loading({ children = 'Loading…' }: { children?: ReactNode }) {
  return <div className="loading" role="status" aria-busy="true"><span className="loader"/>{children}</div>;
}
export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return <section className="empty"><Icon name="folder" size={26}/><h2>{title}</h2>{children}</section>;
}
export function Badge({ children, tone = '' }: { children: ReactNode; tone?: string }) {
  return <span className={'badge ' + tone}>{children}</span>;
}
export function Status({ value }: { value: string }) {
  const tone = ['confirmed', 'approved', 'active', 'resolved', 'completed'].includes(value) ? 'success' :
    ['pending', 'pending_approval', 'contested', 'open', 'reallocated', 'maintenance'].includes(value) ? 'warning' :
    ['declined', 'no_show', 'retired'].includes(value) ? 'danger' : '';
  return <Badge tone={tone}>{word(value)}</Badge>;
}
export function AI({ source }: { source: Source }) {
  return <Badge tone="warning">{source === 'ai' ? <><Icon name="spark" size={13}/> AI-generated</> : 'Rules-based'}</Badge>;
}
export function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const trigger = document.activeElement;
    const element = ref.current;
    element?.showModal();
    return () => { element?.close(); if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus(); };
  }, []);
  return <dialog ref={ref} aria-labelledby={id} onCancel={event => { event.preventDefault(); onClose(); }}>
    <div className="dialog-heading"><h2 id={id}>{title}</h2><button className="icon-button" aria-label="Close" onClick={onClose}><Icon name="close"/></button></div>
    {children}
  </dialog>;
}
export function Tabs({ label, tabs, active, onChange }: { label: string; tabs: {id: string; label: string}[]; active: string; onChange: (key: string) => void }) {
  function handle(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const next = event.key === 'ArrowRight' ? (index + 1) % tabs.length : event.key === 'ArrowLeft' ? (index + tabs.length - 1) % tabs.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : null;
    if (next === null) return;
    event.preventDefault();
    const target = tabs[next];
    if (target) { onChange(target.id); document.getElementById('tab-' + target.id)?.focus(); }
  }
  return <div className="tabs" role="tablist" aria-label={label}>{tabs.map((tab, i) => <button type="button" role="tab" id={'tab-' + tab.id} key={tab.id} aria-controls="tab-results" aria-selected={active === tab.id} tabIndex={active === tab.id ? 0 : -1} onKeyDown={e => handle(e, i)} onClick={() => onChange(tab.id)}>{tab.label}</button>)}</div>;
}
export function Alternatives({ options, onAccept, pending }: { options: Option[]; onAccept: (option: Option, index: number) => void; pending: boolean }) {
  if (!options.length) return <p>No alternatives are available right now.</p>;
  return <ul className="plain alternatives">{options.map((option, index) => <li key={option.equipment_id + option.start}>
    <div><strong>{option.equipment_name}</strong><p>{range(option)} · {option.lab_name}</p><small>{option.reason}</small></div>
    <button className="secondary" disabled={pending} onClick={() => onAccept(option, index)}>Choose slot</button>
  </li>)}</ul>;
}
export function Score({ score }: { score: Breakdown }) {
  return <details className="score"><summary>Why this score?</summary><dl>{Object.entries(score.factors).map(([key, factor]) =>
    <div key={key}><dt>{word(key)} <span>{Math.round(factor.contribution * 100)} / {Math.round(factor.weight * 100)}</span></dt>
    <dd><meter min={0} max={1} value={factor.value} aria-label={word(key)}/><small>{factor.label}</small></dd></div>,
  )}</dl></details>;
}

