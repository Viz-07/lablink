import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const css = readFileSync('src/styles/tokens.css', 'utf8');

function tokens(block: string): Record<string, string> {
  return Object.fromEntries([...block.matchAll(/--([\w-]+):\s*(#[0-9a-fA-F]{6})/g)].map(m => [m[1], m[2]]));
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r! + 0.7152 * g! + 0.0722 * b!;
}

function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi! + 0.05) / (lo! + 0.05);
}

const light = tokens(css.split(':root[data-theme="dark"]')[0] ?? '');
const dark = tokens(css.split(':root[data-theme="dark"]')[1]?.split('@media')[0] ?? '');
const TEXT_PAIRS: [string, string][] = [
  ['text', 'surface'], ['text', 'bg'], ['text-muted', 'surface'], ['text-muted', 'surface-2'], ['on-primary', 'primary'],
  ['primary', 'surface'], ['accent', 'surface'], ['success', 'success-soft'], ['warning', 'warning-soft'],
  ['danger', 'danger-soft'], ['danger', 'surface'],
];
const UI_PAIRS: [string, string][] = [['focus', 'surface'], ['focus', 'bg'], ['border-strong', 'surface']];

describe.each([['light', light], ['dark', dark]])('%s theme contrast (WCAG 2.2 AA)', (_name, theme) => {
  it.each(TEXT_PAIRS)('%s on %s is at least 4.5:1', (fg, bg) => {
    expect(ratio(theme[fg]!, theme[bg]!)).toBeGreaterThanOrEqual(4.5);
  });
  it.each(UI_PAIRS)('%s on %s is at least 3:1', (fg, bg) => {
    expect(ratio(theme[fg]!, theme[bg]!)).toBeGreaterThanOrEqual(3);
  });
});
