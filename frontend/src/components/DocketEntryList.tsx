import type { DocketEntry } from "../types/docket";
import styles from "./DocketEntryList.module.css";

interface DocketEntryListProps {
  entries: DocketEntry[];
}

export function DocketEntryList({ entries }: DocketEntryListProps) {
  if (entries.length === 0) {
    return <p className={styles.empty}>No filings recorded yet — click "Check Now" first.</p>;
  }

  return (
    <ul className={styles.list}>
      {entries.map((entry) => (
        <li key={entry.courtlistener_entry_id} className={styles.item}>
          <div className={styles.itemHeader}>
            {entry.entry_number !== null && <span className={styles.entryNumber}>#{entry.entry_number}</span>}
            {entry.date_filed && <span className={styles.date}>{entry.date_filed}</span>}
          </div>
          <p className={styles.description}>{entry.description || "(no description provided)"}</p>
        </li>
      ))}
    </ul>
  );
}
