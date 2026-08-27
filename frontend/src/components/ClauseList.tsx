import { useMemo } from "react";
import type { ClauseMatch, RiskLevel, RiskSummary } from "../types/api";
import { locatedClauseIndexes } from "../utils/highlight";
import { colorForRiskLevel } from "../utils/riskColors";
import { ClauseListItem } from "./ClauseListItem";
import styles from "./ClauseList.module.css";

const RISK_LEVELS_BY_SEVERITY: RiskLevel[] = ["HIGH", "MEDIUM", "INFORMATIONAL"];

interface ClauseListProps {
  clauses: ClauseMatch[];
  fullTextLength: number;
  riskSummary: RiskSummary;
  reviewed: Set<number>;
  focusedClauseIndex: number | null;
  onFocusClause: (index: number) => void;
  onToggleReviewed: (index: number) => void;
  reviewerFor?: (index: number) => string | undefined;
  reviewDisabled?: boolean;
  persisted?: boolean;
}

export function ClauseList({
  clauses,
  fullTextLength,
  riskSummary,
  reviewed,
  focusedClauseIndex,
  onFocusClause,
  onToggleReviewed,
  reviewerFor,
  reviewDisabled,
  persisted = false,
}: ClauseListProps) {
  const located = useMemo(() => locatedClauseIndexes(clauses, fullTextLength), [clauses, fullTextLength]);

  const order = useMemo(
    () =>
      clauses
        .map((_, index) => index)
        .sort((a, b) => {
          const aStart = clauses[a].char_start ?? Number.MAX_SAFE_INTEGER;
          const bStart = clauses[b].char_start ?? Number.MAX_SAFE_INTEGER;
          return aStart - bStart;
        }),
    [clauses]
  );

  return (
    <div className={styles.wrapper}>
      <div className={styles.header}>
        <div>
          <h2>Extracted Clauses</h2>
          {riskSummary.highest_risk_level && (
            <p className={styles.riskSummaryLine}>
              Highest risk:{" "}
              <strong style={{ color: colorForRiskLevel(riskSummary.highest_risk_level) }}>
                {riskSummary.highest_risk_level}
              </strong>
              {" — "}
              {RISK_LEVELS_BY_SEVERITY.filter((level) => riskSummary.counts_by_level[level] > 0)
                .map((level) => `${riskSummary.counts_by_level[level]} ${level}`)
                .join(", ")}
            </p>
          )}
        </div>
        <span className={styles.counter}>
          {reviewed.size} of {clauses.length} reviewed
        </span>
      </div>
      {clauses.length === 0 ? (
        <p className={styles.empty}>No clauses detected for the categories this model was trained on.</p>
      ) : (
        <ul className={styles.list}>
          {order.map((index) => (
            <ClauseListItem
              key={index}
              clause={clauses[index]}
              located={located.has(index)}
              reviewed={reviewed.has(index)}
              focused={focusedClauseIndex === index}
              onFocus={() => onFocusClause(index)}
              onToggleReviewed={() => onToggleReviewed(index)}
              reviewerName={reviewerFor?.(index)}
              reviewDisabled={reviewDisabled}
            />
          ))}
        </ul>
      )}
      <p className={styles.notice}>
        {persisted
          ? "Review status is saved to this matter and visible to your whole team."
          : "Review status is stored only in this browser tab and is not saved to the server — it resets if you reload the page or process a new document."}
      </p>
    </div>
  );
}
