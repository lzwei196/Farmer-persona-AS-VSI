"""Reproduce corrected survey and LLM trait models, intervals and grouped cross-validation.
The public deidentified analysis table is used by default; --plot-data enables
rebuilding the same model inputs from the cited harmonized Stata source.
Archive intervals used 500 survey and 2000 ensemble draws (seed 20260827).
"""
from pathlib import Path
import argparse, json, hashlib, platform, sys, time, os
os.environ.setdefault('OPENBLAS_NUM_THREADS','1');os.environ.setdefault('OMP_NUM_THREADS','1');os.environ.setdefault('VECLIB_MAXIMUM_THREADS','1')
ap=argparse.ArgumentParser()
ap.add_argument('--plot-data',type=Path,help='Optional original harmonized Plot_dataset.dta; takes precedence over the deidentified CSV.')
ap.add_argument('--survey-traits-csv',type=Path,help='Default: data/processed/trait_survey_analysis_input.csv.gz under --repo.')
ap.add_argument('--ensemble-only',action='store_true',help='Reproduce LLM trait models only, without full-survey input.')
ap.add_argument('--survey-bootstrap',type=int,default=500)
ap.add_argument('--ensemble-bootstrap',type=int,default=2000)
ap.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1],help='Repository root.')
ap.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'reproduced/traits')
ap.add_argument('--reference-audit',type=Path,help='Optional prior independent_trait_cv_bootstrap.json, used only to assert original OLS points and sample sizes unchanged.')
ap.add_argument('--deps',type=Path,help='Optional Python package directory providing numpy/pandas/scipy/sklearn.')
args=ap.parse_args()
W=Path(__file__).parent;OUT=args.output_dir;OUT.mkdir(parents=True,exist_ok=True)
if args.deps:sys.path.insert(0,str(args.deps))
import numpy as np,pandas as pd,scipy,sklearn
from sklearn.model_selection import GroupKFold,KFold
SEED=20260827;START=time.time();TRAITS=['age10','female','education','log2plot','log2farm','owned','intercropped','maize'];COUNTRIES=sorted(['Ethiopia','Malawi','Mali','Niger','Nigeria','Tanzania','Uganda'])
WAVES={'Ethiopia':3,'Malawi':4,'Mali':2,'Niger':1,'Nigeria':4,'Tanzania':3,'Uganda':8}
R=args.repo.resolve();RAW=args.plot_data;F=R/'data/processed/frozen_profiles.csv';Q=R/'data/model_outputs/benchmark_predictions.csv';SURVEY_CSV=args.survey_traits_csv or R/'data/processed/trait_survey_analysis_input.csv.gz'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def blank(x):return x.isna()|x.astype(str).str.strip().isin(['','nan'])
cols=['country','wave','pw','ea_id_merge','hh_id_merge','season','plot_area_GPS','farm_size','age_manager','female_manager','formal_education_manager','plot_owned','intercropped','main_crop','nitrogen_kg','inorganic_fertilizer']
s=None
if not args.ensemble_only:
 if RAW:
  s=pd.read_stata(RAW,columns=cols,convert_categoricals=True);s['country']=s.country.astype(str);s['row_id']=s.index
  s=s[s.country.map(WAVES).eq(s.wave)&s.plot_area_GPS.between(.05,20)].copy()
  for c in ['female_manager','formal_education_manager','plot_owned','inorganic_fertilizer','intercropped']:
   if not pd.api.types.is_numeric_dtype(s[c]):s[c]=s[c].astype(str).map({'Yes':1.,'No':0.})
  s['adoption_indicator_missing']=s.inorganic_fertilizer.isna().astype(int)
  s['rate']=s.nitrogen_kg/s.plot_area_GPS;s['rate_excl']=s.rate.where(s.rate.le(300));s['rate_cap']=s.rate.clip(upper=300);s['adoption']=s.inorganic_fertilizer.fillna(0)
  s.loc[s.country.eq('Ethiopia'),'adoption']=(s.inorganic_fertilizer.eq(1)&s.nitrogen_kg.gt(0)).astype(float)
 else:
  s=pd.read_csv(SURVEY_CSV);RAW=SURVEY_CSV
  if 'row_id' not in s:s['row_id']=s.index
