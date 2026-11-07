import { useState } from "react";
import {
  AGENTS,
  BUDGETS,
  BUSINESS_TYPES,
  CUSTOMERS,
  GOOD_DIRECTION,
  fmt,
  labelFor,
  rampCSS,
} from "../lib.js";

export function Brand() {
  return (
    <div className="brand">
      <div className="brand-mark" aria-hidden="true">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3dd6b5" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 21s-6.5-5.6-6.5-11a6.5 6.5 0 0 1 13 0c0 5.4-6.5 11-6.5 11z" />
          <circle cx="12" cy="10" r="2.4" />
        </svg>
      </div>
      <div>
        <div className="brand-name">SiteScout</div>
        <div className="brand-sub">Business location intelligence · Cork</div>
      </div>
    </div>
  );
}

export function BudgetSwitch({ value, onChange, disabled }) {
  return (
    <div className="seg" role="group" aria-label="Budget">
      {BUDGETS.map((b) => (
        <button
          key={b.value}
          type="button"
          aria-pressed={value === b.value}
          disabled={disabled}
          onClick={() => value !== b.value && onChange(b.value)}
        >
          {b.label}
        </button>
      ))}
    </div>
  );
}

export function BriefForm({ brief, onChange, onSubmit, busy }) {
  const toggle = (c) =>
    onChange({
      ...brief,
      customers: brief.customers.includes(c)
        ? brief.customers.filter((x) => x !== c)
        : [...brief.customers, c],
    });

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit(brief);
      }}
      style={{ display: "flex", flexDirection: "column", gap: 18 }}
    >
      <h1 className="h1">Where should your business open?</h1>

      <div className="field">
        <label className="field-label" htmlFor="biz">What are you opening?</label>
        <select
          id="biz"
          className="select"
          value={brief.business_type}
          onChange={(e) => onChange({ ...brief, business_type: e.target.value })}
        >
          {BUSINESS_TYPES.map((b) => (
            <option key={b.value} value={b.value}>{b.label}</option>
          ))}
        </select>
      </div>

      <fieldset className="field" style={{ border: 0, padding: 0, margin: 0 }}>
        <legend className="field-label" style={{ padding: 0, marginBottom: 8 }}>Who are your customers?</legend>
        <div className="chips">
          {CUSTOMERS.map((c) => (
            <button
              key={c.value}
              type="button"
              className="chip"
              aria-pressed={brief.customers.includes(c.value)}
              onClick={() => toggle(c.value)}
            >
              {c.label}
            </button>
          ))}
        </div>
      </fieldset>

      <div className="field">
        <span className="field-label" id="budget-label">Budget</span>
        <BudgetSwitch value={brief.budget} onChange={(b) => onChange({ ...brief, budget: b })} />
        <span className="small muted">A tighter budget gives more weight to cheaper areas away from the centre.</span>
      </div>

      <button className="btn-primary" type="submit" disabled={busy}>
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="6.5" />
          <path d="M16 16l4.5 4.5" />
        </svg>
        {busy ? "Scouting…" : "Scout Cork"}
      </button>
    </form>
  );
}

export function BriefSummary({ brief, onEdit, onBudget, busy }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="brief-row">
        <div className="tags">
          <span className="tag">{labelFor(BUSINESS_TYPES, brief.business_type)}</span>
          {brief.customers.length ? (
            brief.customers.map((c) => <span className="tag" key={c}>{labelFor(CUSTOMERS, c)}</span>)
          ) : (
            <span className="tag">Any customers</span>
          )}
        </div>
        <button type="button" className="btn-ghost" onClick={onEdit}>Edit</button>
      </div>
      <div className="field">
        <span className="field-label">Budget · switch to re-rank</span>
        <BudgetSwitch value={brief.budget} onChange={onBudget} disabled={busy} />
      </div>
    </div>
  );
}

