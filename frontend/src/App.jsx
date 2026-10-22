import { useCallback, useEffect, useState } from "react";
import { api } from "./api.js";
import { gbp, monthLabel } from "./colors.js";
import UploadPanel from "./components/UploadPanel.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import CategoryChart from "./components/CategoryChart.jsx";
import TrendChart from "./components/TrendChart.jsx";
import TopMerchants from "./components/TopMerchants.jsx";
import TransactionsTable from "./components/TransactionsTable.jsx";

export default function App() {
  const [categories, setCategories] = useState([]);
  const [months, setMonths] = useState([]);
  const [month, setMonth] = useState("");
  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState([]);
  const [error, setError] = useState("");
  const [version, setVersion] = useState(0); // bump to refresh everything

  const refresh = useCallback(() => setVersion((v) => v + 1), []);

  useEffect(() => {
    api.categories().then(setCategories).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    Promise.all([api.months(), api.summary(month), api.trends()])
      .then(([m, s, t]) => {
        setMonths(m);
        setSummary(s);
        setTrends(t);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, [month, version]);

  const hasData = summary && summary.count > 0;

  return (
    <div className="page">
      <header className={`hero ${hasData ? "" : "hero-empty"}`}>
        <div className="hero-inner">
          <div className="topbar">
            <div className="brand">
              <span className="logo">£</span>
              <div>
                <h1>SpendSense</h1>
                <p>Upload a bank statement, see where your money goes</p>
              </div>
            </div>
            {hasData && (
              <div className="controls">
                <select className="glass" value={month} onChange={(e) => setMonth(e.target.value)} aria-label="Month">
                  <option value="">All time</option>
                  {months.map((m) => (
                    <option key={m} value={m}>{monthLabel(m)}</option>
                  ))}
                </select>
                <button
                  className="glass"
                  onClick={async () => {
                    if (!window.confirm("Delete all imported data?")) return;
                    await api.reset();
                    setMonth("");
                    refresh();
                  }}
                >
                  Clear data
                </button>
              </div>
            )}
          </div>
          {hasData ? (
            <div className="hero-figure">
              <span>Spent in {monthLabel(month).toLowerCase() === "all time" ? "total" : monthLabel(month)}</span>
              <strong>{gbp(summary.spending)}</strong>
              <em>across {summary.count} transactions</em>
            </div>
          ) : (
            <div className="hero-figure">
              <strong className="headline">Your money, sorted automatically.</strong>
              <span>Rules and machine learning categorise every transaction, and it learns from your corrections.</span>
            </div>
          )}
        </div>
      </header>

      <main className="app">
      {error && <div className="error">{error}</div>}

      {hasData && <SummaryCards summary={summary} />}
      <UploadPanel onImported={refresh} compact={hasData} />

      {hasData && (
        <>
          <div className="grid">
            <section className="card">
              <h2>Spending by category <span className="muted">· {monthLabel(month)}</span></h2>
              <CategoryChart data={summary.by_category} />
            </section>
            <section className="card">
              <h2>Top merchants <span className="muted">· {monthLabel(month)}</span></h2>
              <TopMerchants data={summary.top_merchants} />
            </section>
          </div>
          <section className="card">
            <h2>Monthly spending</h2>
            <TrendChart data={trends} />
          </section>
          <TransactionsTable month={month} categories={categories} version={version} onChanged={refresh} />
        </>
      )}
      </main>
      <footer className="foot">Built with FastAPI, scikit-learn, SQLite and React</footer>
    </div>
  );
}
