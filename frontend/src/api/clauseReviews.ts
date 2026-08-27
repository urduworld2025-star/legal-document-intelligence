import { requestJson } from "./client";
import type { ClauseReview } from "../types/user";

export function listClauseReviews(matterId: number, documentId: number): Promise<ClauseReview[]> {
  return requestJson<ClauseReview[]>(`/matters/${matterId}/documents/${documentId}/review`);
}

export function markClauseReviewed(
  matterId: number,
  documentId: number,
  clauseIndex: number
): Promise<ClauseReview> {
  return requestJson<ClauseReview>(
    `/matters/${matterId}/documents/${documentId}/review/${clauseIndex}`,
    { method: "POST" }
  );
}

export function unmarkClauseReviewed(
  matterId: number,
  documentId: number,
  clauseIndex: number
): Promise<void> {
  return requestJson<void>(
    `/matters/${matterId}/documents/${documentId}/review/${clauseIndex}`,
    { method: "DELETE" }
  );
}
