import { useState } from "react";

/**
 * Manual fallback for adding an item. Voice is the primary path, so this is
 * visually demoted to a single quiet row at the foot of the list.
 */
export default function AddItemForm({ onAdd, adding }) {
  const [name, setName] = useState("");
  const [quantity, setQuantity] = useState(1);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!name.trim()) return;

    const added = await onAdd({ name: name.trim(), quantity: Number(quantity) || 1 });
    if (added) {
      setName("");
      setQuantity(1);
    }
  };

  return (
    <div className="manual-add">
      <span className="block-label">Or add manually</span>
      <form className="add-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={name}
          placeholder="Item name, e.g. Milk"
          aria-label="Item name"
          onChange={(event) => setName(event.target.value)}
        />
        <input
          type="number"
          min="1"
          max="999"
          value={quantity}
          aria-label="Quantity"
          onChange={(event) => setQuantity(event.target.value)}
        />
        <button type="submit" className="button-quiet" disabled={adding || !name.trim()}>
          {adding ? "Adding…" : "Add"}
        </button>
      </form>
    </div>
  );
}
