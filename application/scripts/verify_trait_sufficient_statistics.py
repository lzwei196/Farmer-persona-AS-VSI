"""Check stored bootstrap coefficients against direct weighted row-level least squares.
Uses row multiplicities from the identical fixed-seed cluster/profile draws;
no raw household identifiers are written to any output.
"""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('VECLIB_MAXIMUM_THREADS','1')
from pathlib import Path
import argparse,json,sys
ap=argparse.ArgumentParser();ap.add_argument('--plot-data',type=Path);ap.add_argument('--survey-traits-csv',type=Path);ap.add_argument('--repo',type=Path,required=True);ap.add_argument('--results-dir',type=Path,required=True);ap.add_argument('--deps',type=Path);a=ap.parse_args()
if a.deps:sys.path.insert(0,str(a.deps))
import numpy as np,pandas as pd
T=['age10','female','education','log2plot','log2farm','owned','intercropped','maize'];waves={'Ethiopia':3,'Malawi':4,'Mali':2,'Niger':1,'Nigeria':4,'Tanzania':3,'Uganda':8};countries=sorted(waves)
cols=['country','wave','pw','ea_id_merge','hh_id_merge','plot_area_GPS','farm_size','age_manager','female_manager','formal_education_manager','plot_owned','intercropped','main_crop','nitrogen_kg','inorganic_fertilizer']
if a.plot_data:
 s=pd.read_stata(a.plot_data,columns=cols,convert_categoricals=True);s['country']=s.country.astype(str);s=s[s.country.map(waves).eq(s.wave)&s.plot_area_GPS.between(.05,20)].copy()
 for fld in ['female_manager','formal_education_manager','plot_owned','inorganic_fertilizer','intercropped']:
  if not pd.api.types.is_numeric_dtype(s[fld]):s[fld]=s[fld].astype(str).map({'Yes':1.,'No':0.})
 s['rate_excl']=(s.nitrogen_kg/s.plot_area_GPS).where((s.nitrogen_kg/s.plot_area_GPS).le(300));s['rate_cap']=(s.nitrogen_kg/s.plot_area_GPS).clip(upper=300);s['adoption']=s.inorganic_fertilizer.fillna(0);s.loc[s.country.eq('Ethiopia'),'adoption']=(s.inorganic_fertilizer.eq(1)&s.nitrogen_kg.gt(0)).astype(float)
else:
 s=pd.read_csv(a.survey_traits_csv or a.repo/'data/processed/trait_survey_analysis_input.csv.gz')
f=pd.read_csv(a.repo/'data/processed/frozen_profiles.csv');q=pd.read_csv(a.repo/'data/model_outputs/benchmark_predictions.csv');q=q[q.provider.isin(['claude','codex','kimi'])].groupby(['country','profile_key'],as_index=False).agg(rate=('predicted_n','mean'),adoption=('predicted_adoption','mean'));f['idx']=f.profile_key.str.rsplit('_',n=1).str[-1].astype(int);q['idx']=q.profile_key.str.rsplit('_',n=1).str[-1].astype(int);t=f.merge(q[['country','idx','rate','adoption']],on=['country','idx'],validate='one_to_one');t['pw']=1.
def blank(s):return s.isna()|s.astype(str).str.strip().isin(['','nan'])
def matrix(d,pooled):
 X=pd.DataFrame({'age10':d.age_manager/10,'female':d.female_manager,'education':d.formal_education_manager,'log2plot':np.log2(d.plot_area_GPS),'log2farm':np.log2(d.farm_size),'owned':d.plot_owned,'intercropped':d.intercropped,'maize':d.main_crop.astype(str).eq('MAIZE').astype(float)},index=d.index)
 if pooled:
  for c in countries:X['country_'+c]=d.country.eq(c).astype(float)
 else:X['intercept']=1.
 return X.replace([np.inf,-np.inf],np.nan).astype(float)
DRAWS=pd.read_csv(a.results_dir/'trait_bootstrap_coefficient_draws.csv');checks=[]
# Three draw indices for all pooled specifications and each country-specific model.
for (source,outcome,scheme,scope),stored in DRAWS.groupby(['source','outcome','scheme','scope'],sort=False):
 d=s.copy() if source=='survey'else t.copy()
 if scope!='pooled':d=d[d.country.eq(scope)].copy()
 X=matrix(d,scope=='pooled');ok=X.notna().all(axis=1)&d[outcome].notna()&np.isfinite(d.pw)&d.pw.gt(0);d=d.loc[ok];X=X.loc[ok].to_numpy(float);y=d[outcome].to_numpy(float);w=d.pw.to_numpy(float)
 if source=='ensemble':g=np.arange(len(d)).astype(str)
 else:
  miss=blank(d.ea_id_merge);g=(d.country+'|EA|'+d.ea_id_merge.astype(str)).to_numpy(object)
  g[miss]=(d.loc[miss,'country']+'|HH|'+d.loc[miss,'hh_id_merge'].astype(str)).to_numpy() if scheme=='hybrid'else(d.loc[miss,'country']+'|UNKNOWN_EA_STRESS_TEST').to_numpy()
 codes,levels=pd.factorize(g,sort=False);gc=pd.Series(d.country.to_numpy()).groupby(codes,sort=True).first().to_numpy();nboot=int(stored.draw.max())+1;ixdraw=[0,nboot//2,nboot-1];counts_all=np.zeros((3,len(levels)),int);rng=np.random.default_rng(20260827)
 for country in np.unique(gc):
  ix=np.flatnonzero(gc==country);counts=rng.multinomial(len(ix),np.ones(len(ix))/len(ix),size=nboot);counts_all[:,ix]=counts[ixdraw]
 for k,draw in enumerate(ixdraw):
  sq=np.sqrt(w*counts_all[k,codes]);direct=np.linalg.lstsq(X*sq[:,None],y*sq,rcond=None)[0][:8];archived=stored.loc[stored.draw.eq(draw),T].iloc[0].to_numpy(float);err=float(np.max(np.abs(direct-archived)))
  assert err<1e-7,(source,outcome,scheme,scope,draw,err)
  checks.append({'source':source,'outcome':outcome,'scheme':scheme,'scope':scope,'draw':draw,'max_abs_coefficient_difference':err})
result={'status':'PASS','verification':'Direct row-level weighted least squares with bootstrap multiplicity weights versus per-cluster sufficient-statistic least squares. First/middle/last draws for every pooled and country-specific model.','models':len(checks)//3,'direct_fit_checks':len(checks),'max_abs_error':max(r['max_abs_coefficient_difference']for r in checks),'checks':checks}
(a.results_dir/'direct_bootstrap_arithmetic_verification.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items()if k!='checks'})
