"""Assemble the documented plotting snapshot from local archived/reported inputs.

This does not fit regressions or infer values from the accepted PNG.
"""
from pathlib import Path
import csv
import re
HERE = Path(__file__).resolve().parent
dat = HERE / "data"
old = dat / "Fig2_population_calibration_legacy.csv"
rows=list(csv.DictReader(old.open())); si=dat/'Table_S8a_reported.csv'
reported={r['Country']:r for r in csv.DictReader(si.open(encoding='utf-8-sig'))}
cap_path=dat/'paper2_country_wave_capped_sensitivity_targets.csv'
caps={r['country']:r for r in csv.DictReader(cap_path.open())}
provenance=[]
def put(row,col,val,source,precision):
 row[col]=val
 provenance.append({'country':row['country'],'variable':col,'value':val,'source':source,'precision':precision})
for row in rows:
 c=row['country'];s=reported[c]
 for col,val in list(row.items()):
  if col!='country':
   provenance.append({'country':c,'variable':col,'value':val,'source':'Fig2_population_calibration_legacy.csv; archived population analysis','precision':'full-precision archived CSV'})
 # CIs for rate/adoption are taken from the supplied current Table S8, not refitted.
 for heading,col,dp in [('LLM N rate (95% CI)','predicted_n_kg_per_ha',2),('LLM adoption (95% CI)','predicted_adoption',3)]:
  vv=[float(v) for v in re.findall(r'[-+]?\d*\.?\d+',s[heading])]
  assert len(vv)==3
  for tail,val in zip(['_lo','_hi'],vv[1:]):
   provenance=[v for v in provenance if not(v['country']==c and v['variable']==col+tail)]
   put(row,col+tail,val,'current Table S8a',f'{dp} decimal places (reported)')
 put(row,'regression_n_kg_per_ha',float(s['Regression N rate']),'current Table S8a','2 decimal places (reported)')
 put(row,'regression_adoption',float(s['Regression adoption']),'current Table S8a','3 decimal places (reported)')
 put(row,'capped_n_kg_per_ha',float(caps[c]['survey_weighted_mean_capped_n_kg_per_ha']),'paper2_country_wave_capped_sensitivity_targets.csv','full-precision aggregate derived from source survey')
 put(row,'capped_n_kg_per_plot',float(caps[c]['survey_weighted_mean_capped_n_kg_per_plot']),'paper2_country_wave_capped_sensitivity_targets.csv','full-precision aggregate derived from source survey')
with (dat/'Fig2_plotting_values.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
with (dat/'Fig2_input_provenance.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=['country','variable','value','source','precision']);w.writeheader();w.writerows(provenance)

print('Fig2 mixed-precision inputs ready:',len(rows),'countries',len(provenance),'numeric cells')
