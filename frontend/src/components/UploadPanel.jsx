import { useRef, useState } from "react";
import { api } from "../api.js";

export default function UploadPanel({ onImported, compact }) {
  const input = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);

  async function handle(file) {
    if (!file) return;
    setBusy(true);
    setMessage(null);
    try {
      const r = await api.upload(file);
      const parts = [`Imported ${r.inserted} transactions`];
      if (r.duplicates_skipped) parts.push(`skipped ${r.duplicates_skipped} duplicates`);
      if (r.needs_review) parts.push(`${r.needs_review} need a quick check`);
      setMessage({ ok: true, text: parts.join(", ") });
      onImported();
    } catch (e) {
      setMessage({ ok: false, text: e.message });
    } finally {
      setBusy(false);
      if (input.current) input.current.value = "";
    }
  }

  return (
    <section
      className={`upload ${dragging ? "dragging" : ""} ${compact ? "compact" : ""}`}
      onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); handle(e.dataTransfer.files[0]); }}
    >
      <input ref={input} type="file" accept=".csv" hidden onChange={(e) => handle(e.target.files[0])} />
      <div className="upload-icon">📄</div>
      <div className="upload-text">
        <strong>{compact ? "Add another statement" : "Drop your bank statement CSV here"}</strong>
        {!compact && <p className="muted">Works with Monzo, Starling, Barclays, HSBC and most UK bank exports</p>}
      </div>
      <button onClick={() => input.current.click()} disabled={busy}>
        {busy ? "Importing…" : "Choose file"}
      </button>
      {message && <p className={message.ok ? "ok" : "bad"}>{message.text}</p>}
    </section>
  );
}
