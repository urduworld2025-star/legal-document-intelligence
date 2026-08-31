import { requestJson } from "./client";
import type { SearchResult } from "../types/search";

export function search(query: string): Promise<SearchResult[]> {
  return requestJson<SearchResult[]>(`/search?q=${encodeURIComponent(query)}`);
}
