"""Export source data for the farmer-persona figures without model calls."""
import argparse,csv,gzip,json
from pathlib import Path
import numpy as np

def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def archive(path):
    with gzip.open(path,'rt') as f:return [json.loads(line) for line in f]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source_root',type=Path,help='Combined code and data directory')
    a=parser.parse_args();source=a.source_root;out=Path(__file__).resolve().parent/'data';out.mkdir(exist_ok=True)
    persona=source/'persona';results=persona/'results/analysis'
    metrics=json.loads((results/'african_prompt_design_metrics_recomputed.json').read_text())
    paper=json.loads((results/'paper1_metrics.json').read_text())
    rows=[]
    for outcome,cells in metrics.items():
        for key,values in cells.items():
            provider,tier=key.split('_');rows.append({'outcome':outcome,'provider':provider,'tier':tier,**values})
    write_csv(out/'african_configurations.csv',rows)
    rows=[]
    for country,cells in paper['lsms']['by_country'].items():
        for key,values in cells.items():
            provider,tier=key.split('_');rows.append({'country':country,'provider':provider,'tier':tier,**values})
    write_csv(out/'african_country_configurations.csv',rows)
    write_csv(out/'african_nitrogen_reference.csv',[paper['lsms']['reference']['ALL']])
    with (persona/'data/lsms/lsms_4country_full.csv').open() as f:profiles=list(csv.DictReader(f))
    records=[{**r,'tier':1} for r in archive(source/'application/data/model_outputs/raw_model_responses.jsonl.gz') if r['experiment']=='benchmark_original']
    records+=archive(persona/'results/full/lsms/archived_T2_T3_T4.jsonl.gz')
    decisions={(r['provider'],r['tier'],int(r['profile_key'].rsplit('_',1)[1])):r['decision'] for r in records}
    outcomes={'nitrogen_kg_per_ha':'nitrogen_kg_per_ha','family_labor_days':'total_family_labor_days','hired_labor_days':'total_hired_labor_days'}
    quantile_rows=[];cdf_rows=[]
    for outcome,observed_field in outcomes.items():
        observed=np.array([float(p[observed_field] or 'nan') for p in profiles]);valid=np.isfinite(observed);observed=observed[valid]
        floor=.28*np.quantile(observed,.9)
        if outcome=='nitrogen_kg_per_ha':
            for j,value in enumerate(np.sort(observed),1):cdf_rows.append({'provider':'observed','tier':'Observed','value':float(value),'ecdf':j/len(observed),'n':len(observed)})
        for provider in ['claude','codex','kimi']:
            for tier in range(1,5):
                predicted=np.array([float(decisions[provider,tier,i][outcome]) for i in range(len(profiles))])[valid]
                assert np.all(np.isfinite(predicted))
                for percent in range(5,100):
                    q=percent/100;oq=float(np.quantile(observed,q));pq=float(np.quantile(predicted,q))
                    quantile_rows.append({'outcome':outcome,'provider':provider,'tier':f'T{tier}','percentile':percent,'observed_quantile':oq,'predicted_quantile':pq,'floor':float(floor),'display':oq>floor,'ratio':pq/oq if oq>0 else '', 'n':len(observed)})
                if outcome=='nitrogen_kg_per_ha':
                    for j,value in enumerate(np.sort(predicted),1):cdf_rows.append({'provider':provider,'tier':f'T{tier}','value':float(value),'ecdf':j/len(predicted),'n':len(predicted)})
    write_csv(out/'african_percentile_ratios.csv',quantile_rows);write_csv(out/'african_nitrogen_ecdf.csv',cdf_rows)
    print('Exported source datasets; no rows dropped except missing observed outcomes.')
if __name__=='__main__':main()
