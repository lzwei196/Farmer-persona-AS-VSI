"""Paper 2 task 0a — the rival-explanation test.

THESIS: LLM agents represent farmers worse where training data is sparse.
RIVAL:  smallholder behaviour is simply harder to predict for ANYONE, so any
        model degrades. That is not a story about AI.

DISCRIMINANT: fit conventional predictors (OLS, random forest) to the SAME
households and covariates, honest CV within each country, and compare the
per-country skill ORDERING against the agents'. Tanzania is decisive: all three
LLMs collapse there (median r 0.076) while Nigeria reaches 0.351 under an
identical instrument, prompt and sample size.

  conventional ALSO collapses in Tanzania -> phenomenon difficulty, thesis wrong
  conventional HOLDS where LLMs collapse  -> representational gap, thesis live

Leakage control (critical): fert_user / inorganic_fertilizer ARE the adoption
decision; nitrogen_kg is the target's numerator; harvest_kg and yield_kg_per_ha
are POST-TREATMENT outcomes of the fertilizer choice. All excluded.

Usage: python paper2_rival_test.py
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import pearsonr, spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

ROOT = Path(__file__).resolve().parents[2]
CSV = ROOT / "data" / "lsms" / "lsms_4country_full.csv"
OUT = ROOT / "reproduced" / "historical" / "paper2_rival_test.md"
TARGET = "nitrogen_kg_per_ha"
LEAK = {"fert_user", "inorganic_fertilizer", "nitrogen_kg", "harvest_kg",
        "yield_kg_per_ha", TARGET}
NUM = ["age_manager", "plot_area_GPS", "farm_size", "dist_popcenter", "elevation",
       "total_family_labor_days", "total_hired_labor_days", "family_labor_d_per_ha",
       "female_manager", "formal_education_manager", "primary_education_manager",
       "married_manager", "plot_owned", "irrigated", "intercropped",
       "drought_shock", "pests_shock", "flood_shock", "crop_shock", "wave"]
CAT = ["main_crop", "region_clean"]
# agent per-country medians, from results/analysis/paper1_metrics.md (12 cells each)
AGENT = {"Nigeria": 0.351, "Malawi": 0.309, "Ethiopia": 0.294, "Tanzania": 0.076}
AGENT_RANGE = {"Nigeria": (0.141, 0.460), "Malawi": (0.182, 0.398),
               "Ethiopia": (0.175, 0.386), "Tanzania": (-0.157, 0.253)}


def make(kind):
    pre = ColumnTransformer([
        ("n", Pipeline([("i", SimpleImputer(strategy="median")), ("s", StandardScaler())]), NUM),
        ("c", Pipeline([("i", SimpleImputer(strategy="most_frequent")),
                        ("o", OneHotEncoder(handle_unknown="ignore", min_frequency=3))]), CAT)])
    est = (Ridge(alpha=1.0) if kind == "ols"
           else RandomForestRegressor(n_estimators=400, min_samples_leaf=3,
                                      random_state=0, n_jobs=-1))
    return Pipeline([("pre", pre), ("est", est)])


def cv_country(d, kind, seeds=(0, 1, 2, 3, 4)):
    """Repeated 5-fold CV within one country. Returns out-of-fold r/rho/MAE."""
    X = d[NUM + CAT]; y = d[TARGET].values
    rs, rhos, maes = [], [], []
    for s in seeds:
        oof = np.full(len(d), np.nan)
        for tr, te in KFold(5, shuffle=True, random_state=s).split(X):
            m = make(kind).fit(X.iloc[tr], y[tr])
            oof[te] = m.predict(X.iloc[te])
        ok = np.isfinite(oof) & np.isfinite(y)
        if ok.sum() > 5 and np.std(oof[ok]) > 1e-9:
            rs.append(pearsonr(oof[ok], y[ok])[0])
            rhos.append(spearmanr(oof[ok], y[ok])[0])
            maes.append(np.mean(np.abs(oof[ok] - y[ok])))
    return (float(np.median(rs)) if rs else np.nan,
            float(np.median(rhos)) if rhos else np.nan,
            float(np.median(maes)) if maes else np.nan)


def main():
    d = pd.read_csv(CSV).dropna(subset=[TARGET])
    lines = ["# Paper 2 — rival-explanation test", "",
             "Conventional supervised models (Ridge/OLS, random forest) fitted to the SAME",
             "households and covariates as the LLM agents, honest repeated 5-fold CV WITHIN",
             "each country. Leakage excluded: " + ", ".join(sorted(LEAK - {TARGET})) + ".", "",
             f"n = {len(d)} plots, {d.country.nunique()} countries, target = {TARGET}", "",
             "| country | n | zero-frac | AGENT median r | agent range | OLS r | RF r | best conventional |",
             "|---|---|---|---|---|---|---|---|"]
    res = {}
    for c, g in d.groupby("country"):
        ro, _, _ = cv_country(g, "ols")
        rf, _, _ = cv_country(g, "rf")
        best = np.nanmax([ro, rf])
        res[c] = (ro, rf, best)
        lo, hi = AGENT_RANGE[c]
        lines.append(f"| {c} | {len(g)} | {(g[TARGET]==0).mean():.2f} | {AGENT[c]:+.3f} | "
                     f"{lo:+.3f}..{hi:+.3f} | {ro:+.3f} | {rf:+.3f} | **{best:+.3f}** |")
    lines += ["", "## Verdict", ""]
    tz_conv = res["Tanzania"][2]; tz_agent = AGENT["Tanzania"]
    others_conv = np.nanmean([res[c][2] for c in res if c != "Tanzania"])
    others_agent = np.nanmean([AGENT[c] for c in AGENT if c != "Tanzania"])
    lines.append(f"- Tanzania: agents {tz_agent:+.3f} vs best conventional {tz_conv:+.3f}")
    lines.append(f"- Other three (mean): agents {others_agent:+.3f} vs best conventional {others_conv:+.3f}")
    drop_a = others_agent - tz_agent
    drop_c = others_conv - tz_conv
    lines.append(f"- Skill DROP into Tanzania: agents {drop_a:+.3f}, conventional {drop_c:+.3f}")
    lines.append("")
    if not np.isfinite(tz_conv):
        v = "INCONCLUSIVE — conventional model did not fit."
    elif tz_conv < 0.15 and drop_c >= 0.6 * drop_a:
        v = ("**RIVAL SUPPORTED** — the conventional model collapses in Tanzania too. "
             "The gap is phenomenon difficulty, not representation. Paper 2's thesis is "
             "WRONG AS STATED and must be rebuilt.")
    elif tz_conv >= 0.15 and drop_c < 0.6 * drop_a:
        v = ("**THESIS LIVE** — the conventional model holds where the LLMs collapse. "
             "The gap is representational.")
    else:
        v = ("**MIXED** — partial degradation in both. Report the ordering honestly; the "
             "thesis needs a weaker, comparative statement.")
    lines += [v, "", "Caveats: n=70 per country is small; CV variance is real (medians over 5 seeds).",
              "A supervised model trained on the country's OWN data is a strong-form rival —",
              "the LLM is zero-shot. Treat this as an upper bound on conventional skill."]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\n-> {OUT}")


if __name__ == "__main__":
    main()
