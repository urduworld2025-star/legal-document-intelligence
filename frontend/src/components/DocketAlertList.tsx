import { DocketEntryList } from "./DocketEntryList";
import type { DocketAlert, DocketEntry } from "../types/docket";
import styles from "./DocketAlertList.module.css";

interface DocketAlertListProps {
  alerts: DocketAlert[];
  entries: DocketEntry[];
}

export function DocketAlertList({ alerts, entries }: DocketAlertListProps) {
  if (alerts.length === 0) {
    return <p className={styles.empty}>No alerts yet.</p>;
  }

  const entriesById = new Map(entries.map((e) => [e.courtlistener_entry_id, e]));

  return (
    <ul className={styles.list}>
      {alerts.map((alert) => {
        const alertEntries = alert.new_entry_ids
          .map((id) => entriesById.get(id))
          .filter((e): e is DocketEntry => e !== undefined);

        return (
          <li key={alert.id} className={styles.item}>
            <div className={styles.itemHeader}>
              <span className={styles.count}>{alert.new_entry_count} new entries</span>
              <span className={styles.date}>{new Date(alert.created_at).toLocaleString()}</span>
            </div>
            {alertEntries.length > 0 ? (
              <DocketEntryList entries={alertEntries} />
            ) : (
              <p className={styles.missingDetail}>
                Filing details for this alert aren't available (may have been superseded by a later check).
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
