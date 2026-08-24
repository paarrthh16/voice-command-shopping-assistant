/** Display helpers shared by the shopping list and the voice panel. */

// Units that never take a plural 's': measures and 'dozen'.
const INVARIANT_UNITS = new Set(["kg", "g", "l", "ml", "dozen"]);
const IRREGULAR_PLURALS = { loaf: "loaves", box: "boxes", pouch: "pouches" };

export function formatQuantity(quantity) {
  return Number.isInteger(quantity) ? String(quantity) : String(Number(quantity.toFixed(2)));
}

/** Render '2 bottles', '1 kg', or plain '5' when the unit is just a count. */
export function formatAmount(quantity, unit) {
  const amount = formatQuantity(quantity);
  if (!unit || unit === "piece") return amount;
  if (quantity === 1 || INVARIANT_UNITS.has(unit)) return `${amount} ${unit}`;
  return `${amount} ${IRREGULAR_PLURALS[unit] || `${unit}s`}`;
}
