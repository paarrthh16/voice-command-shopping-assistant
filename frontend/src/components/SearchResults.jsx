import ProductCard from "./ProductCard.jsx";
import { AlertIcon, SearchIcon } from "../icons.jsx";

/**
 * Results of a SEARCH_PRODUCT command, plus alternatives for anything that is
 * out of stock. Adding from here reuses the same shopping-list call as the
 * catalog and the voice ADD command.
 */
export default function SearchResults({ results, substitutes = [], adding, onAdd }) {
  return (
    <div className="search-block">
      {results.length === 0 ? (
        <div className="empty-state compact">
          <span className="empty-mark"><SearchIcon /></span>
          <p>
            No products found matching your search.
            <br />
            Try changing the brand, size or price range.
          </p>
        </div>
      ) : (
        <>
          <div className="results-header">
            <span className="block-label">Search results</span>
            <span className="count">
              {results.length} product{results.length === 1 ? "" : "s"} found
            </span>
          </div>
          <ul className="product-grid">
            {results.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                adding={adding}
                onAdd={onAdd}
                actionLabel="Add"
                ariaLabel={`Add ${product.name} to list from search results`}
              />
            ))}
          </ul>
        </>
      )}

      {substitutes.map((group) => (
        <div key={group.for_product} className="substitute-block">
          <p className="substitute-heading">
            <AlertIcon />
            <span><strong>{group.for_product}</strong> is currently unavailable — you might like these instead:</span>
          </p>
          <ul className="product-grid">
            {group.alternatives.map((alternative) => (
              <ProductCard
                key={alternative.id}
                product={alternative}
                adding={adding}
                onAdd={onAdd}
                variant="substitute"
                actionLabel="Add"
                ariaLabel={`Add ${alternative.name} to list as a substitute`}
              />
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