// The API returns the whole agent log at the end, so while waiting we show
// the specialists as running and the challenger and reporter as queued.
export function AgentPanel({ explanation, waiting, error }) {
  const [open, setOpen] = useState(null);
  const byAgent = Object.fromEntries((explanation?.agent_log ?? []).map((e) => [e.agent, e]));

  const statusOf = (a) => {
    if (explanation) return byAgent[a.key]?.status ?? "done";
    if (error) return "error";
    if (waiting) return a.stage === "specialist" ? "running" : "queued";
    return "queued";
  };

  return (
    <section className="card card-pad" aria-labelledby="agents-h">
      <div className="brief-row" style={{ marginBottom: 6 }}>
        <h2 className="h2" id="agents-h">Agent team</h2>
        {explanation ? (
          <span className={`mode-pill${explanation.ai_mode === "gemini" ? " ai" : ""}`}>
            {explanation.ai_mode === "gemini" ? "Gemini" : "Data-only"}
          </span>
        ) : waiting ? (
          <span className="small muted">Specialists run in parallel</span>
        ) : null}
      </div>
      <div className="agents">
        {AGENTS.map((a) => {
          const st = statusOf(a);
          const summary = explanation?.ai_mode === "gemini" ? byAgent[a.key]?.summary : null;
          return (
            <div className="agent" key={a.key} data-open={open === a.key}>
              <span className={`dot dot-${st}`} aria-hidden="true" />
              <button
                type="button"
                className="agent-toggle"
                onClick={() => setOpen(open === a.key ? null : a.key)}
                aria-expanded={open === a.key}
                disabled={!summary}
              >
                <div className="agent-name">
                  <span>{a.label}</span>
                  <span className={`agent-status st-${st}`}>{st}</span>
                </div>
                {summary && <div className="agent-summary">{summary}</div>}
              </button>
            </div>
          );
        })}
      </div>
      {explanation?.ai_mode === "data-only" && (
        <div className="small muted" style={{ marginTop: 8 }}>
          No Gemini key on the server, so the verdicts are data-only summaries built from the numbers.
        </div>
      )}
      {error && <div className="error small" style={{ marginTop: 10 }}>Agents unavailable: {error}. Scores and evidence below are unaffected.</div>}
    </section>
  );
}

function Move({ was, rank }) {
  if (was === undefined) return null;
  if (was === null) return <span className="move new">new</span>;
  if (was === rank) return null;
  return <span className={`move ${was > rank ? "up" : "down"}`}>was #{was}</span>;
}

