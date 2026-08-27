import { requestJson } from "./client";
import type { DocketAlert, DocketCheckResult, DocketEntry, TrackedDocket } from "../types/docket";

export function trackDocket(courtlistenerDocketId: number, matterId: number | null): Promise<TrackedDocket> {
  return requestJson<TrackedDocket>("/dockets/track", {
    method: "POST",
    body: { courtlistener_docket_id: courtlistenerDocketId, matter_id: matterId },
  });
}

export function listDockets(): Promise<TrackedDocket[]> {
  return requestJson<TrackedDocket[]>("/dockets");
}

export function checkDocket(trackedDocketId: number): Promise<DocketCheckResult> {
  return requestJson<DocketCheckResult>(`/dockets/${trackedDocketId}/check`, { method: "POST" });
}

export function listDocketAlerts(trackedDocketId: number): Promise<DocketAlert[]> {
  return requestJson<DocketAlert[]>(`/dockets/${trackedDocketId}/alerts`);
}

export function listDocketEntries(trackedDocketId: number): Promise<DocketEntry[]> {
  return requestJson<DocketEntry[]>(`/dockets/${trackedDocketId}/entries`);
}
