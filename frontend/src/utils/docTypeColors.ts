import type { DocumentType } from "../types/api";

// Fixed mapping, not a hash: document types are a known small enum (unlike
// clause categories), so each one gets an intentional, consistent color.
const DOC_TYPE_COLORS: Record<DocumentType, string> = {
  Contract: "#818cf8", // == --accent-hover
  Email: "#34d399",
  Other: "#9aa0ab", // == --text-muted
};

export function colorForDocType(type: DocumentType): string {
  return DOC_TYPE_COLORS[type];
}
