import type { ClauseMatch } from "../types/api";
import { colorForCategory } from "../utils/categoryColors";
import { colorForRiskLevel } from "../utils/riskColors";
import styles from "./ClauseListItem.module.css";

interface ClauseListItemProps {
  clause: ClauseMatch;
  located: boolean;
  reviewed: boolean;
  focused: boolean;
  onFocus: () => void;
  onToggleReviewed: () => void;
  reviewerName?: string;
  reviewDisabled?: boolean;
}

export function ClauseListItem({
  clause,
  located,
  reviewed,
  focused,
  onFocus,
  onToggleReviewed,
  reviewerName,
  reviewDisabled,
}: ClauseListItemProps) {
  const color = colorForCategory(clause.category);

  return (
    <li className={`${styles.item} ${focused ? styles.focused : ""}`}>
      <button
        type="button"
        className={styles.clickable}
        onClick={onFocus}
        disabled={!located}
        title={located ? "Scroll to this clause in the text" : "Location unavailable in text"}
      >
        <span className={styles.swatch} style={{ backgroundColor: color }} aria-hidden="true" />
        <span className={styles.body}>
          <span className={styles.headerRow}>
            <span className={styles.category}>{clause.category}</span>
            {clause.risk_level && (
              <span
                className={styles.riskBadge}
                style={{
                  backgroundColor: colorForRiskLevel(clause.risk_level),
                  color: clause.risk_level === "MEDIUM" ? "#0f1115" : "#fff",
                }}
                title="Risk level for this clause category"
              >
                {clause.risk_level}
              </span>
            )}
            <span className={styles.confidence}>
              {Math.round(clause.confidence * 100)}%
              {clause.confidence_band && ` (${clause.confidence_band})`}
            </span>
          </span>
          <span className={styles.snippet}>{clause.text}</span>
          {!located && <span className={styles.badge}>location unavailable</span>}
          {clause.possible_negation && (
            <span
              className={styles.negationBadge}
              title="This text is preceded by negation language (e.g. &quot;shall not&quot;, &quot;neither party may&quot;) — double-check it doesn't mean the opposite of what this category name suggests."
            >
              ⚠ possible negation — verify
            </span>
          )}
        </span>
      </button>
      <label className={styles.reviewedLabel}>
        <input type="checkbox" checked={reviewed} onChange={onToggleReviewed} disabled={reviewDisabled} />
        Reviewed
        {reviewed && reviewerName && <span className={styles.reviewerName}>by {reviewerName}</span>}
      </label>
    </li>
  );
}
