const paths = {
  flask: 'M9 3h6m-5 0v7L5 19a1.5 1.5 0 0 0 1.3 2h11.4a1.5 1.5 0 0 0 1.3-2L14 10V3M8 15h8',
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  calendar: 'M8 2v4m8-4v4M3 10h18M5 4h14a2 2 0 0 1 2 2v13a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  folder: 'M3 19V5h7l2 3h9v11z',
  checks: 'm3 12 4 4 7-8m-2 8 3 3 6-7',
  balance: 'M12 3v17m-6 1h12M4 7l8-2 8 2M4 7l-3 7h6L4 7Zm16 0-3 7h6l-3-7Z',
  chart: 'M3 3v18h18M8 16v-4m5 4V8m5 8V5',
  settings: 'M4 6h16M4 12h16M4 18h16M8 4v4m8 2v4m-6 2v4',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9m-8 12a2 2 0 0 0 4 0',
  search: 'M16 16l5 5m-3-10a7 7 0 1 1-14 0 7 7 0 0 1 14 0z',
  spark: 'M12 2l2.5 7.5L22 12l-7.5 2.5L12 22l-2.5-7.5L2 12l7.5-2.5L12 2Z',
  pin: 'M20 10c0 5-8 11-8 11S4 15 4 10a8 8 0 1 1 16 0zm-5 0a3 3 0 1 0-6 0 3 3 0 0 0 6 0z',
  wave: 'M2 12h4l3-7 5 14 3-7h5',
  cpu: 'M6 6h12v12H6zM9 9h6v6H9zM9 3v3m6-3v3m-6 12v3m6-3v3M3 9h3m-3 6h3m12-6h3m-3 6h3',
  monitor: 'M3 4h18v12H3zM12 16v4m-4 0h8',
  cube: 'm12 2 9 5v10l-9 5-9-5V7zM3 7l9 5 9-5m-9 5v10',
  bolt: 'm13 2-9 12h7l-1 8 9-12h-7l1-8z',
  tool: 'M14 6a4 4 0 0 0-5 5L3 17l4 4 6-6a4 4 0 0 0 5-5l-3 3-4-4 3-3z',
  clock: 'M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0zM12 6v6l4 2',
  chevron: 'm6 9 6 6 6-6',
  menu: 'M4 6h16M4 12h16M4 18h16',
  close: 'm6 6 12 12M6 18 18 6',
  plus: 'M12 5v14M5 12h14',
  list: 'M9 5h11M9 12h11M9 19h11M4 5h1M4 12h1m-1 7h1',
  shield: 'M12 2l8 4v6c0 5-8 10-8 10s-8-5-8-10V6l8-4zM8 12l3 3 5-6',
  user: 'M16 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0zM4 21v-2a5 5 0 0 1 5-5h6a5 5 0 0 1 5 5v2',
};

export type IconName = keyof typeof paths;
export function Icon({ name, size = 20 }: { name: IconName; size?: number }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}

export const categoryIcon = (category: string): IconName => ({
  measurement: 'wave', dev_kit: 'cpu', workstation: 'monitor', fabrication: 'cube',
  bio: 'flask', mechanical_testing: 'tool', computing: 'monitor', electronics: 'bolt',
} as Record<string, IconName>)[category] ?? 'flask';

