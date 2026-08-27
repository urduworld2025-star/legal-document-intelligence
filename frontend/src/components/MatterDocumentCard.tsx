import { useState } from "react";
import { DocumentTextViewer } from "./DocumentTextViewer";
import { ClauseList } from "./ClauseList";
import { DocumentClassificationCard } from "./DocumentClassificationCard";
import { usePersistedClauseReviews } from "../hooks/usePersistedClauseReviews";
import { useAuth } from "../auth/AuthContext";
import type { MatterDocument } from "../types/matter";
import styles from "./MatterDocumentCard.module.css";

interface MatterDocumentCardProps {
  document: MatterDocument;
}

export function MatterDocumentCard({ document }: MatterDocumentCardProps) {
  const { user } = useAuth();
  const [expanded, setExpanded] = useState(false);
  const [focusedClauseIndex, setFocusedClauseIndex] = useState<number | null>(null);
  const { reviewed, reviewerFor, toggle } = usePersistedClauseReviews(
    document.matter_id,
    document.id,
    expanded && document.analysis_type === "extract_clauses"
  );

  return (
    <div className={styles.card}>
      <button type="button" className={styles.headerButton} onClick={() => setExpanded((e) => !e)}>
        <span className={styles.filename}>{document.source_filename}</span>
        <span className={styles.badge}>{document.analysis_type}</span>
        <span className={styles.date}>{new Date(document.created_at).toLocaleString()}</span>
      </button>

      {expanded && document.analysis_type === "parse" && (
        <DocumentTextViewer
          fullText={document.result.full_text}
          clauses={[]}
          focusedClauseIndex={null}
          onFocusClause={() => {}}
        />
      )}

      {expanded && document.analysis_type === "extract_clauses" && (
        <div className={styles.resultGrid}>
          <DocumentTextViewer
            fullText={document.result.document.full_text}
            clauses={document.result.clauses}
            focusedClauseIndex={focusedClauseIndex}
            onFocusClause={setFocusedClauseIndex}
          />
          <ClauseList
            clauses={document.result.clauses}
            fullTextLength={document.result.document.full_text.length}
            riskSummary={document.result.risk_summary}
            reviewed={reviewed}
            focusedClauseIndex={focusedClauseIndex}
            onFocusClause={setFocusedClauseIndex}
            onToggleReviewed={toggle}
            reviewerFor={reviewerFor}
            reviewDisabled={user?.role === "support_staff"}
            persisted
          />
        </div>
      )}

      {expanded && document.analysis_type === "classify" && (
        <DocumentClassificationCard classification={document.result.classification} />
      )}
    </div>
  );
}
