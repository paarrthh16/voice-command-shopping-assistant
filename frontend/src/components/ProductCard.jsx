import { CURRENCY } from "../api.js";
import ProductImage from "../productImages.jsx";

/**
 * One product card, shared by the catalog, search results, suggestions and
 * substitutes so all four look and behave identically.
 *
 * "In stock" is the default, expected state for a card the shop is even
 * showing, so it isn't marked at all — an enabled Add button already implies
 * it. Only the exception (unavailable) gets a visible status.
 */
export default function ProductCard({
  product,
  actionLabel = "Add",
  ariaLabel,
  onAdd,
  adding = false,
  variant = "",
  children,
}) {
  return (
    <li className={`product-card ${variant}`.trim()}>
      <ProductImage product={product} size="portrait" />

      <div className="product-card-body">
        <span className="item-name">{product.name}</span>
        <span className="product-meta">
          {[product.brand, product.size].filter(Boolean).join(" · ")}
        </span>

        {children}

        <div className="product-card-footer">
          <span className="result-price">
            {CURRENCY}
            {product.price}
            {!product.available && <span className="unavailable-badge">Unavailable</span>}
          </span>

          <button
            type="button"
            className="card-add"
            disabled={adding || !product.available}
            aria-label={ariaLabel || `Add ${product.name} to list`}
            onClick={() => onAdd({ product_id: product.id, quantity: 1 })}
          >
            {product.available ? actionLabel : "—"}
          </button>
        </div>
      </div>
    </li>
  );
}
