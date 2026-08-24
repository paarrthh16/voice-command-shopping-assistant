import { formatAmount } from "../format.js";
import ProductImage from "../productImages.jsx";
import { CartIcon, MinusIcon, PlusIcon, RemoveIcon } from "../icons.jsx";
import AddItemForm from "./AddItemForm.jsx";

function groupByCategory(items) {
  const groups = new Map();
  items.forEach((item) => {
    const group = groups.get(item.category) || [];
    group.push(item);
    groups.set(item.category, group);
  });
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b));
}

function ShoppingListRow({ item, busy, onUpdate, onDelete }) {
  const changeQuantity = (delta) => {
    const next = item.quantity + delta;
    if (next < 1) return;
    onUpdate(item.id, { quantity: next });
  };

  return (
    <li className={`list-row ${item.completed ? "completed" : ""} ${busy ? "busy" : ""}`}>
      <input
        type="checkbox"
        className="list-check"
        checked={item.completed}
        disabled={busy}
        aria-label={`Mark ${item.name} as bought`}
        onChange={(event) => onUpdate(item.id, { completed: event.target.checked })}
      />

      <ProductImage product={item} size="row" />

      <span className="row-text">
        <span className="item-name">{item.name}</span>
        <span className="row-meta">{item.category}</span>
      </span>

      <div className="quantity-control">
        <button
          type="button"
          disabled={busy || item.quantity <= 1}
          aria-label={`Decrease quantity of ${item.name}`}
          onClick={() => changeQuantity(-1)}
        >
          <MinusIcon />
        </button>
        <span className="quantity-value">{formatAmount(item.quantity, item.unit)}</span>
        <button
          type="button"
          disabled={busy}
          aria-label={`Increase quantity of ${item.name}`}
          onClick={() => changeQuantity(1)}
        >
          <PlusIcon />
        </button>
      </div>

      <button
        type="button"
        className="delete-button"
        disabled={busy}
        aria-label={`Remove ${item.name}`}
        onClick={() => onDelete(item.id)}
      >
        <RemoveIcon />
      </button>
    </li>
  );
}

export default function ShoppingList({
  items,
  loading,
  busyItemIds,
  onUpdate,
  onDelete,
  onAdd,
  adding,
}) {
  const remaining = items.filter((item) => !item.completed).length;

  return (
    <section className="card shopping-list">
      <div className="card-header">
        <div>
          <h2>Your shopping list</h2>
          <p className="card-subtitle">Say what you need, or add it by hand below</p>
        </div>
        {!loading && items.length > 0 && (
          <span className="count-pill">
            {remaining} of {items.length} left
          </span>
        )}
      </div>

      {loading && (
        <p className="status loading">
          <span className="spinner" aria-hidden="true" />
          Loading your list…
        </p>
      )}

      {!loading && items.length === 0 && (
        <div className="empty-state">
          <span className="empty-mark"><CartIcon /></span>
          <p className="empty-title">Your list is ready</p>
          <p>Try saying:</p>
          <ul className="empty-examples">
            <li>"Add milk"</li>
            <li>"Add two apples"</li>
            <li>"दूध जोड़ो"</li>
          </ul>
        </div>
      )}

      {!loading &&
        groupByCategory(items).map(([category, categoryItems]) => (
          <div key={category} className="category-group">
            <h3 className="category-title">
              {category} · {categoryItems.length} item{categoryItems.length === 1 ? "" : "s"}
            </h3>
            <ul className="list">
              {categoryItems.map((item) => (
                <ShoppingListRow
                  key={item.id}
                  item={item}
                  busy={busyItemIds.includes(item.id)}
                  onUpdate={onUpdate}
                  onDelete={onDelete}
                />
              ))}
            </ul>
          </div>
        ))}

      <AddItemForm onAdd={onAdd} adding={adding} />
    </section>
  );
}
