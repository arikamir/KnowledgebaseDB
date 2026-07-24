export function markDuration(name: string, start: string, end: string): number | undefined {
  const startEntry = performance.getEntriesByName(start, "mark").at(-1);
  const endEntry = performance.getEntriesByName(end, "mark").at(-1);
  if (!startEntry || !endEntry) return undefined;
  const duration = Math.max(0, endEntry.startTime - startEntry.startTime);
  performance.measure(name, { start, end });
  return duration;
}
