import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { search } from "../api/search";
import { ApiError } from "../api/client";
import { formatApiError } from "../utils/formatApiError";
import { ErrorBanner } from "../components/ErrorBanner";
import { LoadingIndicator } from "../components/LoadingIndicator";
import type { SearchResult, SearchResultType } from "../types/search";
import styles from "./SearchResultsPage.module.css";

const SECTION_TITLES: Record<SearchResultType, string> = {
  matter: "Matters",
  document: "Documents",
  docket: "Dockets",
};

const SECTION_ORDER: SearchResultType[] = ["matter", "document", "docket"];

export function SearchResultsPage() {
  const [searchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";

  const [results, setResults] = useState<SearchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    setResults(null);
    setError(null);
    search(query)
      .then(setResults)
      .catch((err) => setError(err instanceof ApiError ? formatApiError(err) : "Unexpected error."));
  }, [query]);

  const grouped = SECTION_ORDER.map((type) => ({
    type,
    items: (results ?? []).filter((r) => r.type === type),
  })).filter((group) => group.items.length > 0);

  return (
    <div className={styles.page}>
      <header>
        <h1>Search</h1>
        <p className={styles.subtitle}>
          {query ? (
            <>
              Results for <strong>&ldquo;{query}&rdquo;</strong>
            </>
          ) : (
            "Enter a search term above to get started."
          )}
        </p>
      </header>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {query.trim().length > 0 && query.trim().length < 2 ? (
        <p className={styles.empty}>Type at least 2 characters to search.</p>
      ) : results === null ? (
        <LoadingIndicator message="Searching…" />
      ) : grouped.length === 0 ? (
        <p className={styles.empty}>No matches found.</p>
      ) : (
        <div className={styles.sections}>
          {grouped.map((group) => (
            <section key={group.type}>
              <h2>{SECTION_TITLES[group.type]}</h2>
              <ul className={styles.list}>
                {group.items.map((result, index) => (
                  <li key={`${result.type}-${result.document_id ?? result.docket_id ?? result.matter_id}-${index}`}>
                    <Link to={`/matters/${result.matter_id}`} className={styles.resultLink}>
                      <span className={styles.resultTitle}>{result.title}</span>
                      {result.type !== "matter" && (
                        <span className={styles.resultMatter}>in {result.matter_name}</span>
                      )}
                      {result.snippet && <span className={styles.resultSnippet}>{result.snippet}</span>}
                    </Link>
                  </li>
                ))}
              </ul>
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
