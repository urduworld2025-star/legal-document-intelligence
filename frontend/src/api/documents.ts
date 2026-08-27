import { postMultipart } from "./client";
import type { ClauseExtractionResult, DocumentClassificationResult, ParsedDocument } from "../types/api";

export function parseDocument(file: File, matterId: number | null): Promise<ParsedDocument> {
  return postMultipart<ParsedDocument>("/documents/parse", file, matterId);
}

export function extractClauses(file: File, matterId: number | null): Promise<ClauseExtractionResult> {
  return postMultipart<ClauseExtractionResult>("/documents/extract-clauses", file, matterId);
}

export function classifyDocument(file: File, matterId: number | null): Promise<DocumentClassificationResult> {
  return postMultipart<DocumentClassificationResult>("/documents/classify", file, matterId);
}
