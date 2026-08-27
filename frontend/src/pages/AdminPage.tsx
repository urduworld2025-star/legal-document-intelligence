import { FormEvent, useEffect, useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { createUser, listAuditLog } from "../api/auth";
import { ApiError } from "../api/client";
import { formatApiError } from "../utils/formatApiError";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingIndicator } from "../components/LoadingIndicator";
import type { AuditLogEntry, Role } from "../types/user";
import styles from "./AdminPage.module.css";

const ROLES: Role[] = ["attorney", "paralegal", "support_staff"];

export function AdminPage() {
  const { user } = useAuth();
  const [auditLog, setAuditLog] = useState<AuditLogEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<Role>("paralegal");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<string | null>(null);

  useEffect(() => {
    if (user?.role !== "attorney") return;
    listAuditLog()
      .then(setAuditLog)
      .catch((err) => setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error."));
  }, [user]);

  if (user?.role !== "attorney") {
    return <p className={styles.denied}>Attorneys only.</p>;
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault();
    setCreating(true);
    setError(null);
    setCreated(null);
    try {
      const newUser = await createUser(email.trim(), name.trim(), password, role);
      setCreated(`Created ${newUser.role} account for ${newUser.email}.`);
      setEmail("");
      setName("");
      setPassword("");
      setRole("paralegal");
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className={styles.page}>
      <header>
        <h1>Admin</h1>
        <p className={styles.subtitle}>Create accounts and review the audit log.</p>
      </header>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <section>
        <h2>Create User</h2>
        <form className={styles.createForm} onSubmit={handleCreate}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            disabled={creating}
          />
          <input
            type="text"
            placeholder="Full name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            disabled={creating}
          />
          <input
            type="password"
            placeholder="Temporary password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            disabled={creating}
          />
          <select value={role} onChange={(e) => setRole(e.target.value as Role)} disabled={creating}>
            {ROLES.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>
          <button
            type="submit"
            disabled={creating || !email.trim() || !name.trim() || password.length < 8}
          >
            Create User
          </button>
        </form>
        {created && <p className={styles.success}>{created}</p>}
      </section>

      <section>
        <h2>Audit Log</h2>
        {auditLog === null ? (
          <LoadingIndicator message="Loading audit log…" />
        ) : auditLog.length === 0 ? (
          <p className={styles.empty}>No audit events yet.</p>
        ) : (
          <div className={styles.tableWrapper}>
            <table className={styles.table}>
              <thead>
                <tr>
                  <th>When</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Detail</th>
                </tr>
              </thead>
              <tbody>
                {auditLog.map((entry) => (
                  <tr key={entry.id}>
                    <td>{new Date(entry.created_at).toLocaleString()}</td>
                    <td>{entry.user_id ?? "—"}</td>
                    <td>{entry.action}</td>
                    <td>{entry.detail ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
