import { useEffect, useMemo, useRef } from "react";
import type { ClauseMatch } from "../types/api";
import { buildHighlightSegments } from "../utils/highlight";
import { colorForCategory } from "../utils/categoryColors";
import styles from "./DocumentTextViewer.module.css";

interface DocumentTextViewerProps {
  fullText: string;
  clauses: ClauseMatch[];
  focusedClauseIndex: number | null;
  onFocusClause: (index: number) => void;
}

export function DocumentTextViewer({ fullText, clauses, focusedClauseIndex, onFocusClause }: DocumentTextViewerProps) {
  const segments = useMemo(() => buildHighlightSegments(fullText, clauses), [fullText, clauses]);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (focusedClauseIndex == null || !containerRef.current) return;
    const el = containerRef.current.querySelector(`[data-clause-indexes~="${focusedClauseIndex}"]`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      el.classList.add(styles.flash);
      const timeout = setTimeout(() => el.classList.remove(styles.flash), 1200);
      return () => clearTimeout(timeout);
    }
  }, [focusedClauseIndex]);

  return (
    <div className={styles.viewer} ref={containerRef}>
      {segments.length === 0 ? (
        <p className={styles.empty}>No text extracted from this document.</p>
      ) : (
        segments.map((segment, i) => {
          if (segment.clauseIndexes.length === 0) {
            return <span key={i}>{segment.text}</span>;
          }
          const isOverlap = segment.clauseIndexes.length > 1;
          const categories = segment.clauseIndexes.map((idx) => clauses[idx].category);
          const color = colorForCategory(categories[0]);
          return (
            <mark
              key={i}
              data-clause-indexes={segment.clauseIndexes.join(" ")}
              title={categories.join(" + ")}
              className={isOverlap ? styles.overlap : undefined}
              style={
                isOverlap
                  ? { backgroundImage: `repeating-linear-gradient(45deg, ${segment.clauseIndexes.map((idx) => colorForCategory(clauses[idx].category) + "55").join(", ")})` }
                  : { backgroundColor: color + "40", borderBottomColor: color }
              }
              onClick={() => onFocusClause(segment.clauseIndexes[0])}
            >
              {segment.text}
            </mark>
          );
        })
      )}
    </div>
  );
}
