async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, options);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.detail || `Request failed (${res.status})`);
  return body;
}

const qs = (params) => {
  const clean = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== undefined && v !== ""));
  const s = new URLSearchParams(clean).toString();
  return s ? `?${s}` : "";
};

export const api = {
  categories: () => request("/categories"),
  months: () => request("/months"),
  summary: (month) => request(`/summary${qs({ month })}`),
  trends: () => request("/trends"),
  transactions: (params) => request(`/transactions${qs(params)}`),
  setCategory: (id, category) =>
    request(`/transactions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category }),
    }),
  upload: (file) => {
    const form = new FormData();
    form.append("file", file);
    return request("/import", { method: "POST", body: form });
  },
  reset: () => request("/data", { method: "DELETE" }),
};
