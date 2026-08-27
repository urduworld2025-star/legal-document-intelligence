import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { UploadForm } from "../components/UploadForm";
import type { SubmitAction } from "../components/UploadForm";
import { LoadingIndicator } from "../components/LoadingIndicator";
import { ErrorBanner } from "../components/ErrorBanner";
import { MatterDocumentCard } from "../components/MatterDocumentCard";
import { TrackDocketForm } from "../components/TrackDocketForm";
import { TrackedDocketList } from "../components/TrackedDocketList";
import { deleteMatter, getMatterDetail } from "../api/matters";
import { parseDocument, extractClauses, classifyDocument } from "../api/documents";
import { ApiError, requestBlob } from "../api/client";
import { formatApiError } from "../utils/formatApiError";
import { useAuth } from "../auth/AuthContext";
import type { MatterDetail } from "../types/matter";
import styles from "./MatterDetailPage.module.css";

export function MatterDetailPage() {
  const { matterId } = useParams<{ matterId: string }>();
  const id = Number(matterId);
  const navigate = useNavigate();
  const { user } = useAuth();
  const canAnalyze = user?.role === "attorney" || user?.role === "paralegal";
  const canDelete = user?.role === "attorney";

  const [detail, setDetail] = useState<MatterDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setDetail(await getMatterDetail(id));
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function handleUpload(file: File, action: SubmitAction) {
    setUploading(true);
    setError(null);
    try {
      if (action === "parse") await parseDocument(file, id);
      else if (action === "extract") await extractClauses(file, id);
      else await classifyDocument(file, id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
    } finally {
      setUploading(false);
    }
  }

  async function handleDownloadReport() {
    setDownloadingReport(true);
    setError(null);
    try {
      const blob = await requestBlob(`/matters/${id}/report`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `matter-${id}-report.pdf`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
    } finally {
      setDownloadingReport(false);
    }
  }

  async function handleDeleteMatter() {
    if (!detail) return;
    if (!window.confirm(`Delete "${detail.matter.name}"? This removes all its documents and tracked dockets.`)) {
      return;
    }
    setDeleting(true);
    setError(null);
    try {
      await deleteMatter(id);
      navigate("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
      setDeleting(false);
    }
  }

  if (error && !detail) {
    return <ErrorBanner message={error} onDismiss={() => setError(null)} />;
  }

  if (!detail) {
    return <LoadingIndicator message="Loading matter…" />;
  }

  return (
    <div className={styles.page}>
      <header className={styles.headerRow}>
        <div>
          <h1>{detail.matter.name}</h1>
          {detail.matter.description && <p className={styles.description}>{detail.matter.description}</p>}
        </div>
        <div className={styles.headerActions}>
          <button
            type="button"
            className={styles.reportLink}
            onClick={handleDownloadReport}
            disabled={downloadingReport}
          >
            {downloadingReport ? "Preparing…" : "Download Report (PDF)"}
          </button>
          {canDelete && (
            <button
              type="button"
              className={styles.deleteButton}
              onClick={handleDeleteMatter}
              disabled={deleting}
            >
              {deleting ? "Deleting…" : "Delete Matter"}
            </button>
          )}
        </div>
      </header>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <UploadForm disabled={uploading} canAnalyze={canAnalyze} onSubmit={handleUpload} />
      {uploading && <LoadingIndicator message="Analyzing and saving to this matter…" />}

      <section>
        <h2>Analyzed Documents</h2>
        {detail.documents.length === 0 ? (
          <p className={styles.empty}>No documents analyzed for this matter yet.</p>
        ) : (
          <div className={styles.documentList}>
            {detail.documents.map((doc) => (
              <MatterDocumentCard key={doc.id} document={doc} />
            ))}
          </div>
        )}
      </section>

      <section>
        <h2>Tracked Dockets</h2>
        <TrackDocketForm matterId={id} onTracked={refresh} disabled={!canAnalyze} />
        <TrackedDocketList dockets={detail.tracked_dockets} checkDisabled={!canAnalyze} />
      </section>
    </div>
  );
}
