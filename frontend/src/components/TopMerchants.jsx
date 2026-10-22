import { CATEGORY_COLORS, CATEGORY_ICONS, gbp } from "../colors.js";

export default function TopMerchants({ data }) {
  if (!data.length) return <p className="muted">Nothing yet.</p>;
  const max = data[0].total;
  return (
    <ol className="merchants">
      {data.map((m) => (
        <li key={m.merchant + m.category}>
          <div className="row">
            <span className="m-icon" style={{ background: `color-mix(in srgb, ${CATEGORY_COLORS[m.category]} 18%, transparent)` }}>
              {CATEGORY_ICONS[m.category]}
            </span>
            <span className="name">{m.merchant.toLowerCase()}</span>
            <strong>{gbp(m.total)}</strong>
          </div>
          <div className="bar">
            <span style={{ width: `${(m.total / max) * 100}%`, background: CATEGORY_COLORS[m.category] }} />
          </div>
          <span className="muted small">{m.category} · {m.visits} {m.visits === 1 ? "visit" : "visits"}</span>
        </li>
      ))}
    </ol>
  );
}