f=pd.read_csv(F);q=pd.read_csv(Q);q=q[q.provider.isin(['claude','codex','kimi'])].groupby(['country','profile_key'],as_index=False).agg(rate=('predicted_n','mean'),adoption=('predicted_adoption','mean'))
f['idx']=f.profile_key.str.rsplit('_',n=1).str[-1].astype(int);q['idx']=q.profile_key.str.rsplit('_',n=1).str[-1].astype(int)
t=f.merge(q[['country','idx','rate','adoption']],on=['country','idx'],validate='one_to_one');t['row_id']=t.index;t['pw']=1.
def design(d,pooled=True):
 z=pd.DataFrame({'age10':d.age_manager/10,'female':d.female_manager,'education':d.formal_education_manager,'log2plot':np.log2(d.plot_area_GPS),'log2farm':np.log2(d.farm_size),'owned':d.plot_owned,'intercropped':d.intercropped,'maize':d.main_crop.astype(str).eq('MAIZE').astype(float)},index=d.index)
 if pooled:
  for c in COUNTRIES:z['country_'+c]=d.country.eq(c).astype(float)
 else:z['intercept']=1.
 return z.replace([np.inf,-np.inf],np.nan).astype(float)
def solve(X,y,w):return np.linalg.lstsq(X*np.sqrt(w[:,None]),y*np.sqrt(w),rcond=None)[0]
def groups(d,scheme):
 if scheme=='profile':return np.arange(len(d)).astype(str)
 b=blank(d.ea_id_merge);g=(d.country+'|EA|'+d.ea_id_merge.astype(str)).to_numpy(dtype=object)
 assert not blank(d.loc[b,'hh_id_merge']).any()
 g[b]=(d.loc[b,'country']+'|HH|'+d.loc[b,'hh_id_merge'].astype(str)).to_numpy() if scheme=='hybrid' else (d.loc[b,'country']+'|UNKNOWN_EA_STRESS_TEST').to_numpy()
 return g
ALLCO=[];ALLDRAWS=[];ALLFOLDS=[];RESULTS=[];RANKS=[]
def bootstrap(X,y,w,g,c,reps):
 codes,levels=pd.factorize(g,sort=False);G=len(levels);D=X.shape[1];xx=np.zeros((G,D,D));xy=np.zeros((G,D))
 np.add.at(xx,codes,X[:,:,None]*X[:,None,:]*w[:,None,None]);np.add.at(xy,codes,X*y[:,None]*w[:,None])
 gc=pd.Series(c).groupby(codes,sort=True).first().to_numpy();rng=np.random.default_rng(SEED);bx=np.zeros((reps,D,D));by=np.zeros((reps,D))
 for name in np.unique(gc):
  ix=np.flatnonzero(gc==name);counts=rng.multinomial(len(ix),np.ones(len(ix))/len(ix),size=reps)
  bx+=np.einsum('bg,gij->bij',counts,xx[ix],optimize=True);by+=counts@xy[ix]
 co=np.array([np.linalg.lstsq(a,b,rcond=None)[0] for a,b in zip(bx,by)])
 return np.quantile(co,[.025,.975],axis=0),co,G

