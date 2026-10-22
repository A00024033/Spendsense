import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CATEGORY_COLORS, gbp } from "../colors.js";

// The API returns one row per (month, category). Recharts wants one row
// per month with a key for each category, so we pivot here.
function pivot(rows) {
  const byMonth = {};
  const cats = new Set();
  for (const { month, category, total } of rows) {
    byMonth[month] ??= { month };
    byMonth[month][category] = total;
    cats.add(category);
  }
  return { data: Object.values(byMonth), categories: [...cats] };
}

export default function TrendChart({ data }) {
  const { data: rows, categories } = pivot(data);
  const short = (m) => new Date(m + "-01").toLocaleDateString("en-GB", { month: "short", year: "2-digit" });
  return (
    <ResponsiveContainer width="100%" height={280}>
      <BarChart data={rows} margin={{ left: 8, right: 8 }}>
        <CartesianGrid vertical={false} stroke="var(--line)" />
        <XAxis dataKey="month" tickFormatter={short} stroke="var(--muted)" tickLine={false} axisLine={false} />
        <YAxis tickFormatter={(v) => `£${v}`} stroke="var(--muted)" width={60} tickLine={false} axisLine={false} />
        <Tooltip formatter={(v) => gbp(v)} labelFormatter={short} cursor={{ fill: "var(--hover)" }}
          contentStyle={{ borderRadius: 12, border: "1px solid var(--line)", background: "var(--card)" }} />
        <Legend iconType="circle" wrapperStyle={{ fontSize: 13 }} />
        {categories.map((c, i) => (
          <Bar key={c} dataKey={c} stackId="a" fill={CATEGORY_COLORS[c]} maxBarSize={64}
            radius={i === categories.length - 1 ? [8, 8, 0, 0] : 0} />
        ))}
      </BarChart>
    </ResponsiveContainer>
  );
}
