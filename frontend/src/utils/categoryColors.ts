// A fixed palette + deterministic string hash, rather than a hardcoded
// switch over the current 4 categories, so new categories added later don't
// require a code change here.
const PALETTE = [
  "#a78bfa", // amethyst violet
  "#38bdf8", // sapphire blue
  "#34d399", // emerald green
  "#f472b6", // rose quartz pink
  "#22d3ee", // aquamarine cyan
  "#facc15", // citrine yellow
  "#fb7185", // garnet coral
  "#a3e635", // peridot lime
];

export function colorForCategory(category: string): string {
  let hash = 0;
  for (let i = 0; i < category.length; i++) {
    hash = (hash << 5) - hash + category.charCodeAt(i);
    hash |= 0;
  }
  const index = Math.abs(hash) % PALETTE.length;
  return PALETTE[index];
}