export function Shortlist({ picks, labels, selectedRank, onSelect, prevRanks }) {
  return (
    <section aria-labelledby="picks-h" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <h2 className="h2" id="picks-h">Top five locations</h2>
      <div className="picks">
        {picks.map((p) => (
          <button
            key={p.cell_id}
            type="button"
            className="pick"
            aria-current={p.rank === selectedRank}
            onClick={() => onSelect(p.rank)}
          >
            <span className={`rank${p.rank === 1 ? " first" : ""}`}>{p.rank}</span>
            <span>
              <span className="pick-name">
                Near {labels[p.cell_id]}
                <Move was={prevRanks ? prevRanks[p.cell_id] ?? null : undefined} rank={p.rank} />
              </span>
              <span className="pick-sub" style={{ display: "block" }}>
                Demand {p.scores.demand} · Competition {p.scores.competition} · Cost {p.scores.cost}
              </span>
            </span>
            <span className="pick-score">{p.scores.total}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

const SUBS = [
  ["demand", "Demand"],
  ["competition", "Competition"],
  ["access", "Access"],
  ["cost", "Cost"],
];

function relation(row) {
  const dir = GOOD_DIRECTION[row.metric] ?? 0;
  if (row.value === row.cork_median || dir === 0) return { text: row.value > row.cork_median ? "further" : row.value < row.cork_median ? "closer" : "same", cls: "" };
  const better = dir > 0 ? row.value > row.cork_median : row.value < row.cork_median;
  return { text: row.value > row.cork_median ? "above" : "below", cls: better ? "ev-good" : "ev-bad" };
}

export function PickDetail({ pick, label, verdict, aiMode, waiting, onCompare }) {
  return (
    <section className="card card-pad" style={{ display: "flex", flexDirection: "column", gap: 16 }} aria-labelledby="detail-h">
      <div className="detail-head">
        <span className={`rank${pick.rank === 1 ? " first" : ""}`}>{pick.rank}</span>
        <div className="detail-name" id="detail-h">Near {label}</div>
        <div>
          <span className="big-score">{pick.scores.total}</span>
          <span className="small muted">/100</span>
        </div>
      </div>

      <div className="bars">
        {SUBS.map(([k, label]) => (
          <div className="bar-row" key={k}>
            <span className="muted">{label}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${pick.scores[k]}%`, background: rampCSS(pick.scores[k] / 100) }} />
            </div>
            <b style={{ textAlign: "right" }}>{pick.scores[k]}</b>
          </div>
        ))}
      </div>

      <div>
        <h3 className="h2" style={{ marginBottom: 6 }}>Verdict</h3>
        {verdict ? (
          <>
            <p style={{ margin: 0, fontSize: 14 }}>{verdict.verdict}</p>
            <div className="small muted" style={{ marginTop: 6 }}>
              {aiMode === "gemini" ? "Written by the agent team; every number is checked against the data." : "Data-only summary (no AI)."}
            </div>
          </>
        ) : waiting ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            <div className="skeleton" style={{ width: "95%" }} />
            <div className="skeleton" style={{ width: "80%" }} />
            <div className="skeleton" style={{ width: "60%" }} />
          </div>
        ) : (
          <p className="muted small" style={{ margin: 0 }}>No verdict yet.</p>
        )}
      </div>

      <div>
        <h3 className="h2" style={{ marginBottom: 4 }}>Evidence</h3>
        <table className="ev-table">
          <thead>
            <tr><th scope="col">Measure</th><th scope="col">Here</th><th scope="col">Median</th><th scope="col" aria-label="Compared with the Cork median"></th></tr>
          </thead>
          <tbody>
            {pick.evidence.map((row) => {
              const r = relation(row);
              return (
                <tr key={row.metric}>
                  <td>{row.label}</td>
                  <td><b>{fmt(row.value, row.metric)}</b></td>
                  <td className="muted">{fmt(row.cork_median, row.metric)}</td>
                  <td className={r.cls} style={{ width: 64 }}>{r.text}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {pick.nearest_competitors.length > 0 && (
        <div>
          <h3 className="h2" style={{ marginBottom: 4 }}>Nearest competitors</h3>
          {pick.nearest_competitors.map((c) => (
            <div className="comp-row" key={`${c.name}-${c.distance_m}`}>
              <span>{c.name}</span>
              <span className="muted">{c.distance_m.toLocaleString("en-IE")} m</span>
            </div>
          ))}
        </div>
      )}

      {verdict?.risks?.length > 0 && (
        <div className="risk-box">
          <h3 className="h2" style={{ marginBottom: 8 }}>Risks</h3>
          <ul className="list" style={{ fontSize: 13.5 }}>
            {verdict.risks.map((r, i) => <li key={i}>{r}</li>)}
          </ul>
        </div>
      )}

      <button type="button" className="btn-ghost" style={{ alignSelf: "flex-start" }} onClick={onCompare}>
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true"><path d="M4 6h16M4 12h16M4 18h16" /><path d="M10 4v16M16 4v16" /></svg>
        Compare all five
      </button>
    </section>
  );
}

export function Limits() {
  return (
    <div className="limits">
      A better-informed starting point, not a forecast. Scores rank Cork locations against each other. Cost is a
      distance-from-centre proxy, not rent. OpenStreetMap counts can be incomplete. Area names are the nearest
      well-known neighbourhood. Data: CSO Census 2022, OpenStreetMap contributors.
    </div>
  );
}
