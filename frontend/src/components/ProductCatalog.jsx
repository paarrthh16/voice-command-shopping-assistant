import ProductCard from "./ProductCard.jsx";
import { SearchIcon } from "../icons.jsx";

/**
 * Browse-and-filter view of the whole catalog — the secondary, de-emphasized
 * path. The assistant (voice/typed command + list + suggestions) is home;
 * this is one tap away for someone who genuinely wants to scroll the shelf.
 */
export default function ProductCatalog({
  products,
  categories,
  loading,
  search,
  category,
  adding,
  onSearchChange,
  onCategoryChange,
  onAdd,
}) {
  return (
    <section className="card discover">
      <div className="card-header">
        <div>
          <h2>Browse the catalog</h2>
          <p className="card-subtitle">Search, filter by category, or add anything straight from a card.</p>
        </div>
        {!loading && <span className="count">{products.length} products</span>}
      </div>

      <div className="filters">
        <div className="search-field">
          <span className="search-icon"><SearchIcon /></span>
          <input
            type="search"
            value={search}
            placeholder="Search products or brands…"
            aria-label="Search products"
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
        <select
          value={category}
          aria-label="Filter by category"
          onChange={(event) => onCategoryChange(event.target.value)}
        >
          <option value="">All categories</option>
          {categories.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </div>

      {loading && (
        <p className="status loading">
          <span className="spinner" aria-hidden="true" />
          Loading products…
        </p>
      )}

      {!loading && products.length === 0 && (
        <p className="status">No products match that search.</p>
      )}

      {!loading && products.length > 0 && (
        <ul className="product-grid catalog-grid">
          {products.map((product) => (
            <ProductCard
              key={product.id}
              product={product}
              adding={adding}
              onAdd={onAdd}
              actionLabel="Add"
              ariaLabel={`Add ${product.name} to list`}
            />
          ))}
        </ul>
      )}
    </section>
  );
}