def fit_model(d,outcome,source,scheme,scope='pooled',do_cv=True):
 pooled=scope=='pooled';z=design(d,pooled=pooled);mask=z.notna().all(axis=1)&d[outcome].notna()&np.isfinite(d.pw)&d.pw.gt(0)
 d=d.loc[mask].copy();X=z.loc[mask].to_numpy(float);y=d[outcome].to_numpy(float);w=d.pw.to_numpy(float);c=d.country.to_numpy();g=groups(d,scheme);co=solve(X,y,w);reps=args.survey_bootstrap if source=='survey' else args.ensemble_bootstrap
 (lo,hi),draws,G=bootstrap(X,y,w,g,c,reps);rank=int(np.linalg.matrix_rank(X*np.sqrt(w[:,None])));p=X.shape[1]
 RANKS.append({'source':source,'outcome':outcome,'scheme':scheme,'scope':scope,'n':len(d),'rank':rank,'p':p,'constant_traits':[TRAITS[j] for j in range(8) if np.ptp(X[:,j])==0]})
 for j,trait in enumerate(TRAITS):
  ALLCO.append({'source':source,'outcome':outcome,'scheme':scheme,'scope':scope,'trait':trait,'n':len(d),'clusters':G,'point':float(co[j]),'ci_low':float(lo[j]),'ci_high':float(hi[j]),'clearly_nonzero':bool(lo[j]>0 or hi[j]<0),'constant_in_sample':bool(np.ptp(X[:,j])==0)})
 for i,b in enumerate(draws):ALLDRAWS.append({'source':source,'outcome':outcome,'scheme':scheme,'scope':scope,'draw':i,**dict(zip(TRAITS,map(float,b[:8])))})
 result={'source':source,'outcome':outcome,'scheme':scheme,'scope':scope,'n':len(d),'clusters':G,'bootstrap_repetitions':reps,'seed':SEED,'coefficients':{tr:{'point':float(co[j]),'ci_low':float(lo[j]),'ci_high':float(hi[j])} for j,tr in enumerate(TRAITS)}}
 if do_cv:
  pred=np.zeros(len(d));base=np.zeros(len(d));folds=5 if source=='survey' else 10
  splitter=GroupKFold(n_splits=folds,shuffle=True,random_state=SEED) if source=='survey' else KFold(n_splits=folds,shuffle=True,random_state=SEED)
  Z=X[:,8:];fold_counts=[]
  for fold,(tr,te) in enumerate(splitter.split(X,y,g if source=='survey' else None)):
   assert not set(g[tr]).intersection(g[te])
   pred[te]=X[te]@solve(X[tr],y[tr],w[tr]);base[te]=Z[te]@solve(Z[tr],y[tr],w[tr]);fold_counts.append({'fold':fold,'test_rows':len(te),'test_clusters':len(np.unique(g[te]))})
   for j in te:ALLFOLDS.append({'source':source,'outcome':outcome,'scheme':scheme,'row_id':int(d.iloc[j].row_id),'country':c[j],'fold':fold})
  result['cv']={'folds':folds,'seed':SEED,'within_country_oos_r2':float(1-np.sum(w*(y-pred)**2)/np.sum(w*(y-base)**2)),'weighted_full_sse':float(np.sum(w*(y-pred)**2)),'weighted_training_country_baseline_sse':float(np.sum(w*(y-base)**2)),'test_fold_counts':fold_counts}
 RESULTS.append(result);print(source,outcome,scheme,scope,'n',len(d),'G',G,'rank',rank,'r2',result.get('cv',{}).get('within_country_oos_r2'),'seconds',round(time.time()-START,1),flush=True)
 return result

if s is not None:
 for outcome in ['adoption','rate_excl','rate_cap']:
  fit_model(s,outcome,'survey','hybrid');fit_model(s,outcome,'survey','unknown_country_bucket_stress_test')
  for c in COUNTRIES:fit_model(s[s.country.eq(c)],outcome,'survey','hybrid',scope=c,do_cv=False)
for outcome in ['adoption','rate']:
 fit_model(t,outcome,'ensemble','profile')
 for c in COUNTRIES:fit_model(t[t.country.eq(c)],outcome,'ensemble','profile',scope=c,do_cv=False)
