// Mirrors src/legalintel/models/docket.py 1:1.

export interface TrackedDocket {
  id: number;
  courtlistener_docket_id: number;
  court: string | null;
  docket_number: string | null;
  case_name: string | null;
  matter_id: number | null;
  created_at: string;
  last_checked_at: string | null;
}

export interface DocketEntry {
  courtlistener_entry_id: number;
  entry_number: number | null;
  description: string;
  date_filed: string | null;
}

export interface DocketAlert {
  id: number;
  tracked_docket_id: number;
  created_at: string;
  new_entry_count: number;
  new_entry_ids: number[];
}

export interface DocketCheckResult {
  tracked_docket_id: number;
  checked_at: string;
  new_entries: DocketEntry[];
  alert_created: boolean;
  alert: DocketAlert | null;
}
