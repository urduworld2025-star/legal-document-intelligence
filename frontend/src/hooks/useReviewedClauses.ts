import { useCallback, useState } from "react";

export function useReviewedClauses() {
  const [reviewed, setReviewed] = useState<Set<number>>(new Set());

  const toggle = useCallback((index: number) => {
    setReviewed((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  }, []);

  const reset = useCallback(() => setReviewed(new Set()), []);

  return { reviewed, toggle, reset };
}
