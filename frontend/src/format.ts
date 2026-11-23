import type { Interval, Role } from './api/types';
export const ZONE = 'Asia/Kolkata';
export const word = (value: string) => value.replace(/[_-]/g, ' ').replace(/^./, letter => letter.toUpperCase());
export const roleName = (role: Role) => role === 'lab_admin' ? 'Lab admin' : word(role);
export const time = (value: string) => new Intl.DateTimeFormat('en-IN', { timeZone: ZONE, hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }).format(new Date(value));
export function date(value: string, weekday = true) {
  const parsed = new Date(value.length === 10 ? value + 'T12:00:00+05:30' : value);
  return new Intl.DateTimeFormat('en-IN', { timeZone: ZONE, day: 'numeric', month: 'short', weekday: weekday ? 'short' : undefined }).format(parsed);
}
export const range = (item: Interval) => date(item.start) + ', ' + time(item.start) + '–' + time(item.end) + ' IST';
export const today = () => new Intl.DateTimeFormat('en-CA', { timeZone: ZONE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date());
export function shiftDay(day: string, offset: number) {
  const value = new Date(day + 'T12:00:00Z');
  value.setUTCDate(value.getUTCDate() + offset);
  return value.toISOString().slice(0, 10);
}
export const hours = (minutes: number) => (minutes / 60).toLocaleString('en-IN', { maximumFractionDigits: 1 }) + ' h';
export const CATEGORIES = ['measurement', 'dev_kit', 'workstation', 'fabrication', 'bio', 'mechanical_testing', 'computing', 'electronics'];
export const PROJECT_TYPES = ['capstone', 'research', 'course_lab', 'competition', 'personal'];
export const CERTIFICATIONS = ['laser-safety', 'rf-safety', 'bsl1-biosafety', 'machine-shop-basic', 'high-voltage'];

