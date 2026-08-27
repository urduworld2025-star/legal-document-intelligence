import { useState } from "react";
import { UploadForm } from "../components/UploadForm";
import type { SubmitAction } from "../components/UploadForm";
import { LoadingIndicator } from "../components/LoadingIndicator";
import { ErrorBanner } from "../components/ErrorBanner";
import { DocumentTextViewer } from "../components/DocumentTextViewer";
import { ClauseList } from "../components/ClauseList";
import { DocumentClassificationCard } from "../components/DocumentClassificationCard";
import { useReviewedClauses } from "../hooks/useReviewedClauses";
import { parseDocument, extractClauses, classifyDocument } from "../api/documents";
import { ApiError } from "../api/client";
import { formatApiError } from "../utils/formatApiError";
import { useAuth } from "../auth/AuthContext";
import type { ClauseMatch, DocumentClassification, ParsedDocument, RiskSummary } from "../types/api";
import styles from "../App.module.css";

type Status = "idle" | "loading-parse" | "loading-extract" | "loading-classify";

type Result =
  | { mode: "parse"; document: ParsedDocument }
  | { mode: "extract"; document: ParsedDocument; clauses: ClauseMatch[]; riskSummary: RiskSummary }
  | { mode: "classify"; document: ParsedDocument; classification: DocumentClassification };

export function QuickAnalyzePage() {
  const { user } = useAuth();
  const canAnalyze = user?.role === "attorney" || user?.role === "paralegal";
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [focusedClauseIndex, setFocusedClauseIndex] = useState<number | null>(null);
  const { reviewed, toggle, reset } = useReviewedClauses();

  async function handleSubmit(file: File, action: SubmitAction) {
    setStatus(
      action === "parse" ? "loading-parse" : action === "extract" ? "loading-extract" : "loading-classify"
    );
    setError(null);
    try {
      if (action === "parse") {
        const document = await parseDocument(file, null);
        setResult({ mode: "parse", document });
      } else if (action === "extract") {
        const extraction = await extractClauses(file, null);
        setResult({
          mode: "extract",
          document: extraction.document,
          clauses: extraction.clauses,
          riskSummary: extraction.risk_summary,
        });
        reset();
        setFocusedClauseIndex(null);
      } else {
        const { document, classification } = await classifyDocument(file, null);
        setResult({ mode: "classify", document, classification });
        setFocusedClauseIndex(null);
      }
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error — see browser console.");
      if (!(err instanceof ApiError)) console.error(err);
    } finally {
      setStatus("idle");
    }
  }

  const clauses = result?.mode === "extract" ? result.clauses : [];

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <h1>Quick Analyze</h1>
        <p className={styles.subtitle}>
          Upload a contract to parse its text or extract risk-relevant clauses. Nothing here is saved — use a
          matter if you want to keep results.
        </p>
      </header>

      <UploadForm disabled={status !== "idle"} canAnalyze={canAnalyze} onSubmit={handleSubmit} />

      {status !== "idle" && (
        <LoadingIndicator
          message={
            status === "loading-extract"
              ? "Extracting clauses — this can take several seconds on CPU…"
              : status === "loading-classify"
                ? "Classifying document…"
                : "Parsing document…"
          }
        />
      )}

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {result && (
        <div className={styles.resultGrid}>
          <DocumentTextViewer
            fullText={result.document.full_text}
            clauses={clauses}
            focusedClauseIndex={focusedClauseIndex}
            onFocusClause={setFocusedClauseIndex}
          />
          {result.mode === "extract" ? (
            <ClauseList
              clauses={result.clauses}
              fullTextLength={result.document.full_text.length}
              riskSummary={result.riskSummary}
              reviewed={reviewed}
              focusedClauseIndex={focusedClauseIndex}
              onFocusClause={setFocusedClauseIndex}
              onToggleReviewed={toggle}
            />
          ) : result.mode === "classify" ? (
            <DocumentClassificationCard classification={result.classification} />
          ) : (
            <p className={styles.hint}>Run "Extract Clauses" or "Classify Document" to see results here.</p>
          )}
        </div>
      )}
    </div>
  );
}
