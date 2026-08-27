import { requestJson } from "./client";
import type { Matter, MatterDetail } from "../types/matter";

export function createMatter(name: string, description: string | null): Promise<Matter> {
  return requestJson<Matter>("/matters", { method: "POST", body: { name, description } });
}

export function listMatters(): Promise<Matter[]> {
  return requestJson<Matter[]>("/matters");
}

export function getMatterDetail(matterId: number): Promise<MatterDetail> {
  return requestJson<MatterDetail>(`/matters/${matterId}`);
}

export function deleteMatter(matterId: number): Promise<void> {
  return requestJson<void>(`/matters/${matterId}`, { method: "DELETE" });
}
