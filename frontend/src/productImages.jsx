/**
 * Original product illustrations — layered-gradient SVG, not photography.
 *
 * There is no image-generation tool or licensed photo source available in
 * this environment, and scraping unlicensed stock photography was explicitly
 * ruled out, so this is the legitimate substitute: naturalistic color and
 * soft directional shading (one highlight gradient + one contact shadow per
 * object) so items read as "photographed on a plain surface" rather than as
 * flat icons or emoji. Every symbol is rendered once here and referenced by
 * <use>, so a 54-card grid shares one set of defs instead of duplicating
 * markup per card.
 *
 * Swap path: ProductImage below is the only place that resolves a product to
 * a visual. Replacing this system with real photography later means editing
 * ProductImage's resolve() function — no caller (ProductCard, ShoppingList,
 * SearchResults, Recommendations) needs to change.
 */

const TILE_BY_CATEGORY = {
  Dairy: "var(--tile-dairy)",
  Produce: "var(--tile-produce)",
  Bakery: "var(--tile-bakery)",
  Beverages: "var(--tile-bev)",
  Snacks: "var(--tile-snacks)",
  "Personal Care": "var(--tile-personal)",
  Household: "var(--tile-household)",
};

// Exact catalog product names (lower-cased) mapped to a symbol id. Anything
// not listed here falls back to a category-level illustration, then to a
// monogram — every product still gets a real visual, never a broken image.
const SYMBOL_BY_PRODUCT = {
  milk: "milk", "toned milk": "milk", "almond milk": "milk-carton",
  curd: "curd", "greek yogurt": "curd", butter: "butter", "cheese slices": "cheese",
  paneer: "cheese", tofu: "cheese",
  apples: "apple", "organic apples": "apple", bananas: "banana",
  oranges: "citrus", "sweet lime": "citrus", mangoes: "mango",
  tomatoes: "tomato", onions: "onion", potatoes: "potato",
  spinach: "leafy", "fenugreek leaves": "leafy",
  bread: "bread", "brown bread": "bread", "pav buns": "buns", croissant: "croissant", rusk: "rusk",
  water: "bottle-water", soda: "can", "orange juice": "juice", cola: "can",
  "green tea": "cup", tea: "cup", coffee: "cup",
  "potato chips": "chip-bag", popcorn: "chip-bag", biscuits: "biscuits",
  chocolate: "chocolate", namkeen: "chip-bag", almonds: "nuts", cashews: "nuts",
  toothpaste: "toothpaste", "herbal toothpaste": "toothpaste", toothbrush: "toothbrush",
  shampoo: "bottle-pump", "herbal shampoo": "bottle-pump", soap: "soap", handwash: "bottle-pump",
  "dish soap": "bottle-pump", "dish bar": "soap", detergent: "box",
  "detergent liquid": "bottle-pump", "floor cleaner": "bottle-pump",
  "garbage bags": "roll", "toilet paper": "roll", "aluminium foil": "roll",
};

const CATEGORY_FALLBACK_SYMBOL = {
  Dairy: "milk", Produce: "apple", Bakery: "bread", Beverages: "bottle-water",
  Snacks: "chip-bag", "Personal Care": "bottle-pump", Household: "box",
};

function resolve(product) {
  const key = (product?.name || "").trim().toLowerCase();
  const symbol = SYMBOL_BY_PRODUCT[key] || CATEGORY_FALLBACK_SYMBOL[product?.category] || null;
  const tile = TILE_BY_CATEGORY[product?.category] || "var(--tile-other)";
  return { symbol, tile };
}

