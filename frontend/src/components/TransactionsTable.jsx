import { useEffect, useState } from "react";
import { api } from "../api.js";
import { CATEGORY_COLORS, CATEGORY_ICONS, gbp } from "../colors.js";

const SOURCE_LABEL = { rule: "Rule", ml: "AI guess", user: "You" };

export default function TransactionsTable({ month, categories, version, onChanged }) {
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("");
  const [reviewOnly, setReviewOnly] = useState(false);
  const [toast, setToast] = useState("");

  useEffect(() => {
    api
      .transactions({ month, category: filter, needs_review: reviewOnly ? true : undefined })
      .then(setRows);
  }, [month, filter, reviewOnly, version]);

  async function change(tx, category) {
    const r = await api.setCategory(tx.id, category);
    setToast(
      r.also_relabelled
        ? `Updated, plus ${r.also_relabelled} other ${tx.description.split(" ")[0]} transactions. Future imports will remember this.`
        : "Updated. Future imports will remember this merchant."
    );
    setTimeout(() => setToast(""), 4000);
    onChanged();
  }

  return (
    <section className="card">
      <div className="table-head">
        <h2>Transactions</h2>
        <div className="controls">
          <label className="check">
            <input type="checkbox" checked={reviewOnly} onChange={(e) => setReviewOnly(e.target.checked)} />
            Needs review only
          </label>
          <select value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Category filter">
            <option value="">All categories</option>
            {categories.map((c) => <option key={c}>{c}</option>)}
          </select>
        </div>
      </div>
      {toast && <div className="toast">{toast}</div>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr><th>Date</th><th>Description</th><th>Category</th><th>Decided by</th><th className="num">Amount</th></tr>
          </thead>
          <tbody>
            {rows.map((tx) => (
              <tr key={tx.id} className={tx.needs_review ? "review" : ""}>
                <td className="muted">{new Date(tx.date).toLocaleDateString("en-GB", { day: "numeric", month: "short" })}</td>
                <td>{tx.description}</td>
                <td>
                  <select
                    className="pill"
                    style={{ "--c": CATEGORY_COLORS[tx.category] }}
                    value={tx.category}
                    onChange={(e) => change(tx, e.target.value)}
                  >
                    {categories.map((c) => <option key={c} value={c}>{CATEGORY_ICONS[c]} {c}</option>)}
                  </select>
                </td>
                <td>
                  <span className={`badge ${tx.source}`}>
                    {SOURCE_LABEL[tx.source]}
                    {tx.source === "ml" && ` · ${Math.round(tx.confidence * 100)}%`}
                  </span>
                </td>
                <td className={`num ${tx.amount > 0 ? "pos" : ""}`}>{gbp(tx.amount)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!rows.length && <p className="muted pad">No transactions match.</p>}
      </div>
    </section>
  );
}
