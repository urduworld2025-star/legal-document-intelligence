// Mirrors src/legalintel/models/matter.py, but sharpens `result` into a
// discriminated union keyed on `analysis_type` — the backend types it as a
// generic dict since it's stored as an opaque JSON blob, but the frontend
// knows exactly which shape each analysis_type produced.

import type { ClauseExtractionResult, DocumentClassificationResult, ParsedDocument } from "./api";
import type { TrackedDocket } from "./docket";

export interface Matter {
  id: number;
  name: string;
  description: string | null;
  created_by: number | null;
  created_at: string;
}

interface MatterDocumentBase {
  id: number;
  matter_id: number;
  source_filename: string;
  created_at: string;
}

export type MatterDocument =
  | (MatterDocumentBase & { analysis_type: "parse"; result: ParsedDocument })
  | (MatterDocumentBase & { analysis_type: "extract_clauses"; result: ClauseExtractionResult })
  | (MatterDocumentBase & { analysis_type: "classify"; result: DocumentClassificationResult });

export interface MatterDetail {
  matter: Matter;
  documents: MatterDocument[];
  tracked_dockets: TrackedDocket[];
}
