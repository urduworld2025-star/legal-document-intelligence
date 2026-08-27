import type { DocumentClassification, DocumentType } from "../types/api";
import { colorForDocType } from "../utils/docTypeColors";
import styles from "./DocumentClassificationCard.module.css";

const ORDER: DocumentType[] = ["Contract", "Email", "Other"];

interface DocumentClassificationCardProps {
  classification: DocumentClassification;
}

export function DocumentClassificationCard({ classification }: DocumentClassificationCardProps) {
  return (
    <div className={styles.wrapper}>
      <h2>Document Classification</h2>
      <p className={styles.predicted}>
        Predicted type:{" "}
        <strong style={{ color: colorForDocType(classification.predicted_type) }}>
          {classification.predicted_type}
        </strong>{" "}
        ({Math.round(classification.confidence * 100)}%)
      </p>
      <ul className={styles.breakdown}>
        {ORDER.map((type) => (
          <li key={type} className={styles.row}>
            <span className={styles.label} style={{ color: colorForDocType(type) }}>
              {type}
            </span>
            <div className={styles.barTrack}>
              <div
                className={styles.barFill}
                style={{
                  width: `${Math.round(classification.probabilities[type] * 100)}%`,
                  backgroundColor: colorForDocType(type),
                }}
              />
            </div>
            <span className={styles.pct}>{Math.round(classification.probabilities[type] * 100)}%</span>
          </li>
        ))}
      </ul>
      <p className={styles.notice}>
        First-pass triage only — review before relying on it. "Other" is a placeholder proxy class (trained on
        generic news text, not a curated eDiscovery category) meaning "not a contract, not an email" — see README
        for details.
      </p>
    </div>
  );
}
