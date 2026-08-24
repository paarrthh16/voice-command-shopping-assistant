import { useEffect, useState } from "react";
import * as api from "../api.js";
import ProductCard from "./ProductCard.jsx";

/**
 * Presentational list of suggestions. Used by the section below and by the
 * voice panel when a "show recommendations" command is processed.
 */
export function RecommendationList({ recommendations, adding, onAdd }) {
  return (
    <ul className="product-grid">
      {recommendations.map(({ product, reasons }) => (
        <ProductCard
          key={product.id}
          product={product}
          adding={adding}
          onAdd={onAdd}
          actionLabel="Add"
          ariaLabel={`Add ${product.name} to list from suggestions`}
        >
          <p className="product-reason">{reasons.join(" · ")}</p>
        </ProductCard>
      ))}
    </ul>
  );
}

/**
 * Smart Suggestions section. Reloads whenever the shopping list changes, so
 * marking an item as bought feeds straight back into the recommendations.
 */
export default function Recommendations({ listVersion, adding, onAdd }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);

    api
      .getRecommendations()
      .then((response) => {
        if (!cancelled) {
          setData(response);
          setError("");
        }
      })
      .catch((loadError) => {
        if (!cancelled) setError(loadError.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [listVersion]);

  return (
    <section className="card suggestions">
      <div className="card-header">
        <div>
          <h2>Suggested for you</h2>
          <p className="card-subtitle">From your habits, the season and current offers</p>
        </div>
        {data?.season && <span className="season-badge">{data.season}</span>}
      </div>

      {loading && (
        <p className="status loading">
          <span className="spinner" aria-hidden="true" />
          Loading suggestions…
        </p>
      )}

      {!loading && error && <p className="status">Suggestions are unavailable right now.</p>}

      {!loading && !error && data && (
        <>
          <p className="status subtle">{data.message}</p>
          {data.recommendations.length === 0 ? (
            <p className="status">Nothing to suggest yet. Add and tick off a few items first.</p>
          ) : (
            <RecommendationList
              recommendations={data.recommendations}
              adding={adding}
              onAdd={onAdd}
            />
          )}
        </>
      )}
    </section>
  );
}