co=pd.DataFrame(ALLCO);co.to_csv(OUT/'trait_coefficients_full_precision.csv',index=False);pd.DataFrame(ALLDRAWS).to_csv(OUT/'trait_bootstrap_coefficient_draws.csv',index=False);pd.DataFrame(ALLFOLDS).to_csv(OUT/'trait_cv_fold_assignments.csv',index=False);pd.DataFrame(RANKS).to_csv(OUT/'trait_design_rank_checks.csv',index=False)
# Assert all 40 pooled OLS points unchanged relative to earlier full-precision audit.
ASSERTIONS=[]
if args.reference_audit:
 old=json.loads(args.reference_audit.read_text())
 for v in RESULTS:
  if v['scope']!='pooled':continue
  o=next(r for r in old['results'] if r['source']==v['source'] and r['outcome']==v['outcome'])
  delta=max(abs(v['coefficients'][tr]['point']-o['coefficients'][tr]['point']) for tr in TRAITS)
  assert v['n']==o['n'];assert delta<1e-10,(v['source'],v['outcome'],delta)
  ASSERTIONS.append({'source':v['source'],'outcome':v['outcome'],'scheme':v['scheme'],'n_unchanged':True,'max_abs_point_delta':delta})
SUMMARY=[]
for outcome in ([] if s is None else ['adoption','rate_excl','rate_cap']):
 eout='adoption' if outcome=='adoption' else 'rate'
 a=co[(co.source=='survey')&(co.outcome==outcome)&(co.scheme=='hybrid')];b=co[(co.source=='ensemble')&(co.outcome==eout)]
 ap=a[a.scope=='pooled'].set_index('trait').reindex(TRAITS);bp=b[b.scope=='pooled'].set_index('trait').reindex(TRAITS)
 ct=a[a.scope!='pooled'].merge(b[b.scope!='pooled'],on=['scope','trait'],suffixes=('_survey','_ensemble'))
 ct['same_sign']=np.sign(ct.point_survey)==np.sign(ct.point_ensemble);ct['survey_nonzero']=ct.clearly_nonzero_survey&~ct.constant_in_sample_survey
 ct.to_csv(OUT/f'country_trait_sign_comparison_{outcome}.csv',index=False)
 vr=next(v for v in RESULTS if v['source']=='survey'and v['outcome']==outcome and v['scope']=='pooled' and v['scheme']=='hybrid')
 er=next(v for v in RESULTS if v['source']=='ensemble'and v['outcome']==eout and v['scope']=='pooled')
 sr=next(v for v in RESULTS if v['source']=='survey'and v['outcome']==outcome and v['scope']=='pooled' and v['scheme']=='unknown_country_bucket_stress_test')
 SUMMARY.append({'outcome':outcome,'survey_n':vr['n'],'survey_clusters':vr['clusters'],'survey_cv_r2':vr['cv']['within_country_oos_r2'],'ensemble_n':er['n'],'ensemble_cv_r2':er['cv']['within_country_oos_r2'],'absolute_coefficient_ratio':float(bp.point.abs().sum()/ap.point.abs().sum()),'predicted_coefficients_outside_survey_ci':int(((bp.point<ap.ci_low)|(bp.point>ap.ci_high)).sum()),'country_trait_survey_clearly_nonzero':int(ct.survey_nonzero.sum()),'country_trait_same_sign_among_survey_nonzero':int((ct.survey_nonzero&ct.same_sign).sum()),'country_trait_all_same_sign':int(ct.same_sign.sum()),'stress_test_cv_r2':sr['cv']['within_country_oos_r2']})
