// Mirrors src/legalintel/models/search.py

export type SearchResultType = "matter" | "document" | "docket";

export interface SearchResult {
  type: SearchResultType;
  matter_id: number;
  matter_name: string;
  title: string;
  snippet: string | null;
  document_id: number | null;
  docket_id: number | null;
}
