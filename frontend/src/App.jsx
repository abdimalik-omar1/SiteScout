import { useState } from "react";

// Owner: frontend. Contract: docs/api-contract.md
// Minimal wiring so the end-to-end flow works from minute one.
const brief = {
  business_type: "cafe",
  budget: "tight",
  customers: ["students", "office_workers"],
  city: "Cork",
};

export default function App() {
  const [analysis, setAnalysis] = useState(null);
  const [explanation, setExplanation] = useState(null);

  async function run() {
    const a = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(brief),
    }).then((r) => r.json());
    setAnalysis(a);
    const e = await fetch("/api/explain", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(a),
    }).then((r) => r.json());
    setExplanation(e);
  }

  return (
    <main style={{ fontFamily: "system-ui", padding: 24 }}>
      <h1>SiteScout</h1>
      <button onClick={run}>Run sample analysis</button>
      {analysis?.data_mode === "sample" && (
        <p style={{ background: "#fde68a", padding: 8 }}>
          Sample data mode: these numbers are not real.
        </p>
      )}
      <pre>{analysis && JSON.stringify(analysis.shortlist, null, 2)}</pre>
      <pre>{explanation && JSON.stringify(explanation, null, 2)}</pre>
    </main>
  );
}