pd.DataFrame(SUMMARY).to_csv(OUT/'trait_summary.csv',index=False)
# Complete-case adoption sensitivity (Table S10); no additional resampling.
if s is not None and 'adoption_indicator_missing' in s:
 z=design(s);ok=z.notna().all(axis=1)&s.adoption.notna()&np.isfinite(s.pw)&s.pw.gt(0)
 primary=solve(z.loc[ok].to_numpy(float),s.loc[ok,'adoption'].to_numpy(float),s.loc[ok,'pw'].to_numpy(float))[:8]
 cc=ok & ~s.adoption_indicator_missing.astype(bool)
 complete=solve(z.loc[cc].to_numpy(float),s.loc[cc,'adoption'].to_numpy(float),s.loc[cc,'pw'].to_numpy(float))[:8]
 ccrows=pd.DataFrame({'trait':TRAITS,'primary_coefficient':primary,'complete_case_coefficient':complete,'difference':complete-primary})
 ccrows.to_csv(OUT/'trait_adoption_complete_case_sensitivity.csv',index=False)
 cc_check={'primary_n':int(ok.sum()),'complete_case_n':int(cc.sum()),'excluded_missing_indicator':int((ok&~cc).sum()),'all_eight_signs_unchanged':bool(np.all(np.sign(primary)==np.sign(complete))),'max_absolute_change':float(np.max(abs(complete-primary)))}
 assert cc_check['primary_n']==64917 and cc_check['complete_case_n']==64519
 assert cc_check['all_eight_signs_unchanged'] and cc_check['max_absolute_change']<0.0001
 display=R/'data/manuscript_tables/Supplementary_Table_S10.csv'
 if display.exists():
  disp=pd.read_csv(display)
  for field,column in [('primary_coefficient','Primary coefficient'),('complete_case_coefficient','Complete-case coefficient'),('difference','Difference')]:
   assert np.allclose(ccrows[field].round(6),disp[column].astype(float),atol=1e-9),('Table S10',field)
  cc_check['current_Table_S10_rounding_matches']=True
 (OUT/'trait_adoption_complete_case_checks.json').write_text(json.dumps(cc_check,indent=2)+'\n')
report={'status':'Necessary deterministic correction; original manuscript CI/fold implementation not located. OLS points, samples and weights unchanged.','software':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scipy':scipy.__version__,'sklearn':sklearn.__version__},'inputs':[{'name':p.name,'sha256':sha(p)}for p in [RAW,F,Q] if p is not None],'required_inputs_note':'The default survey input is the public deidentified trait analysis table. The original cited harmonized Plot_dataset.dta can be supplied instead. CV output row_id denotes anonymous input order for the public table; no original household or enumeration-area identifier is exported.','methods':{'traits':TRAITS,'survey_point_model':'Unpenalized weighted least squares with country fixed effects; eight traits; household pw applied to plot rows.','ensemble_point_model':'Same traits/country fixed effects, unweighted provider-ensemble predictions.','adoption':'Missing inorganic-fertilizer responses coded zero; Ethiopia requires inorganic_fertilizer=1 and positive nitrogen_kg, matching frozen definition.','survey_primary_cluster':'country x known EA; missing EA uses country x household, retaining all seasons/plots of each household.','bootstrap':f'With replacement at cluster/profile level within each country; supplied analysis weights unchanged; percentile 2.5/97.5 intervals; {args.survey_bootstrap} survey/{args.ensemble_bootstrap} ensemble draws (archive: 500/2000).' ,'cv':'Survey: 5-fold shuffled GroupKFold at cluster level. Ensemble: 10-fold shuffled KFold at profile level. R2=1 - heldout weighted full-model SSE / heldout weighted SSE of country-only model fit in each training fold.','country_models':'Same eight traits plus intercept, separately by country; primary cluster/profile bootstrap and seed as pooled models.','stress_test':'All rows with unknown EA in each country placed in one artificial cluster; diagnostic sensitivity only, neither a recovered EA nor a conservative uncertainty bound.','seed':SEED,'limitation':'Unknown-EA fallback covers dependence within households, not residual dependence between different households from the same unknown EA. Uganda missing-EA records comprise 61.3% of its analysis weight. Intervals do not represent complete survey-design uncertainty.'},'ols_unchanged_assertions':ASSERTIONS,'summary':SUMMARY,'results':RESULTS,'rank_checks':RANKS,'elapsed_seconds':time.time()-START}
(OUT/'trait_correction_results.json').write_text(json.dumps(report,indent=2)+'\n');print('SUMMARY',json.dumps(SUMMARY,indent=2));print('DONE',round(time.time()-START,1))
