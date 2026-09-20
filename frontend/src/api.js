// Backend-URL (Railway). Direkt im Code, damit kein .env noetig ist.
const BASE = "https://backend-production-66df.up.railway.app";

const TOKEN_KEY = "vesti_token";

// Wandelt eine Datei in reines base64 (ohne data:-Prefix) um
export function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result || "";
      const comma = result.indexOf(",");
      resolve(comma >= 0 ? result.slice(comma + 1) : result);
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export const auth = {
  get token() {
    return localStorage.getItem(TOKEN_KEY);
  },
  set(token) {
    localStorage.setItem(TOKEN_KEY, token);
  },
  clear() {
    localStorage.removeItem(TOKEN_KEY);
  },
};

function authHeaders(extra = {}) {
  const t = auth.token;
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra;
}

async function handle(res) {
  if (res.status === 401) {
    auth.clear();
    window.dispatchEvent(new Event("vesti-unauthorized"));
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const data = await res.json();
      detail = data.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json();
}

export const api = {
  // ---- Auth ----
  async register(payload) {
    return handle(
      await fetch(`${BASE}/api/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async login(payload) {
    return handle(
      await fetch(`${BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
    );
  },

  async me() {
    return handle(await fetch(`${BASE}/api/auth/me`, { headers: authHeaders() }));
  },

  // ---- Meta ----
  async getMeta() {
    return handle(await fetch(`${BASE}/api/meta`));
  },

  // ---- Analyse ----
  async getStats() {
    return handle(await fetch(`${BASE}/api/analytics/stats`, { headers: authHeaders() }));
  },

  async getInsights() {
    return handle(
      await fetch(`${BASE}/api/analytics/insights`, {
        method: "POST",
        headers: authHeaders(),
      })
    );
  },

  // ---- Marken ----
  async getBrands() {
    return handle(await fetch(`${BASE}/api/brands`, { headers: authHeaders() }));
  },

  // ---- Profil ----
  async getProfileFields() {
    return handle(await fetch(`${BASE}/api/profile/fields`));
  },

  async updateProfile(payload) {
    return handle(
      await fetch(`${BASE}/api/profile`, {
        method: "PUT",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  // ---- Shopping ----
  async shoppingSuggest(payload) {
    return handle(
      await fetch(`${BASE}/api/shopping/suggest`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async fitCheck(payload) {
    return handle(
      await fetch(`${BASE}/api/shopping/fitcheck`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async updateQuantity(id, quantity) {
    return handle(
      await fetch(`${BASE}/api/items/${id}/quantity`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ quantity }),
      })
    );
  },

  async toggleFavorite(id, favorite) {
    return handle(
      await fetch(`${BASE}/api/items/${id}/favorite`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ favorite }),
      })
    );
  },

  // ---- Items ----
  async listItems() {
    return handle(await fetch(`${BASE}/api/items`, { headers: authHeaders() }));
  },

  async analyzeQuick(files, hint = "") {
    const list = Array.isArray(files) ? files : [files];
    const form = new FormData();
    for (const f of list) form.append("files", f);
    if (hint) form.append("hint", hint);
    return handle(
      await fetch(`${BASE}/api/analyze/quick`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      })
    );
  },

  async analyzeDetail(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/detail`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async analyzeProductShot(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/product-shot`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async generateItemImage(id) {
    return handle(
      await fetch(`${BASE}/api/items/${id}/generate-image`, {
        method: "POST",
        headers: authHeaders(),
      })
    );
  },

  async deleteAiImage(id) {
    return handle(
      await fetch(`${BASE}/api/items/${id}/ai-image`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async reanalyzeItem(id, regenerateImage = true) {
    return handle(
      await fetch(`${BASE}/api/items/${id}/reanalyze`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ regenerate_image: regenerateImage }),
      })
    );
  },

  async addItemImages(id, images) {
    return handle(
      await fetch(`${BASE}/api/items/${id}/images`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ images }),
      })
    );
  },

  async deleteItemImage(imageId) {
    return handle(
      await fetch(`${BASE}/api/item-images/${imageId}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async outfitTryon(itemIds, occasion = "") {
    return handle(
      await fetch(`${BASE}/api/outfits/tryon`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ item_ids: itemIds, occasion }),
      })
    );
  },

  async analyze(file, hint = "") {
    const form = new FormData();
    form.append("file", file);
    if (hint) form.append("hint", hint);
    return handle(
      await fetch(`${BASE}/api/analyze`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      })
    );
  },

  async createItem(payload) {
    return handle(
      await fetch(`${BASE}/api/items`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async deleteItem(id) {
    return handle(
      await fetch(`${BASE}/api/items/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async updateItem(id, payload) {
    return handle(
      await fetch(`${BASE}/api/items/${id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async recommend(payload) {
    return handle(
      await fetch(`${BASE}/api/recommend`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async generateOutfits(payload) {
    return handle(
      await fetch(`${BASE}/api/outfits/generate`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  // ---- Uhren ----
  async listWatches() {
    return handle(await fetch(`${BASE}/api/watches`, { headers: authHeaders() }));
  },

  async analyzeWatch(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/watch`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async analyzeWatchShot(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/watch-shot`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async createWatch(payload) {
    return handle(
      await fetch(`${BASE}/api/watches`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async updateWatch(id, payload) {
    return handle(
      await fetch(`${BASE}/api/watches/${id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async deleteWatch(id) {
    return handle(
      await fetch(`${BASE}/api/watches/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async toggleWatchFavorite(id, favorite) {
    return handle(
      await fetch(`${BASE}/api/watches/${id}/favorite`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ favorite }),
      })
    );
  },

  async reanalyzeWatch(id, regenerateImage = true) {
    return handle(
      await fetch(`${BASE}/api/watches/${id}/reanalyze`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ regenerate_image: regenerateImage }),
      })
    );
  },

  async generateWatchImage(id) {
    return handle(
      await fetch(`${BASE}/api/watches/${id}/generate-image`, {
        method: "POST",
        headers: authHeaders(),
      })
    );
  },

  async deleteWatchAiImage(id) {
    return handle(
      await fetch(`${BASE}/api/watches/${id}/ai-image`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async addWatchImages(id, images) {
    return handle(
      await fetch(`${BASE}/api/watches/${id}/images`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ images }),
      })
    );
  },

  async deleteWatchImage(imageId) {
    return handle(
      await fetch(`${BASE}/api/watch-images/${imageId}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async getWatchBrands() {
    return handle(await fetch(`${BASE}/api/brands/watches`, { headers: authHeaders() }));
  },

  // ---- Accessoires ----
  async listAccessories() {
    return handle(await fetch(`${BASE}/api/accessories`, { headers: authHeaders() }));
  },

  async analyzeAccessory(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/accessory`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async analyzeAccessoryShot(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/accessory-shot`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async createAccessory(payload) {
    return handle(
      await fetch(`${BASE}/api/accessories`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async updateAccessory(id, payload) {
    return handle(
      await fetch(`${BASE}/api/accessories/${id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async deleteAccessory(id) {
    return handle(
      await fetch(`${BASE}/api/accessories/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async toggleAccessoryFavorite(id, favorite) {
    return handle(
      await fetch(`${BASE}/api/accessories/${id}/favorite`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ favorite }),
      })
    );
  },

  async reanalyzeAccessory(id, regenerateImage = true) {
    return handle(
      await fetch(`${BASE}/api/accessories/${id}/reanalyze`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ regenerate_image: regenerateImage }),
      })
    );
  },

  async generateAccessoryImage(id) {
    return handle(
      await fetch(`${BASE}/api/accessories/${id}/generate-image`, {
        method: "POST",
        headers: authHeaders(),
      })
    );
  },

  async deleteAccessoryAiImage(id) {
    return handle(
      await fetch(`${BASE}/api/accessories/${id}/ai-image`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async addAccessoryImages(id, images) {
    return handle(
      await fetch(`${BASE}/api/accessories/${id}/images`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ images }),
      })
    );
  },

  async deleteAccessoryImage(imageId) {
    return handle(
      await fetch(`${BASE}/api/accessory-images/${imageId}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async getAccessoryBrands() {
    return handle(await fetch(`${BASE}/api/brands/accessories`, { headers: authHeaders() }));
  },

  async getAccessoryStats() {
    return handle(await fetch(`${BASE}/api/analytics/accessories`, { headers: authHeaders() }));
  },

  // ---- Düfte ----
  async listFragrances() {
    return handle(await fetch(`${BASE}/api/fragrances`, { headers: authHeaders() }));
  },

  async analyzeFragrance(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/fragrance`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async analyzeFragranceShot(payload) {
    return handle(
      await fetch(`${BASE}/api/analyze/fragrance-shot`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async createFragrance(payload) {
    return handle(
      await fetch(`${BASE}/api/fragrances`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async updateFragrance(id, payload) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  async deleteFragrance(id) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async toggleFragranceFavorite(id, favorite) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}/favorite`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ favorite }),
      })
    );
  },

  async updateFillLevel(id, fillLevel) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}/fill-level`, {
        method: "PATCH",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ fill_level: fillLevel }),
      })
    );
  },

  async reanalyzeFragrance(id, regenerateImage = true) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}/reanalyze`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ regenerate_image: regenerateImage }),
      })
    );
  },

  async generateFragranceImage(id) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}/generate-image`, {
        method: "POST",
        headers: authHeaders(),
      })
    );
  },

  async deleteFragranceAiImage(id) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}/ai-image`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async addFragranceImages(id, images) {
    return handle(
      await fetch(`${BASE}/api/fragrances/${id}/images`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify({ images }),
      })
    );
  },

  async deleteFragranceImage(imageId) {
    return handle(
      await fetch(`${BASE}/api/fragrance-images/${imageId}`, {
        method: "DELETE",
        headers: authHeaders(),
      })
    );
  },

  async getFragranceBrands() {
    return handle(await fetch(`${BASE}/api/brands/fragrances`, { headers: authHeaders() }));
  },

  async fragranceAdvice(payload) {
    return handle(
      await fetch(`${BASE}/api/fragrances/advice`, {
        method: "POST",
        headers: authHeaders({ "Content-Type": "application/json" }),
        body: JSON.stringify(payload),
      })
    );
  },

  // ---- Sammlungs-Analyse ----
  async getWatchStats() {
    return handle(await fetch(`${BASE}/api/analytics/watches`, { headers: authHeaders() }));
  },

  async getWatchInsights() {
    return handle(
      await fetch(`${BASE}/api/analytics/watches/insights`, {
        method: "POST",
        headers: authHeaders(),
      })
    );
  },

  async getFragranceStats() {
    return handle(await fetch(`${BASE}/api/analytics/fragrances`, { headers: authHeaders() }));
  },

  async getFragranceInsights() {
    return handle(
      await fetch(`${BASE}/api/analytics/fragrances/insights`, {
        method: "POST",
        headers: authHeaders(),
      })
    );
  },

  async getPendingReview() {
    return handle(
      await fetch(`${BASE}/api/collections/pending-review`, { headers: authHeaders() })
    );
  },

  async chat(message, history = [], imageFile = null) {
    const form = new FormData();
    form.append("message", message);
    form.append("history", JSON.stringify(history));
    if (imageFile) {
      form.append("image", imageFile);
    }
    return handle(
      await fetch(`${BASE}/api/chat`, {
        method: "POST",
        headers: authHeaders(),
        body: form,
      })
    );
  },
};
