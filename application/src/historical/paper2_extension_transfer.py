"""Can conventional statistics predict the 3 NEW countries (Mali, Niger, Uganda)?

This is the free half of the extension test. If a transfer model (trained on the original
4 countries, no labels from the new one) predicts Uganda/Niger fine, then any LLM failure
there is the LLM's, not the phenomenon's -- exactly the logic that made Tanzania decisive.
If the transfer model ALSO fails, the country is hard for everyone and tells us nothing
about the agents.

Usage: python paper2_extension_transfer.py
"""
from __future__ import annotations
import warnings; warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import pearsonr, spearmanr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / "data" / "lsms" / "lsms_4country_full.csv"
NEW = ROOT / "data" / "lsms" / "lsms_extension_3country.csv"
T = "nitrogen_kg_per_ha"
NUM = ["age_manager","plot_area_GPS","farm_size","dist_popcenter","elevation",
       "total_family_labor_days","total_hired_labor_days","family_labor_d_per_ha",
       "female_manager","formal_education_manager","primary_education_manager",
       "married_manager","plot_owned","irrigated","intercropped",
       "drought_shock","pests_shock","flood_shock","crop_shock","wave"]
CAT = ["main_crop"]
ADOPT = {"Malawi":0.52,"Ethiopia":0.51,"Nigeria":0.34,"Mali":0.286,
         "Niger":0.123,"Tanzania":0.11,"Uganda":0.037}
AGENT = {"Nigeria":0.351,"Malawi":0.309,"Ethiopia":0.294,"Tanzania":0.076}


def pre():
    return ColumnTransformer([
        ("n", Pipeline([("i",SimpleImputer(strategy="median")),("s",StandardScaler())]), NUM),
        ("c", Pipeline([("i",SimpleImputer(strategy="most_frequent")),
                        ("o",OneHotEncoder(handle_unknown="ignore",min_frequency=5))]), CAT)])


def hurdle(Xtr, ytr, Xte):
    ytr = np.asarray(ytr, float); a = (ytr > 0).astype(int)
    if len(set(a)) < 2: return np.full(len(Xte), ytr.mean())
    clf = Pipeline([("p",pre()),("m",LogisticRegression(max_iter=2000,C=0.5))]).fit(Xtr,a)
    p = clf.predict_proba(Xte)[:,1]
    pos = np.where(ytr > 0)[0]
    if len(pos) < 8: return p * (ytr[pos].mean() if len(pos) else 0.0)
    reg = Pipeline([("p",pre()),("m",Ridge(alpha=1.0))]).fit(Xtr.iloc[pos], np.log1p(ytr[pos]))
    return p * np.expm1(reg.predict(Xte)).clip(0)


def rf(Xtr, ytr, Xte):
    return Pipeline([("p",pre()),("m",RandomForestRegressor(
        n_estimators=500,min_samples_leaf=7,max_depth=6,random_state=0,n_jobs=-1))]
        ).fit(Xtr,ytr).predict(Xte)


def score(y, yh):
    ok = np.isfinite(y) & np.isfinite(yh)
    if ok.sum() < 8 or np.std(yh[ok]) < 1e-9: return np.nan, np.nan
    return pearsonr(yh[ok],y[ok])[0], spearmanr(yh[ok],y[ok])[0]


def main():
    old = pd.read_csv(OLD).dropna(subset=[T]); new = pd.read_csv(NEW).dropna(subset=[T])
    for c in NUM + CAT:
        if c not in new.columns: new[c] = np.nan
        if c not in old.columns: old[c] = np.nan
    print("Can conventional statistics predict the NEW countries?")
    print("(trained on the original 4 countries -- NO labels from the test country)\n")
    print(f"{'country':10s} {'adoption':>9s} {'n':>4s} {'transfer r':>11s} {'rho':>7s}   agents")
    for c, g in new.groupby("country"):
        Xtr, ytr = old[NUM+CAT], old[T].values
        Xte, yte = g[NUM+CAT], g[T].values
        r1,_ = score(yte, hurdle(Xtr, ytr, Xte)); r2,rho = score(yte, rf(Xtr, ytr, Xte))
        best = np.nanmax([r1,r2])
        print(f"{c:10s} {ADOPT[c]:8.1%} {len(g):4d} {best:11.3f} {rho:7.3f}   not yet run")
    print()
    print("reference -- original 4, agents vs transfer (from paper2_rival_test.md):")
    for c in ["Nigeria","Ethiopia","Malawi","Tanzania"]:
        print(f"  {c:10s} adoption {ADOPT[c]:5.1%}  agent r {AGENT[c]:+.3f}")


if __name__ == "__main__":
    main()
