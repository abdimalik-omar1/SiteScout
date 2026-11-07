import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MapView from "./components/MapView.jsx";
import NearbyLeases, { nearbyLeases } from "./components/NearbyLeases.jsx";
import CompareTable from "./components/CompareTable.jsx";
import {
  AgentPanel,
  Brand,
  BriefForm,
  BriefSummary,
  Limits,
  PickDetail,
  Shortlist,
} from "./components/Panels.jsx";
import { analyze, explain, pickLabels } from "./lib.js";

// Owner: frontend. Contract: docs/api-contract.md

const DEFAULT_BRIEF = {
  business_type: "cafe",
  budget: "tight",
  customers: ["students", "office_workers"],
  city: "Cork",
};

function initialTheme() {
  try {
    const saved = localStorage.getItem("sitescout-theme");
    if (saved === "light" || saved === "dark") return saved;
  } catch {
    /* storage unavailable */
  }
  return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
}

export default function App() {
  const [theme, setTheme] = useState(initialTheme);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    document.querySelector('meta[name="theme-color"]')?.setAttribute("content", theme === "light" ? "#f4f2ed" : "#0a0e13");
    try {
      localStorage.setItem("sitescout-theme", theme);
    } catch {
      /* storage unavailable */
    }
  }, [theme]);
  const [brief, setBrief] = useState(DEFAULT_BRIEF);
  const [editing, setEditing] = useState(true);
  const [analysis, setAnalysis] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [explaining, setExplaining] = useState(false);
  const [error, setError] = useState(null);
  const [explainError, setExplainError] = useState(null);
  const [selectedRank, setSelectedRank] = useState(1);
  const [metric, setMetric] = useState("total");
  const [compareOpen, setCompareOpen] = useState(false);
  const [prevRanks, setPrevRanks] = useState(null);
  const leasesPanel = useRef(null);
  const [leaseRadius, setLeaseRadius] = useState(3);
  const [hoveredLeaseId, setHoveredLeaseId] = useState(null);

  // Drop responses from a run that has since been replaced.
  const runId = useRef(0);
  const controller = useRef(null);

  const run = useCallback(async (nextBrief, { keepRanks = false } = {}) => {
    const id = ++runId.current;
    controller.current?.abort();
    const ctrl = new AbortController();
    controller.current = ctrl;

    setBrief(nextBrief);
    setEditing(false);
    setError(null);
    setExplainError(null);
    setExplanation(null);
    setAnalyzing(true);
    setPrevRanks(
      keepRanks && analysis
        ? Object.fromEntries(analysis.shortlist.map((p) => [p.cell_id, p.rank]))
        : null
    );

    let a;
    try {
      a = await analyze(nextBrief, ctrl.signal);
    } catch (e) {
      if (id !== runId.current || e.name === "AbortError") return;
      setError(e.message || "Could not reach the SiteScout API.");
      setAnalyzing(false);
      return;
    }
    if (id !== runId.current) return;
    setAnalysis(a);
    setSelectedRank(1);
    setAnalyzing(false);

    setExplaining(true);
    try {
      const ex = await explain(a, ctrl.signal);
      if (id !== runId.current) return;
      setExplanation(ex);
    } catch (e) {
      if (id !== runId.current || e.name === "AbortError") return;
      setExplainError(e.message || "agent call failed");
    } finally {
      if (id === runId.current) setExplaining(false);
    }
  }, [analysis]);

  const picks = analysis?.shortlist ?? [];
  const labels = useMemo(() => pickLabels(analysis?.shortlist ?? []), [analysis]);
  const selected = picks.find((p) => p.rank === selectedRank) ?? null;
  const nearby = useMemo(() => nearbyLeases(selected, leaseRadius), [selected, leaseRadius]);
  const mapLeases = useMemo(() => nearby.slice(0, 10), [nearby]);
  useEffect(() => setHoveredLeaseId(null), [mapLeases]);
  const verdict = explanation?.verdicts.find((v) => v.rank === selectedRank) ?? null;
  const selectPick = (rank) => {
    setSelectedRank(rank);
    setCompareOpen(false);
    requestAnimationFrame(() => {
      leasesPanel.current?.scrollIntoView({ block: "nearest" });
      leasesPanel.current?.focus({ preventScroll: true });
    });
  };

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="sidebar-scroll">
          <Brand theme={theme} onToggleTheme={() => setTheme((t) => (t === "light" ? "dark" : "light"))} />

          {analysis?.data_mode === "sample" && (
            <div className="banner" role="status">
              <strong>Sample data.</strong> The live data pull isn't available, so these numbers are not real.
            </div>
          )}
          {error && <div className="error" role="alert">{error} Is the backend running on port 8000?</div>}

          {editing || !analysis ? (
            <BriefForm brief={brief} onChange={setBrief} onSubmit={(b) => run(b)} busy={analyzing} />
          ) : (
            <>
              <BriefSummary
                brief={brief}
                busy={analyzing}
                onEdit={() => setEditing(true)}
                onBudget={(budget) => run({ ...brief, budget }, { keepRanks: true })}
              />
              <AgentPanel explanation={explanation} waiting={explaining} error={explainError} />
              {picks.length > 0 && (
                <Shortlist picks={picks} labels={labels} selectedRank={selectedRank} onSelect={selectPick} prevRanks={prevRanks} />
              )}
              {selected && (
                <div ref={leasesPanel} tabIndex={-1} aria-label={`Commercial rentals near pick ${selected.rank}`}>
                  <NearbyLeases area={selected} nearby={nearby} radius={leaseRadius} onRadius={setLeaseRadius} hoveredId={hoveredLeaseId} />
                </div>
              )}
              {selected && (
                <PickDetail
                  pick={selected}
                  label={labels[selected.cell_id]}
                  verdict={verdict}
                  aiMode={explanation?.ai_mode}
                  waiting={explaining}
                  onCompare={() => setCompareOpen(true)}
                />
              )}
            </>
          )}

          <Limits />
        </div>
      </aside>

      <MapView
        leases={mapLeases}
        onLeaseHover={setHoveredLeaseId}
        analysis={analysis}
        labels={labels}
        selectedRank={selectedRank}
        onSelect={selectPick}
        metric={metric}
        onMetric={setMetric}
        loading={analyzing}
        theme={theme}
      />

      {compareOpen && analysis && (
        <CompareTable analysis={analysis} labels={labels} onClose={() => setCompareOpen(false)} onSelect={selectPick} />
      )}
    </div>
  );
}
