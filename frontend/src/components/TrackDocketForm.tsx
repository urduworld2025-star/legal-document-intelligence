import { FormEvent, useState } from "react";
import { trackDocket } from "../api/dockets";
import { ApiError } from "../api/client";
import { formatApiError } from "../utils/formatApiError";
import { ErrorBanner } from "./ErrorBanner";
import styles from "./TrackDocketForm.module.css";

interface TrackDocketFormProps {
  matterId: number;
  onTracked: () => void;
  disabled?: boolean;
}

export function TrackDocketForm({ matterId, onTracked, disabled = false }: TrackDocketFormProps) {
  const [docketId, setDocketId] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const blocked = disabled || submitting;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const parsed = Number(docketId);
    if (!docketId.trim() || Number.isNaN(parsed)) return;

    setSubmitting(true);
    setError(null);
    try {
      await trackDocket(parsed, matterId);
      setDocketId("");
      onTracked();
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      {disabled && <p className={styles.note}>Your role doesn't include docket tracking.</p>}
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <form className={styles.form} onSubmit={handleSubmit}>
        <input
          type="number"
          placeholder="CourtListener docket ID (e.g. 69510553)"
          value={docketId}
          onChange={(e) => setDocketId(e.target.value)}
          disabled={blocked}
        />
        <button type="submit" disabled={blocked || !docketId.trim()}>
          Track Docket
        </button>
      </form>
    </div>
  );
}
