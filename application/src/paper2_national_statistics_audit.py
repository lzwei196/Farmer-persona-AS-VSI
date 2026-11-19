"""Approximate the national-statistics benchmark from retained rounded inputs.

This is NOT the missing original full-precision analysis. It does not overwrite
reported Table S8 values or pretend to reproduce its original interval endpoints.
The annual FAO/World Bank series and exact survey-year mapping were not retained.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
ROOT=Path(__file__).resolve().parents[1]

def number(v):
    return float(re.match(r'[+−-]?\d+(?:\.\d+)?',str(v)).group(0).replace('−','-'))

def loco(x,y,adoption=False):
    out=[]
    for i in range(len(x)):
        take=np.arange(len(x))!=i
        b=np.linalg.lstsq(np.c_[np.ones(take.sum()),x[take]],y[take],rcond=None)[0]
        pred=float(np.r_[1,x[i]]@b)
        out.append(np.clip(pred,0,1) if adoption else max(0,pred))
    return np.array(out)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,default=ROOT)
    ap.add_argument('--output-dir',type=Path)
    args=ap.parse_args();r=args.repo;out=args.output_dir or r/'reproduced/analysis';out.mkdir(parents=True,exist_ok=True)
    f=pd.read_csv(r/'data/manuscript_tables/Supplementary_Table_S8a.csv',encoding='utf-8-sig').set_index('Country')
    for c in f.columns:f[c]=f[c].map(number)
    pop=pd.read_csv(r/'data/analysis/paper2_population_consequence.csv');pop=pop[pop.provider.eq('ensemble')].set_index('country').loc[f.index]
    rows=[];summary=[]
    specifications=[('N rate','Survey N rate','predicted_n_kg_per_ha','Regression N rate',False),('N rate capped','Capped N rate','predicted_n_kg_per_ha','Regression N rate, capped',False),('Adoption','Survey adoption','predicted_adoption','Regression adoption',True)]
    for label,targetcol,llmcol,regcol,adopt in specifications:
        x=f['FAO statistic'].to_numpy(float);y=f[targetcol].to_numpy(float)
        if label!='N rate capped':y=pop['observed_adoption' if adopt else 'observed_n_kg_per_ha'].to_numpy(float)
        else:
            cp=r/'data/processed/paper2_country_wave_capped_sensitivity_targets.csv'
            if cp.exists():y=pd.read_csv(cp).set_index('country').loc[f.index,'survey_weighted_mean_capped_n_kg_per_ha'].to_numpy(float)
        rp=loco(x,y,adopt);llm=pop[llmcol].to_numpy(float)
        for i,country in enumerate(f.index):rows.append({'outcome':label,'country':country,'rounded_fao_statistic':x[i],'target':y[i],'approximate_loco_prediction':rp[i],'reported_regression_prediction':f.loc[country,regcol],'approximate_minus_reported':rp[i]-f.loc[country,regcol]})
        summary.append({'outcome':label,'country_n':len(y),'r_with_rounded_statistic':float(pearsonr(x,y).statistic),'llm_mae':float(np.mean(abs(llm-y))),'approximate_regression_mae':float(np.mean(abs(rp-y))),'rounded_source_only':True})
    pd.DataFrame(rows).to_csv(out/'paper2_national_statistics_rounded_audit.csv',index=False)
    (out/'paper2_national_statistics_rounded_audit.json').write_text(json.dumps({'status':'approximate_point_reconstruction_only','exact_original_analysis_reproduced':False,'unavailable':['Full-precision annual external statistic series','Exact year mapping for surveys spanning calendar years','Original conditional-bootstrap code/endpoints'],'input':'Retained rounded FAO statistic in Table S8a; targets use full-precision archived aggregate data when available.','summary':summary},indent=2)+'\n')
    print('National-statistics benchmark: rounded-input audit only; exact original reproduction is unavailable.')
    print(pd.DataFrame(summary).to_string(index=False))
if __name__=='__main__':main()
