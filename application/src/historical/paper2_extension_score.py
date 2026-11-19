"""Score the extension run: do the agents fail where fertilizer use is RARE?

THE HYPOTHESIS. The agents failed in exactly one of the original four countries -- Tanzania --
which is also the one with the lowest fertilizer adoption (11%). Reading: the models carry a
prior that fertilizing is normal and lose their footing where it is rare.

THE TEST. Niger is decisive: adoption 12.3% (Tanzania-like) but conventional transfer predicts
it WELL (r=0.469), so an agent failure there replicates Tanzania cleanly -- low adoption,
statistics fine, LLM broken. Mali (28.6%) is the mid-point control. Uganda (3.7%) is
uninformative by design: conventional also fails there (r=0.023), so both failing proves nothing.

Tier 1 only, so no hand-written per-country agronomy confounds the comparison.

Usage: python paper2_extension_score.py
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import json, numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import pearsonr, spearmanr

ROOT = Path(__file__).resolve().parents[2]
RES = ROOT / "results" / "full" / "lsms_extension" / "claude"
OUT = ROOT / "reproduced" / "historical" / "paper2_extension_result.md"
ADOPT = {"Malawi":.52,"Ethiopia":.51,"Nigeria":.34,"Mali":.286,"Niger":.123,
         "Tanzania":.11,"Uganda":.037}
# tier-1 medians over 3 providers, from results/analysis/paper1_metrics.md
T1_ORIG = {"Ethiopia":0.292,"Nigeria":0.281,"Malawi":0.266,"Tanzania":0.032}
TRANSFER = {"Mali":0.226,"Niger":0.469,"Uganda":0.023}


def agent_n(dec):
    if not isinstance(dec, dict): return None
    for c in (dec.get("annual_plan") or []):
        v = c.get("nitrogen_kg_per_ha")
        if isinstance(v, (int, float)): return float(v)
    v = dec.get("nitrogen_kg_per_ha")
    return float(v) if isinstance(v, (int, float)) else None


def main():
    rows = []
    for f in RES.glob("*.json"):
        try: j = json.loads(f.read_text())
        except Exception: continue
        n = agent_n(j.get("decision"))
        if n is None or j.get("observed_n_per_ha") is None: continue
        rows.append(dict(country=j["country"], pred=n, obs=float(j["observed_n_per_ha"])))
    d = pd.DataFrame(rows)
    L = ["# Paper 2 extension — do agents fail where fertilizer use is rare?", "",
         "Tier 1 (identity card only, no hand-written country agronomy) so the comparison is",
         "uniform across all seven countries. Claude, n=70 sampled per country at ~50/50",
         "adopters, matching the original design.", "",
         "| country | national adoption | n scored | AGENT r | conventional transfer r | verdict |",
         "|---|---|---|---|---|---|"]
    res = {}
    for c, g in d.groupby("country"):
        ok = np.isfinite(g.pred) & np.isfinite(g.obs)
        r = pearsonr(g.pred[ok], g.obs[ok])[0] if ok.sum() > 8 and g.pred[ok].std() > 1e-9 else np.nan
        res[c] = r
        t = TRANSFER[c]
        if c == "Uganda":
            v = "uninformative (both fail)"
        elif np.isfinite(r) and r < 0.15 and t > 0.30:
            v = "**REPLICATES TANZANIA**"
        elif np.isfinite(r) and r >= 0.20:
            v = "agents work"
        else:
            v = "ambiguous"
        L.append(f"| {c} | {ADOPT[c]:.1%} | {int(ok.sum())} | {r:+.3f} | {t:+.3f} | {v} |")
    L += ["", "## Original four (tier 1, median of 3 providers)", "",
          "| country | adoption | agent r |", "|---|---|---|"]
    for c, r in sorted(T1_ORIG.items(), key=lambda x: -ADOPT[x[0]]):
        L.append(f"| {c} | {ADOPT[c]:.1%} | {r:+.3f} |")
    # does agent skill track adoption?
    allc = {**T1_ORIG, **{k: v for k, v in res.items() if np.isfinite(v)}}
    xs = np.array([ADOPT[c] for c in allc]); ys = np.array([allc[c] for c in allc])
    if len(xs) >= 4:
        rr, pp = pearsonr(xs, ys)
        L += ["", "## Does agent skill track fertilizer adoption prevalence?", "",
              f"Across {len(xs)} countries: r = {rr:+.3f} (p = {pp:.3f})", "",
              "| country | adoption | agent r |", "|---|---|---|"]
        for c in sorted(allc, key=lambda k: -ADOPT[k]):
            L.append(f"| {c} | {ADOPT[c]:.1%} | {allc[c]:+.3f} |")
    OUT.write_text("\n".join(L) + "\n")
    print("\n".join(L)); print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
