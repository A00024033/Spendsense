import { gbp } from "../colors.js";

export default function SummaryCards({ summary }) {
  const rate = summary.income > 0 ? Math.round((summary.net / summary.income) * 100) : null;
  const cards = [
    { label: "Money in", value: gbp(summary.income), icon: "↓", tone: "green" },
    { label: "Money out", value: gbp(summary.spending), icon: "↑", tone: "pink" },
    {
      label: "Saved",
      value: gbp(summary.net),
      icon: "★",
      tone: summary.net >= 0 ? "violet" : "pink",
      sub: rate !== null ? `${rate}% of income` : null,
    },
    {
      label: "To review",
      value: summary.needs_review,
      icon: "!",
      tone: "amber",
      sub: summary.needs_review ? "tap a category to fix" : "all sorted",
    },
  ];
  return (
    <div className="stats">
      {cards.map((c) => (
        <div key={c.label} className={`stat ${c.tone}`}>
          <i className="stat-icon">{c.icon}</i>
          <div>
            <span>{c.label}</span>
            <strong>{c.value}</strong>
            {c.sub && <em>{c.sub}</em>}
          </div>
        </div>
      ))}
    </div>
  );
}
