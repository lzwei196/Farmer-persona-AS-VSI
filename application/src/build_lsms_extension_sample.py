"""Extend the LSMS sample to the 3 UNUSED countries in the 7-country panel.

WHY: the LLM agents failed only in Tanzania (r=0.076 vs +0.29..+0.35 elsewhere), and
Tanzania is also the country with the LOWEST fertilizer adoption of the four tested (11%).
Hypothesis: the agents may reproduce country-associated fertilizer-use patterns and perform
less well where observed fertilizer use is uncommon.
Uganda (4%) and Niger (12%) test that directly; Mali (29%) is the mid-point control.

Sampling MUST match the existing 4-country design exactly or the comparison breaks:
70 per country, ~50/50 adopters/non-adopters, balanced on gender x education, same filters
(plot 0.05-20 ha, N/ha capped 300, yield capped 8000), recommended wave per country.

Usage: python build_lsms_extension_sample.py
"""
from __future__ import annotations
import hashlib
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from paths import RAW_LSMS_DIR

ROOT = Path(__file__).resolve().parent.parent
DTA = RAW_LSMS_DIR / "Plot_dataset.dta"
OUT = ROOT / "reproduced" / "profiles" / "lsms_extension_3country.csv"
SEED = 42
PER_COUNTRY = 70
# recommended waves from data/lsms/lsms_7country_data_summary.md
WAVES = {"Mali": 2, "Niger": 1, "Uganda": 8}
KEEP = ["country","wave","hh_id_merge","plot_id_merge","admin_1_name","region_clean",
        "main_crop","plot_area_GPS","farm_size","age_manager","female_manager",
        "formal_education_manager","primary_education_manager","married_manager",
        "fert_user","inorganic_fertilizer","nitrogen_kg","nitrogen_kg_per_ha",
        "irrigated","harvest_kg","yield_kg_per_ha","total_family_labor_days",
        "total_hired_labor_days","family_labor_d_per_ha","intercropped",
        "drought_shock","pests_shock","flood_shock","crop_shock","dist_popcenter",
        "elevation","plot_owned"]


def yn(s):
    return s.map({"Yes": 1, "No": 0}).astype("Int64")


def prep(plot, country, wave):
    c = plot[(plot["country"] == country) & (plot["wave"] == wave)].copy()
    for col in ["inorganic_fertilizer","female_manager","formal_education_manager",
                "primary_education_manager","irrigated","married_manager","plot_owned",
                "intercropped","drought_shock","pests_shock","flood_shock","crop_shock"]:
        if col in c.columns and (c[col].dtype == object or str(c[col].dtype) == "category"):
            c[col] = yn(c[col].astype(object))
    if "admin_1_name" in c.columns:
        c["region_clean"] = (c["admin_1_name"].astype(str).str.strip()
                             .str.replace(r"^\d+\.\s*", "", regex=True))
        if "admin_2_name" in c.columns:
            m = c["region_clean"].isin(["", "nan"])
            c.loc[m, "region_clean"] = c.loc[m, "admin_2_name"].astype(str).str.strip()
    c = c[(c["plot_area_GPS"] >= 0.05) & (c["plot_area_GPS"] <= 20)].copy()
    c["nitrogen_kg_per_ha"] = c["nitrogen_kg"] / c["plot_area_GPS"]
    c.loc[c["nitrogen_kg_per_ha"] > 300, "nitrogen_kg_per_ha"] = np.nan
    c["yield_kg_per_ha"] = c["harvest_kg"] / c["plot_area_GPS"]
    c.loc[c["yield_kg_per_ha"] > 8000, "yield_kg_per_ha"] = np.nan
    c["fert_user"] = (c["inorganic_fertilizer"] == 1).astype("Int64").fillna(0).astype(int)
    c["family_labor_d_per_ha"] = c["total_family_labor_days"] / c["plot_area_GPS"]
    return c


def stratified(df, n, country):
    rng = np.random.RandomState(SEED + int(hashlib.sha256(country.encode("utf-8")).hexdigest()[:8], 16) % 1000)
    req = df[df.female_manager.notna() & df.formal_education_manager.notna()
             & df.age_manager.notna() & df.main_crop.notna()
             & df.nitrogen_kg.notna() & df.nitrogen_kg_per_ha.notna()].copy()
    fp, np_ = req[req.fert_user == 1], req[req.fert_user == 0]
    nf = min(n // 2, len(fp)); nn = min(n - nf, len(np_))
    def pick(pool, k):
        if len(pool) == 0 or k == 0: return pool.iloc[:0]
        pool = pool.copy()
        pool["_s"] = pool.female_manager.astype(str) + "_" + pool.formal_education_manager.astype(str)
        picks, per = [], max(1, k // max(1, pool["_s"].nunique()))
        for s in pool["_s"].unique():
            sub = pool[pool["_s"] == s]
            t = min(per, len(sub))
            if t: picks.append(sub.sample(n=t, random_state=rng.randint(0, 10**9)))
        out = pd.concat(picks) if picks else pool.iloc[:0]
        if len(out) < k:
            rem = pool.drop(out.index)
            out = pd.concat([out, rem.sample(n=min(k-len(out), len(rem)),
                                             random_state=rng.randint(0, 10**9))])
        elif len(out) > k:
            out = out.sample(n=k, random_state=rng.randint(0, 10**9))
        return out.drop(columns="_s")
    return pd.concat([pick(fp, nf), pick(np_, nn)]).reset_index(drop=True)


def main():
    print("loading Plot_dataset.dta ...", flush=True)
    plot = pd.read_stata(DTA, convert_categoricals=True)
    print(f"  {len(plot):,} plots, countries: {sorted(plot.country.unique())}")
    out = []
    for c, w in WAVES.items():
        d = prep(plot, c, w)
        s = stratified(d, PER_COUNTRY, c)
        nat = d.fert_user.mean()
        print(f"{c:8s} wave {w}: pool {len(d):6,}  national adoption {nat:5.1%}  "
              f"-> sampled {len(s)} ({s.fert_user.mean():.0%} adopters), "
              f"N/ha mean {s.nitrogen_kg_per_ha.mean():6.1f}, zero-frac {(s.nitrogen_kg_per_ha==0).mean():.2f}")
        out.append(s)
    t = pd.concat(out, ignore_index=True)
    cols = [c for c in KEEP if c in t.columns]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t[cols].to_csv(OUT, index=False)
    print(f"\n-> {OUT}  ({len(t)} rows, {len(cols)} cols)")


if __name__ == "__main__":
    main()
