// Mirrors src/legalintel/models/document.py 1:1.

export interface ParsedPage {
  page_number: number | null;
  text: string;
}

export interface ParsedDocument {
  source_filename: string;
  file_type: "pdf" | "docx";
  matter_id: number | null;
  pages: ParsedPage[];
  full_text: string;
  parsed_at: string;
}

export type RiskLevel = "HIGH" | "MEDIUM" | "INFORMATIONAL";
export type ConfidenceBand = "HIGH" | "MEDIUM" | "LOW";

export interface ClauseMatch {
  category: string;
  text: string;
  confidence: number;
  char_start: number | null;
  char_end: number | null;
  risk_level: RiskLevel | null;
  confidence_band: ConfidenceBand | null;
  possible_negation: boolean;
}

export interface RiskSummary {
  highest_risk_level: RiskLevel | null;
  counts_by_level: Record<RiskLevel, number>;
}

export interface ClauseExtractionResult {
  document: ParsedDocument;
  clauses: ClauseMatch[];
  risk_summary: RiskSummary;
}

export type DocumentType = "Contract" | "Email" | "Other";

export interface DocumentClassification {
  predicted_type: DocumentType;
  confidence: number;
  probabilities: Record<DocumentType, number>;
}

export interface DocumentClassificationResult {
  document: ParsedDocument;
  classification: DocumentClassification;
}