/** Renders once near the app root; every ProductImage references these by id. */
export function ProductImageDefs() {
  return (
    <svg width="0" height="0" style={{ position: "absolute" }} aria-hidden="true">
      <defs>
        <linearGradient id="pg-cream" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FFFDF7" />
          <stop offset="1" stopColor="#EDE6D2" />
        </linearGradient>
        <linearGradient id="pg-white" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FFFFFF" />
          <stop offset="1" stopColor="#E7E4DA" />
        </linearGradient>
        <linearGradient id="pg-butter" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F6E7A8" />
          <stop offset="1" stopColor="#E3C15C" />
        </linearGradient>
        <linearGradient id="pg-yellow" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F6D65B" />
          <stop offset="1" stopColor="#D9A81E" />
        </linearGradient>
        <linearGradient id="pg-red" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#E06B52" />
          <stop offset="1" stopColor="#A83321" />
        </linearGradient>
        <linearGradient id="pg-orange" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F3A94E" />
          <stop offset="1" stopColor="#D97A1F" />
        </linearGradient>
        <linearGradient id="pg-green" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8FAE6B" />
          <stop offset="1" stopColor="#5C7A45" />
        </linearGradient>
        <linearGradient id="pg-mango" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#F3C24E" />
          <stop offset="0.6" stopColor="#EB9B3A" />
          <stop offset="1" stopColor="#D9601F" />
        </linearGradient>
        <linearGradient id="pg-tan" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#E7C393" />
          <stop offset="1" stopColor="#BE8A4C" />
        </linearGradient>
        <linearGradient id="pg-crust" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#E7B25F" />
          <stop offset="1" stopColor="#B57A34" />
        </linearGradient>
        <linearGradient id="pg-water" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#EAF3F1" />
          <stop offset="1" stopColor="#C3DAD6" />
        </linearGradient>
        <linearGradient id="pg-cola" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#5B4A3A" />
          <stop offset="1" stopColor="#2E241B" />
        </linearGradient>
        <linearGradient id="pg-juice" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F5B24A" />
          <stop offset="1" stopColor="#D97B1A" />
        </linearGradient>
        <linearGradient id="pg-coffee" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#8A5A38" />
          <stop offset="1" stopColor="#5C3A22" />
        </linearGradient>
        <linearGradient id="pg-choc" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#6B4A34" />
          <stop offset="1" stopColor="#3E281B" />
        </linearGradient>
        <linearGradient id="pg-nut" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#D9B283" />
          <stop offset="1" stopColor="#A87A47" />
        </linearGradient>
        <linearGradient id="pg-brass" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#C79657" />
          <stop offset="1" stopColor="#A8763A" />
        </linearGradient>
        <linearGradient id="pg-pine" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#3E5C4C" />
          <stop offset="1" stopColor="#223529" />
        </linearGradient>
        <radialGradient id="pg-shadow" cx="0.5" cy="0.5" r="0.5">
          <stop offset="0" stopColor="rgba(20,20,15,0.28)" />
          <stop offset="1" stopColor="rgba(20,20,15,0)" />
        </radialGradient>

        {/* ---- Dairy ---- */}
        <symbol id="pi-milk" viewBox="0 0 100 100">
          <ellipse cx="50" cy="90" rx="22" ry="4" fill="url(#pg-shadow)" />
          <path d="M40 12h20v9l8 11v50a5 5 0 0 1-5 5H37a5 5 0 0 1-5-5V32l8-11z" fill="url(#pg-white)" stroke="#C9C4B2" strokeWidth="1.2" />
          <rect x="40" y="12" width="20" height="7" rx="1.5" fill="url(#pg-pine)" />
          <rect x="32" y="48" width="36" height="15" fill="#2F4A3C" opacity="0.92" />
          <path d="M40 32l3-6h14l3 6" fill="none" stroke="#C9C4B2" strokeWidth="1" opacity="0.6" />
        </symbol>
        <symbol id="pi-curd" viewBox="0 0 100 100">
          <ellipse cx="50" cy="88" rx="24" ry="4" fill="url(#pg-shadow)" />
          <path d="M26 40h48l-5 40a6 6 0 0 1-6 5H37a6 6 0 0 1-6-5z" fill="url(#pg-white)" stroke="#C9C4B2" strokeWidth="1.2" />
          <ellipse cx="50" cy="40" rx="24" ry="7" fill="#F4F1E6" stroke="#C9C4B2" strokeWidth="1.2" />
          <ellipse cx="50" cy="39" rx="18" ry="4.5" fill="#FFFFFF" opacity="0.8" />
        </symbol>
        <symbol id="pi-butter" viewBox="0 0 100 100">
          <ellipse cx="50" cy="82" rx="26" ry="4" fill="url(#pg-shadow)" />
          <path d="M22 38l6-10h44l6 10v34a4 4 0 0 1-4 4H26a4 4 0 0 1-4-4z" fill="url(#pg-butter)" stroke="#C79A3E" strokeWidth="1.2" />
          <rect x="22" y="52" width="56" height="10" fill="#2F4A3C" opacity="0.9" />
        </symbol>
        <symbol id="pi-cheese" viewBox="0 0 100 100">
          <ellipse cx="50" cy="82" rx="24" ry="4" fill="url(#pg-shadow)" />
          <path d="M28 62l44-14v10l-44 14z" fill="url(#pg-yellow)" stroke="#C79A1F" strokeWidth="1" />
          <path d="M28 50l44-14v10l-44 14z" fill="url(#pg-yellow)" stroke="#C79A1F" strokeWidth="1" opacity="0.92" />
          <path d="M28 38l44-14v10l-44 14z" fill="url(#pg-yellow)" stroke="#C79A1F" strokeWidth="1" opacity="0.84" />
        </symbol>

        {/* ---- Produce ---- */}
        <symbol id="pi-apple" viewBox="0 0 100 100">
          <ellipse cx="50" cy="86" rx="22" ry="4" fill="url(#pg-shadow)" />
          <path d="M50 30c10-9 26-5 28 9 3 18-10 39-28 39S22 66 25 48c2-14 15-17 25-9z" fill="url(#pg-red)" stroke="#8C2C1D" strokeWidth="1" />
          <ellipse cx="42" cy="42" rx="6" ry="9" fill="#F3A88C" opacity="0.35" />
          <path d="M49 30c-2-6 0-12 6-16" fill="none" stroke="#5C7A45" strokeWidth="2.4" strokeLinecap="round" />
        </symbol>
        <symbol id="pi-banana" viewBox="0 0 100 100">
          <ellipse cx="52" cy="84" rx="24" ry="4" fill="url(#pg-shadow)" />
          <path d="M26 30c-6 18-2 40 16 50 14 8 30 2 34-10-14 4-24-2-28-12-4-10-2-22 6-30" fill="none" stroke="url(#pg-yellow)" strokeWidth="10" strokeLinecap="round" />
          <path d="M26 30c-6 18-2 40 16 50 14 8 30 2 34-10-14 4-24-2-28-12-4-10-2-22 6-30" fill="none" stroke="#B48415" strokeWidth="1.2" strokeLinecap="round" />
        </symbol>
        <symbol id="pi-citrus" viewBox="0 0 100 100">
          <ellipse cx="50" cy="86" rx="22" ry="4" fill="url(#pg-shadow)" />
          <circle cx="50" cy="54" r="26" fill="url(#pg-orange)" stroke="#B5641B" strokeWidth="1" />
          <path d="M50 28l3 8-3 4-3-4z" fill="#5C7A45" />
        </symbol>
        <symbol id="pi-mango" viewBox="0 0 100 100">
          <ellipse cx="50" cy="88" rx="22" ry="4" fill="url(#pg-shadow)" />
          <path d="M50 18c18 4 28 20 24 38-3 15-15 28-24 28s-21-13-24-28c-4-18 6-34 24-38z" fill="url(#pg-mango)" stroke="#C0641B" strokeWidth="1" />
          <path d="M52 16l6-8" stroke="#5C7A45" strokeWidth="3" strokeLinecap="round" />
        </symbol>
        <symbol id="pi-tomato" viewBox="0 0 100 100">
          <ellipse cx="50" cy="86" rx="22" ry="4" fill="url(#pg-shadow)" />
          <path d="M50 34c14 0 24 12 24 27s-11 27-24 27-24-12-24-27 10-27 24-27z" fill="url(#pg-red)" stroke="#8C2C1D" strokeWidth="1" />
          <path d="M50 34c-3-6-10-8-16-6M50 34c3-6 10-8 16-6" fill="none" stroke="#5C7A45" strokeWidth="2.4" strokeLinecap="round" />
        </symbol>
        <symbol id="pi-onion" viewBox="0 0 100 100">
          <ellipse cx="50" cy="86" rx="22" ry="4" fill="url(#pg-shadow)" />
          <path d="M50 28c16 4 22 20 20 34-2 14-10 24-20 24s-18-10-20-24c-2-14 4-30 20-34z" fill="url(#pg-tan)" stroke="#9C6B32" strokeWidth="1" />
          <path d="M50 28l2-12M50 28l-4-10" stroke="#B58A50" strokeWidth="1.6" strokeLinecap="round" fill="none" />
        </symbol>
        <symbol id="pi-potato" viewBox="0 0 100 100">
          <ellipse cx="50" cy="84" rx="24" ry="4" fill="url(#pg-shadow)" />
          <path d="M28 60c-4-12 2-24 14-28 10-4 22 0 28 10 6 10 4 24-6 30-12 8-30 2-36-12z" fill="url(#pg-tan)" stroke="#9C6B32" strokeWidth="1" />
          <circle cx="40" cy="52" r="1.6" fill="#7A4E22" />
          <circle cx="56" cy="58" r="1.6" fill="#7A4E22" />
        </symbol>
        <symbol id="pi-leafy" viewBox="0 0 100 100">
          <ellipse cx="50" cy="86" rx="22" ry="4" fill="url(#pg-shadow)" />
          <path d="M50 78V34" stroke="#4C6B3A" strokeWidth="2.4" strokeLinecap="round" />
          <path d="M50 40c-10-6-20-4-26 4 8 4 18 4 26-4z" fill="url(#pg-green)" />
          <path d="M50 52c10-6 20-4 26 4-8 4-18 4-26-4z" fill="url(#pg-green)" />
          <path d="M50 64c-10-6-20-4-26 4 8 4 18 4 26-4z" fill="url(#pg-green)" />
        </symbol>

        {/* ---- Bakery ---- */}
        <symbol id="pi-bread" viewBox="0 0 100 100">
          <ellipse cx="50" cy="82" rx="28" ry="4" fill="url(#pg-shadow)" />
          <path d="M18 52c0-18 14-30 32-30s32 12 32 30v16a6 6 0 0 1-6 6H24a6 6 0 0 1-6-6z" fill="url(#pg-crust)" stroke="#9C6423" strokeWidth="1.2" />
          <path d="M30 48c4-8 8-11 20-11s16 3 20 11" fill="none" stroke="#9C6423" strokeWidth="1.4" strokeLinecap="round" opacity="0.7" />
        </symbol>
        <symbol id="pi-buns" viewBox="0 0 100 100">
          <ellipse cx="50" cy="80" rx="26" ry="4" fill="url(#pg-shadow)" />
          <circle cx="34" cy="60" r="14" fill="url(#pg-crust)" stroke="#9C6423" strokeWidth="1" />
          <circle cx="58" cy="58" r="16" fill="url(#pg-crust)" stroke="#9C6423" strokeWidth="1" />
          <circle cx="76" cy="62" r="12" fill="url(#pg-crust)" stroke="#9C6423" strokeWidth="1" />
        </symbol>
        <symbol id="pi-croissant" viewBox="0 0 100 100">
          <ellipse cx="50" cy="76" rx="26" ry="4" fill="url(#pg-shadow)" />
          <path d="M20 62c4-22 20-34 34-30 10 3 8 12 0 12-14 0-20 8-16 18 3 8 14 10 22 4 6 12-6 22-20 20-14-2-24-12-20-24z" fill="url(#pg-crust)" stroke="#9C6423" strokeWidth="1" />
        </symbol>
        <symbol id="pi-rusk" viewBox="0 0 100 100">
          <ellipse cx="50" cy="82" rx="24" ry="4" fill="url(#pg-shadow)" />
          <rect x="24" y="34" width="52" height="16" rx="3" fill="url(#pg-tan)" stroke="#9C6423" strokeWidth="1" />
          <rect x="24" y="54" width="52" height="16" rx="3" fill="url(#pg-tan)" stroke="#9C6423" strokeWidth="1" />
        </symbol>

        {/* ---- Beverages ---- */}
        <symbol id="pi-bottle-water" viewBox="0 0 100 100">
          <ellipse cx="50" cy="90" rx="16" ry="3.5" fill="url(#pg-shadow)" />
          <path d="M42 10h16l3 12-3 6v54a5 5 0 0 1-5 5H47a5 5 0 0 1-5-5V28l-3-6z" fill="url(#pg-water)" stroke="#9FBDB9" strokeWidth="1.2" opacity="0.94" />
          <rect x="42" y="10" width="16" height="7" fill="url(#pg-pine)" />
          <rect x="40" y="42" width="20" height="9" fill="#FFFFFF" opacity="0.5" />
        </symbol>
        <symbol id="pi-can" viewBox="0 0 100 100">
          <ellipse cx="50" cy="88" rx="16" ry="3.5" fill="url(#pg-shadow)" />
          <path d="M38 20h24l2 8-2 54a4 4 0 0 1-4 4H42a4 4 0 0 1-4-4l-2-54z" fill="url(#pg-cola)" stroke="#241C14" strokeWidth="1" />
          <rect x="36" y="16" width="28" height="8" rx="3" fill="#181310" />
        </symbol>
        <symbol id="pi-juice" viewBox="0 0 100 100">
          <ellipse cx="50" cy="90" rx="16" ry="3.5" fill="url(#pg-shadow)" />
          <path d="M40 14h20l4 10v58a5 5 0 0 1-5 5H41a5 5 0 0 1-5-5V24z" fill="url(#pg-juice)" stroke="#B5641B" strokeWidth="1.2" />
          <rect x="40" y="14" width="20" height="8" fill="url(#pg-pine)" />
        </symbol>
        <symbol id="pi-cup" viewBox="0 0 100 100">
          <ellipse cx="46" cy="84" rx="22" ry="4" fill="url(#pg-shadow)" />
          <path d="M28 40h36l-4 34a6 6 0 0 1-6 5H38a6 6 0 0 1-6-5z" fill="url(#pg-coffee)" stroke="#3E281B" strokeWidth="1" />
          <path d="M64 46c10-2 16 4 14 12s-12 10-18 6" fill="none" stroke="#3E281B" strokeWidth="3" strokeLinecap="round" />
        </symbol>

        {/* ---- Snacks ---- */}
        <symbol id="pi-chip-bag" viewBox="0 0 100 100">
          <ellipse cx="50" cy="88" rx="24" ry="4" fill="url(#pg-shadow)" />
          <path d="M30 22h40l6 12-4 46a5 5 0 0 1-5 4H33a5 5 0 0 1-5-4l-4-46z" fill="url(#pg-orange)" stroke="#B5641B" strokeWidth="1.2" />
          <rect x="30" y="22" width="40" height="8" fill="#8C2C1D" opacity="0.85" />
        </symbol>
        <symbol id="pi-biscuits" viewBox="0 0 100 100">
          <ellipse cx="50" cy="82" rx="24" ry="4" fill="url(#pg-shadow)" />
          <circle cx="50" cy="64" r="18" fill="url(#pg-tan)" stroke="#9C6423" strokeWidth="1" />
          <circle cx="50" cy="46" r="18" fill="url(#pg-tan)" stroke="#9C6423" strokeWidth="1" />
          <circle cx="50" cy="46" r="4" fill="#9C6423" opacity="0.5" />
          <circle cx="42" cy="40" r="2" fill="#9C6423" opacity="0.5" />
          <circle cx="58" cy="52" r="2" fill="#9C6423" opacity="0.5" />
        </symbol>
        <symbol id="pi-chocolate" viewBox="0 0 100 100">
          <ellipse cx="50" cy="82" rx="26" ry="4" fill="url(#pg-shadow)" />
          <rect x="22" y="38" width="56" height="34" rx="3" fill="url(#pg-choc)" stroke="#241A10" strokeWidth="1" />
          <path d="M40 38v34M58 38v34M22 55h56" stroke="#241A10" strokeWidth="1.4" opacity="0.6" />
        </symbol>
        <symbol id="pi-nuts" viewBox="0 0 100 100">
          <ellipse cx="50" cy="82" rx="24" ry="4" fill="url(#pg-shadow)" />
          <path d="M28 56c0-16 14-24 22-24s22 8 22 24-12 22-22 22-22-6-22-22z" fill="url(#pg-nut)" stroke="#8A6136" strokeWidth="1" />
        </symbol>

        {/* ---- Personal care ---- */}
        <symbol id="pi-toothpaste" viewBox="0 0 100 100">
          <ellipse cx="50" cy="90" rx="24" ry="3.5" fill="url(#pg-shadow)" />
          <path d="M30 30h34l6 8v44a5 5 0 0 1-5 5H35a5 5 0 0 1-5-5V38z" fill="url(#pg-white)" stroke="#C9C4B2" strokeWidth="1.2" />
          <path d="M30 30l-6-8h20l4 8z" fill="url(#pg-brass)" />
          <rect x="25" y="54" width="45" height="8" fill="url(#pg-pine)" />
        </symbol>
        <symbol id="pi-toothbrush" viewBox="0 0 100 100">
          <ellipse cx="50" cy="90" rx="20" ry="3" fill="url(#pg-shadow)" />
          <rect x="46" y="18" width="8" height="56" rx="4" fill="url(#pg-white)" stroke="#C9C4B2" strokeWidth="1" />
          <rect x="40" y="14" width="20" height="14" rx="4" fill="url(#pg-pine)" />
        </symbol>
        <symbol id="pi-soap" viewBox="0 0 100 100">
          <ellipse cx="50" cy="80" rx="24" ry="4" fill="url(#pg-shadow)" />
          <rect x="24" y="52" width="52" height="24" rx="8" fill="url(#pg-brass)" stroke="#8C6129" strokeWidth="1" />
          <path d="M32 60c8-4 28-4 36 0" stroke="#8C6129" strokeWidth="1.2" fill="none" opacity="0.5" />
        </symbol>
        <symbol id="pi-bottle-pump" viewBox="0 0 100 100">
          <ellipse cx="50" cy="90" rx="18" ry="3.5" fill="url(#pg-shadow)" />
          <path d="M38 26h20v10l4 4v40a5 5 0 0 1-5 5H39a5 5 0 0 1-5-5V40l4-4z" fill="url(#pg-brass)" stroke="#8C6129" strokeWidth="1.2" />
          <rect x="44" y="10" width="8" height="18" rx="2" fill="url(#pg-pine)" />
          <path d="M52 14h10" stroke="#223529" strokeWidth="3" strokeLinecap="round" />
        </symbol>

        {/* ---- Household ---- */}
        <symbol id="pi-box" viewBox="0 0 100 100">
          <ellipse cx="50" cy="86" rx="26" ry="4" fill="url(#pg-shadow)" />
          <path d="M22 34l28-10 28 10-28 10z" fill="url(#pg-tan)" stroke="#9C6423" strokeWidth="1" />
          <path d="M22 34v38l28 10V44z" fill="url(#pg-tan)" stroke="#9C6423" strokeWidth="1" opacity="0.85" />
          <path d="M78 34v38l-28 10V44z" fill="url(#pg-tan)" stroke="#9C6423" strokeWidth="1" opacity="0.7" />
        </symbol>
        <symbol id="pi-roll" viewBox="0 0 100 100">
          <ellipse cx="50" cy="86" rx="22" ry="4" fill="url(#pg-shadow)" />
          <rect x="26" y="26" width="48" height="52" rx="10" fill="url(#pg-white)" stroke="#C9C4B2" strokeWidth="1" />
          <ellipse cx="50" cy="52" rx="9" ry="18" fill="var(--bg)" stroke="#C9C4B2" strokeWidth="1" />
        </symbol>
      </defs>
    </svg>
  );
}

/**
 * Resolves a catalog product to an illustration tile.
 * size: "row" (36–44px inline), "tile" (square card image), "portrait" (4:5 browse card).
 */
export default function ProductImage({ product, size = "tile", className = "" }) {
  const { symbol, tile } = resolve(product);
  const initial = (product?.name || "?").trim().charAt(0).toUpperCase();

  return (
    <div className={`product-image product-image--${size} ${className}`} style={{ background: tile }}>
      {symbol ? (
        <svg className="product-image-svg" aria-hidden="true">
          <use href={`#pi-${symbol}`} />
        </svg>
      ) : (
        <span className="product-image-monogram" aria-hidden="true">{initial}</span>
      )}
    </div>
  );
}
