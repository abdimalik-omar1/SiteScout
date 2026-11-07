import { useEffect } from "react";
import { GOOD_DIRECTION, fmt } from "../lib.js";

const SCORE_ROWS = [
  ["total", "Overall score"],
  ["demand", "Demand"],
  ["competition", "Competition"],
  ["access", "Access"],
  ["cost", "Cost advantage"],
];

function bestIndex(values, dir) {
  if (dir === 0) return -1;
  const target = dir > 0 ? Math.max(...values) : Math.min(...values);
  // Only highlight a clear winner, not a tie across every pick.
  return values.filter((v) => v === target).length === values.length ? -1 : values.indexOf(target);
}

export default function CompareTable({ analysis, labels, onClose, onSelect }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const picks = analysis.shortlist;
  const evidenceRows = picks[0]?.evidence ?? [];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="cmp-h" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <h2 className="h1" id="cmp-h" style={{ fontSize: 24 }}>Compare the top five</h2>
            <div className="muted small" style={{ marginTop: 4 }}>
              The best value in each row is highlighted. Fewer competitors is better; distance from the centre is shown as-is.
            </div>
          </div>
          <button type="button" className="btn-ghost" onClick={onClose} aria-label="Close comparison">Close</button>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table className="cmp">
            <thead>
              <tr>
                <th scope="col">Measure</th>
                {picks.map((p) => (
                  <th scope="col" key={p.cell_id}>
                    <div className="cmp-col">
                      <button type="button" className="btn-ghost" style={{ height: 30 }} onClick={() => { onSelect(p.rank); onClose(); }}>
                        #{p.rank} · {labels[p.cell_id]}
                      </button>
                    </div>
                  </th>
                ))}
                <th scope="col" className="muted">Cork median</th>
              </tr>
            </thead>
            <tbody>
              <tr className="grp"><td colSpan={picks.length + 2}>Scores out of 100</td></tr>
              {SCORE_ROWS.map(([k, label]) => {
                const vals = picks.map((p) => p.scores[k]);
                const best = bestIndex(vals, 1);
                return (
                  <tr key={k}>
                    <th scope="row">{label}</th>
                    {vals.map((v, i) => <td key={i} className={i === best ? "best" : ""}>{v}</td>)}
                    <td className="med">{k === "total" ? "" : "50"}</td>
                  </tr>
                );
              })}
              <tr className="grp"><td colSpan={picks.length + 2}>Evidence</td></tr>
              {evidenceRows.map((row, ri) => {
                const vals = picks.map((p) => p.evidence[ri]?.value ?? null);
                const best = bestIndex(vals, GOOD_DIRECTION[row.metric] ?? 0);
                return (
                  <tr key={row.metric}>
                    <th scope="row">{row.label}</th>
                    {vals.map((v, i) => <td key={i} className={i === best ? "best" : ""}>{fmt(v, row.metric)}</td>)}
                    <td className="med">{fmt(row.cork_median, row.metric)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <div className="small muted" style={{ marginTop: 12 }}>
          Sources: CSO Census 2022 small areas and OpenStreetMap contributors. Sub-scores are percentile ranks against every Cork cell, so 50 is the middle.
        </div>
      </div>
    </div>
  );
}
