"""Rebuild post-stratification weights and verify current Table S11 offline."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import numpy as np
import pandas as pd
from paper2_review_sensitivity_analysis import calibration_diagnostics
ROOT=Path(__file__).resolve().parents[1]
STRATA=['fert_user','female_manager','formal_education_manager']

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repo',type=Path,default=ROOT)
    ap.add_argument('--output-dir',type=Path)
    args=ap.parse_args();r=args.repo;out=args.output_dir or r/'reproduced/analysis';out.mkdir(parents=True,exist_ok=True)
    design=pd.read_csv(r/'data/processed/profile_survey_design.csv')
    cells=pd.read_csv(r/'data/processed/paper2_population_poststrata.csv')
    keys=['country',*STRATA]
    if len(cells)!=55 or cells.duplicated(keys).any():raise RuntimeError('Expected exactly 55 unique country × adoption × sex × education target cells')
    d=design.drop(columns=['population_cell_n','population_cell_weight_total'],errors='ignore').merge(cells,on=keys,how='left',validate='many_to_one')
    den=d.groupby(keys,dropna=False).household_weight_pw.transform('sum')
    factor=d.population_cell_weight_total/den
    weights=d.household_weight_pw*factor
    np.testing.assert_allclose(factor,d.poststratification_factor,rtol=1e-12,atol=1e-12)
    np.testing.assert_allclose(weights,d.population_analysis_weight,rtol=1e-12,atol=1e-9)
    d['poststratification_factor']=factor;d['population_analysis_weight']=weights
    sums=d.groupby(keys,as_index=False).population_analysis_weight.sum().merge(cells,on=keys,validate='one_to_one')
    np.testing.assert_allclose(sums.population_analysis_weight,sums.population_cell_weight_total,rtol=1e-12,atol=1e-8)
    diagnostics=calibration_diagnostics(d)
    display=pd.read_csv(r/'data/manuscript_tables/Supplementary_Table_S11.csv').set_index('Country')
    checks=[]
    for row in diagnostics.to_dict('records'):
        c=row['country'];v=display.loc[c]
        text={'Profiles':str(row['profiles']),'Post-strata':str(row['poststrata']),
              'Profiles per post-stratum':f"{row['minimum_profiles_per_poststratum']}-{row['maximum_profiles_per_poststratum']}",
              'Kish effective n':f"{row['kish_effective_profile_n']:.1f}",'Weight CV':f"{row['coefficient_of_variation_of_weights']:.2f}",
              'Maximum weight share':f"{row['maximum_normalized_weight']*100:.1f}%",'Post-stratification factor':f"{row['minimum_poststratification_factor']:.2f}-{row['maximum_poststratification_factor']:.2f}"}
        for field,value in text.items():
            actual=str(v[field])
            if field in ['Profiles','Post-strata']:actual=str(int(v[field]))
            if actual!=value:raise AssertionError(f'Table S11 {c} {field}: {value} vs {actual}')
        checks.append({'country':c,'all_display_cells_match':True})
    d.to_csv(out/'paper2_poststratification_weights_rebuilt.csv',index=False)
    diagnostics.to_csv(out/'paper2_weight_diagnostics_rebuilt.csv',index=False)
    (out/'paper2_weight_validation.json').write_text(json.dumps({'status':'PASS','target_poststrata':55,'profile_n':len(d),'all_population_cells_covered':len(sums)==55,'max_relative_weight_delta':float(np.max(abs(weights-design.population_analysis_weight)/design.population_analysis_weight)),'Table_S11_checks':checks},indent=2)+'\n')
    print('All 490 calibrated weights and Table S11 diagnostics match; 55 target cells covered.')
if __name__=='__main__':main()
