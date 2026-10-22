export const CATEGORY_COLORS = {
  Groceries: "#10b981",
  "Eating Out": "#f97316",
  Transport: "#3b82f6",
  Bills: "#8b5cf6",
  Shopping: "#ec4899",
  Entertainment: "#eab308",
  Health: "#06b6d4",
  Rent: "#6366f1",
  Income: "#22c55e",
  Transfers: "#94a3b8",
  Other: "#a8a29e",
};

export const CATEGORY_ICONS = {
  Groceries: "🛒",
  "Eating Out": "🍜",
  Transport: "🚇",
  Bills: "💡",
  Shopping: "🛍️",
  Entertainment: "🎬",
  Health: "💊",
  Rent: "🏠",
  Income: "💰",
  Transfers: "🔁",
  Other: "❔",
};

export const gbp = (n) =>
  new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(n ?? 0);

export const monthLabel = (m) => {
  if (!m) return "All time";
  const [y, mo] = m.split("-");
  return new Date(+y, +mo - 1, 1).toLocaleDateString("en-GB", { month: "long", year: "numeric" });
};
