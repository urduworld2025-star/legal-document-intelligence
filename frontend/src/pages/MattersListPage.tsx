import { FormEvent, useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { createMatter, listMatters } from "../api/matters";
import { ApiError } from "../api/client";
import { formatApiError } from "../utils/formatApiError";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingIndicator } from "../components/LoadingIndicator";
import { useAuth } from "../auth/AuthContext";
import type { Matter } from "../types/matter";
import styles from "./MattersListPage.module.css";

export function MattersListPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const canCreate = user?.role !== "support_staff";
  const [matters, setMatters] = useState<Matter[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    listMatters()
      .then(setMatters)
      .catch((err) => setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error."));
  }, []);

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      const matter = await createMatter(name.trim(), description.trim() || null);
      navigate(`/matters/${matter.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className={styles.page}>
      <header>
        <h1>Matters</h1>
        <p className={styles.subtitle}>Organize contract review and docket monitoring by case.</p>
      </header>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {canCreate && (
        <form className={styles.createForm} onSubmit={handleCreate}>
          <input
            type="text"
            placeholder="Matter name (e.g. Acme v. Beta)"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={creating}
          />
          <input
            type="text"
            placeholder="Description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={creating}
          />
          <button type="submit" disabled={creating || !name.trim()}>
            Create Matter
          </button>
        </form>
      )}

      {matters === null ? (
        <LoadingIndicator message="Loading matters…" />
      ) : matters.length === 0 ? (
        <p className={styles.empty}>No matters yet — create one above to get started.</p>
      ) : (
        <ul className={styles.list}>
          {matters.map((matter) => (
            <li key={matter.id}>
              <Link to={`/matters/${matter.id}`} className={styles.matterLink}>
                <span className={styles.matterName}>{matter.name}</span>
                {matter.description && <span className={styles.matterDescription}>{matter.description}</span>}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
