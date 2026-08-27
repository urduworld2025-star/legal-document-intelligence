import type { ClauseMatch } from "../types/api";

export interface HighlightSegment {
  text: string;
  start: number;
  end: number;
  clauseIndexes: number[];
}

type LocatedClause = ClauseMatch & { index: number; char_start: number; char_end: number };

function isLocated(
  c: ClauseMatch & { index: number },
  textLength: number
): c is LocatedClause {
  return (
    c.char_start != null &&
    c.char_end != null &&
    c.char_start >= 0 &&
    c.char_end <= textLength &&
    c.char_start < c.char_end
  );
}

/**
 * Decomposes fullText into segments at every clause boundary, so overlapping
 * spans from different categories (which aren't guaranteed to nest) each get
 * their own correctly-covered segment instead of being merged or clobbered.
 */
export function buildHighlightSegments(fullText: string, clauses: ClauseMatch[]): HighlightSegment[] {
  const indexed = clauses.map((c, index) => ({ ...c, index }));
  const located = indexed.filter((c): c is LocatedClause => isLocated(c, fullText.length));

  const points = [...new Set([0, fullText.length, ...located.flatMap((c) => [c.char_start, c.char_end])])].sort(
    (a, b) => a - b
  );

  const segments: HighlightSegment[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const start = points[i];
    const end = points[i + 1];
    if (start === end) continue;
    const covering = located.filter((c) => c.char_start <= start && c.char_end >= end);
    segments.push({ text: fullText.slice(start, end), start, end, clauseIndexes: covering.map((c) => c.index) });
  }
  return segments;
}

export function locatedClauseIndexes(clauses: ClauseMatch[], fullTextLength: number): Set<number> {
  const indexed = clauses.map((c, index) => ({ ...c, index }));
  return new Set(indexed.filter((c) => isLocated(c, fullTextLength)).map((c) => c.index));
}
