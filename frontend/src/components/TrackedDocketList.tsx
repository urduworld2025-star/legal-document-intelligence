import { useState } from "react";
import { checkDocket, listDocketAlerts, listDocketEntries } from "../api/dockets";
import { ApiError } from "../api/client";
import { formatApiError } from "../utils/formatApiError";
import { ErrorBanner } from "./ErrorBanner";
import { DocketAlertList } from "./DocketAlertList";
import { DocketEntryList } from "./DocketEntryList";
import type { DocketAlert, DocketCheckResult, DocketEntry, TrackedDocket } from "../types/docket";
import styles from "./TrackedDocketList.module.css";

interface TrackedDocketListProps {
  dockets: TrackedDocket[];
  checkDisabled?: boolean;
}

export function TrackedDocketList({ dockets, checkDisabled = false }: TrackedDocketListProps) {
  if (dockets.length === 0) {
    return <p className={styles.empty}>No dockets tracked for this matter yet.</p>;
  }

  return (
    <ul className={styles.list}>
      {dockets.map((docket) => (
        <TrackedDocketRow key={docket.id} docket={docket} checkDisabled={checkDisabled} />
      ))}
    </ul>
  );
}

interface TrackedDocketRowProps {
  docket: TrackedDocket;
  checkDisabled: boolean;
}

function TrackedDocketRow({ docket, checkDisabled }: TrackedDocketRowProps) {
  const [checking, setChecking] = useState(false);
  const [checkResult, setCheckResult] = useState<DocketCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [alertsExpanded, setAlertsExpanded] = useState(false);
  const [alerts, setAlerts] = useState<DocketAlert[] | null>(null);
  const [entriesExpanded, setEntriesExpanded] = useState(false);
  const [entries, setEntries] = useState<DocketEntry[] | null>(null);

  async function handleCheck() {
    setChecking(true);
    setError(null);
    try {
      const result = await checkDocket(docket.id);
      setCheckResult(result);
      if (alertsExpanded) {
        setAlerts(await listDocketAlerts(docket.id));
      }
      if (entriesExpanded || result.new_entries.length > 0) {
        setEntries(await listDocketEntries(docket.id));
      }
    } catch (err) {
      setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
    } finally {
      setChecking(false);
    }
  }

  async function toggleAlerts() {
    if (!alertsExpanded) {
      try {
        const [alertsResult, entriesResult] = await Promise.all([
          alerts === null ? listDocketAlerts(docket.id) : Promise.resolve(alerts),
          entries === null ? listDocketEntries(docket.id) : Promise.resolve(entries),
        ]);
        setAlerts(alertsResult);
        setEntries(entriesResult);
      } catch (err) {
        setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
      }
    }
    setAlertsExpanded((expanded) => !expanded);
  }

  async function toggleEntries() {
    if (!entriesExpanded) {
      try {
        setEntries(await listDocketEntries(docket.id));
      } catch (err) {
        setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error.");
      }
    }
    setEntriesExpanded((expanded) => !expanded);
  }

  return (
    <li className={styles.row}>
      <div className={styles.header}>
        <div>
          <span className={styles.caseName}>{docket.case_name ?? `Docket ${docket.courtlistener_docket_id}`}</span>
          {docket.docket_number && <span className={styles.docketNumber}> ({docket.docket_number})</span>}
        </div>
        <button
          type="button"
          onClick={handleCheck}
          disabled={checking || checkDisabled}
          title={checkDisabled ? "Your role doesn't include docket checks" : undefined}
        >
          {checking ? "Checking…" : "Check Now"}
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {checkResult && (
        <div className={styles.checkResult}>
          <p className={styles.checkSummary}>
            {checkResult.alert_created
              ? `Found ${checkResult.new_entries.length} new ${checkResult.new_entries.length === 1 ? "entry" : "entries"}:`
              : "No new entries since the last check."}
          </p>
          {checkResult.new_entries.length > 0 && <DocketEntryList entries={checkResult.new_entries} />}
        </div>
      )}

      <div className={styles.toggleRow}>
        <button type="button" className={styles.alertsToggle} onClick={toggleAlerts}>
          {alertsExpanded ? "Hide alerts" : "Show alerts"}
        </button>
        <button type="button" className={styles.alertsToggle} onClick={toggleEntries}>
          {entriesExpanded ? "Hide filings" : "Show filings"}
        </button>
      </div>
      {alertsExpanded && alerts && <DocketAlertList alerts={alerts} entries={entries ?? []} />}
      {entriesExpanded && entries && <DocketEntryList entries={entries} />}
    </li>
  );
}
