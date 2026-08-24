/**
 * Thin wrapper around fetch() for the backend API.
 *
 * Every call either resolves with parsed JSON or throws an Error carrying a
 * message that is safe to show the user.
 */

const BASE_URL = "/api";

async function request(path, options = {}) {
  let response;

  try {
    response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    throw new Error("Cannot reach the server. Is the backend running?");
  }

  if (response.status === 204) return null;

  let body = null;
  try {
    body = await response.json();
  } catch {
    body = null;
  }

  if (!response.ok) {
    throw new Error(body?.detail || `Request failed (${response.status})`);
  }

  return body;
}

export const CURRENCY = "₹";

export function getHealth() {
  return request("/health");
}

export function getProducts({ search = "", category = "" } = {}) {
  const params = new URLSearchParams();
  if (search.trim()) params.set("search", search.trim());
  if (category) params.set("category", category);
  const query = params.toString();
  return request(`/products${query ? `?${query}` : ""}`);
}

export function getCategories() {
  return request("/categories");
}

export function getShoppingList() {
  return request("/shopping-list");
}

export function addShoppingListItem(payload) {
  return request("/shopping-list", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateShoppingListItem(id, changes) {
  return request(`/shopping-list/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export function getRecommendations(limit = 6) {
  return request(`/recommendations?limit=${limit}`);
}

export function getSubstitutes(productId) {
  return request(`/products/${productId}/substitutes`);
}

/** Send a voice transcript or typed command to the NLP endpoint. */
export function processCommand(text) {
  return request("/commands", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function deleteShoppingListItem(id) {
  return request(`/shopping-list/${id}`, { method: "DELETE" });
}
