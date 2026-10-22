import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { CATEGORY_COLORS, CATEGORY_ICONS, gbp } from "../colors.js";

export default function CategoryChart({ data }) {
  if (!data.length) return <p className="muted">No spending this month.</p>;
  const total = data.reduce((s, d) => s + d.total, 0);
  return (
    <div className="donut">
      <div className="donut-wrap">
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie data={data} dataKey="total" nameKey="category" innerRadius={72} outerRadius={110} paddingAngle={3} cornerRadius={6} stroke="none">
            {data.map((d) => <Cell key={d.category} fill={CATEGORY_COLORS[d.category]} />)}
          </Pie>
          <Tooltip formatter={(v) => gbp(v)} />
        </PieChart>
      </ResponsiveContainer>
        <div className="donut-center"><span>Total</span><strong>{gbp(total)}</strong></div>
      </div>
      <ul className="legend">
        {data.map((d) => (
          <li key={d.category}>
            <i style={{ background: `color-mix(in srgb, ${CATEGORY_COLORS[d.category]} 18%, transparent)` }}>{CATEGORY_ICONS[d.category]}</i>
            <span>{d.category}</span>
            <span className="muted">{Math.round((d.total / total) * 100)}%</span>
            <strong>{gbp(d.total)}</strong>
          </li>
        ))}
      </ul>
    </div>
  );
}
