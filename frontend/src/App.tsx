import { lazy, type ReactNode } from 'react';
import { Link, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { Heading, Loading } from './components/ui';
import { useAuth } from './hooks';

const Login = lazy(() => import('./pages/LoginPage'));
const Discover = lazy(() => import('./pages/DiscoverPage'));
const Equipment = lazy(() => import('./pages/EquipmentDetailPage'));
const Bookings = lazy(() => import('./pages/MyBookingsPage'));
const Projects = lazy(() => import('./pages/ProjectsPage'));
const AccessRequest = lazy(() => import('./pages/NewAccessRequestPage'));
const Approvals = lazy(() => import('./pages/ApprovalsPage'));
const Conflicts = lazy(() => import('./pages/ConflictsPage'));
const Analytics = lazy(() => import('./pages/AnalyticsPage'));
const Manage = lazy(() => import('./pages/ManageEquipmentPage'));
const Audit = lazy(() => import('./pages/AuditLogPage'));
const Notifications = lazy(() => import('./pages/NotificationsPage'));

function Guard({ permission, children }: { permission?: string; children: ReactNode }) {
  const { session } = useAuth();
  const { pathname, search } = useLocation();
  if (session === undefined) return <Loading/>;
  if (!session) return <Navigate replace to={'/login?next=' + encodeURIComponent(pathname + search)}/>;
  if (permission && !session.permissions.includes(permission)) return <><Heading title="Access restricted" subtitle="Your current role cannot open this page."/><Link className="button primary" to="/discover">Discover equipment</Link></>;
  return children;
}
export default function App() {
  return <Routes><Route element={<AppShell/>}>
    <Route index element={<Navigate replace to="/discover"/>}/>
    <Route path="login" element={<Login/>}/>
    <Route path="discover" element={<Guard><Discover/></Guard>}/>
    <Route path="equipment/:id" element={<Guard><Equipment/></Guard>}/>
    <Route path="bookings" element={<Guard><Bookings/></Guard>}/>
    <Route path="projects" element={<Guard><Projects/></Guard>}/>
    <Route path="projects/new-request" element={<Guard><AccessRequest/></Guard>}/>
    <Route path="approvals" element={<Guard permission="approvals"><Approvals/></Guard>}/>
    <Route path="conflicts/:id?" element={<Guard permission="conflicts"><Conflicts/></Guard>}/>
    <Route path="analytics" element={<Guard permission="analytics"><Analytics/></Guard>}/>
    <Route path="manage/equipment" element={<Guard permission="manage"><Manage/></Guard>}/>
    <Route path="manage/audit" element={<Guard permission="manage"><Audit/></Guard>}/>
    <Route path="notifications" element={<Guard><Notifications/></Guard>}/>
    <Route path="*" element={<><Heading title="Page not found"/><Link className="button primary" to="/">Return to LabLink</Link></>}/>
  </Route></Routes>;
}

