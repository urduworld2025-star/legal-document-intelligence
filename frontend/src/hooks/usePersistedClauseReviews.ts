import { useCallback, useEffect, useState } from "react";
import { listClauseReviews, markClauseReviewed, unmarkClauseReviewed } from "../api/clauseReviews";
import type { ClauseReview } from "../types/user";

export function usePersistedClauseReviews(matterId: number, documentId: number, enabled: boolean) {
  const [reviews, setReviews] = useState<ClauseReview[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!enabled) return;
    listClauseReviews(matterId, documentId)
      .then((result) => {
        setReviews(result);
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, [matterId, documentId, enabled]);

  const reviewed = new Set(reviews.map((r) => r.clause_index));

  const reviewerFor = useCallback(
    (index: number) => reviews.find((r) => r.clause_index === index)?.reviewed_by_name,
    [reviews]
  );

  const toggle = useCallback(
    async (index: number) => {
      if (reviewed.has(index)) {
        await unmarkClauseReviewed(matterId, documentId, index);
        setReviews((prev) => prev.filter((r) => r.clause_index !== index));
      } else {
        const review = await markClauseReviewed(matterId, documentId, index);
        setReviews((prev) => [...prev.filter((r) => r.clause_index !== index), review]);
      }
    },
    [matterId, documentId, reviewed]
  );

  return { reviewed, reviewerFor, toggle, loaded };
}
