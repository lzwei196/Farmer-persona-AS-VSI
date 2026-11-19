"""Run the public archive's analyses and figure exports without making LLM calls."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parent

def run(script,*args):
    print('Running:',script,*args,flush=True)
    subprocess.run([sys.executable,str(ROOT/script),*map(str,args)],cwd=ROOT,check=True)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bootstrap',type=int,default=200,help='Core bootstrap draws. Use 10000 to reproduce the archived core intervals; default 200 is a quick run.')
    ap.add_argument('--skip-figures',action='store_true')
    ap.add_argument('--plot-data',type=Path,help='Optional cited harmonized Plot_dataset.dta to rebuild survey traits from source rather than the included analysis CSV.')
    ap.add_argument('--survey-traits-csv',type=Path,help='Optional override for the included deidentified full-survey trait table.')
    ap.add_argument('--require-external-data',action='store_true',help='Require --plot-data and run the source survey-design recovery in addition to public derived-data reproduction.')
    ap.add_argument('--rebuild-survey-design',action='store_true',help='Also reconstruct survey weights/targets from --plot-data, writing only under ignored reproduced/.')
    args=ap.parse_args()
    if args.bootstrap<=0:ap.error('--bootstrap must be positive')
    if args.plot_data and not args.plot_data.is_file():ap.error('--plot-data does not exist')
    if args.require_external_data and not args.plot_data:ap.error('--require-external-data needs --plot-data')
    if args.rebuild_survey_design and not args.plot_data:ap.error('--rebuild-survey-design needs --plot-data')
    out=ROOT/'reproduced';out.mkdir(exist_ok=True)
    report={'started_utc':datetime.now(timezone.utc).isoformat(),'core_bootstrap_draws':args.bootstrap,'completed':[],'not_reproduced':[]}
    run('scripts/validate_release.py');report['completed'].append('release_integrity_and_response_manifest_checks')
    run('scripts/reproduce_summary.py','--check');report['completed'].append('headline_point_estimates')
    run('scripts/reproduce_core_analyses.py','--bootstrap',args.bootstrap);report['completed'].append('seven_core_analysis_modules_and_archived_point_comparison')
    run('src/paper2_weight_validation.py');report['completed'].append('55_cell_weight_reconstruction_and_Table_S11_checks')
    run('src/paper2_national_statistics_audit.py');report['completed'].append('rounded_input_national_statistics_audit_only')
    report['not_reproduced'].append({'analysis':'exact_original_national_statistics_benchmark','reason':'Original full-precision annual series, survey-year mapping and conditional-bootstrap implementation were not retained. Reported Table S8 is an archived display snapshot; the rounded-input audit is approximate.'})
    traitargs=['--repo',ROOT,'--output-dir',out/'traits']
    if args.plot_data:traitargs+=['--plot-data',args.plot_data]
    elif args.survey_traits_csv:traitargs+=['--survey-traits-csv',args.survey_traits_csv]
    survey=args.survey_traits_csv or ROOT/'data/processed/trait_survey_analysis_input.csv.gz'
    has_survey=bool(args.plot_data or survey.is_file())
    if not has_survey:
        traitargs+=['--ensemble-only'];report['not_reproduced'].append({'analysis':'full_survey_trait_models','reason':'No original Plot_dataset.dta or deidentified trait analysis CSV supplied.'})
    # Trait intervals use their own published repetition counts, not the core count.
    run('src/paper2_trait_models.py',*traitargs)
    report['completed'].append('survey_and_ensemble_trait_models_500_and_2000_draws' if has_survey else 'ensemble_trait_models_only_2000_draws')
    if args.rebuild_survey_design or args.require_external_data:
        run('src/prepare_survey_analysis_inputs.py','--plot-data',args.plot_data,'--output-dir',out/'source_inputs')
        run('src/paper2_recover_survey_design.py','--plot-data',args.plot_data,'--output-dir',out/'survey_design')
        report['completed'].append('source_survey_design_recovery')
    else:
        report['not_reproduced'].append({'analysis':'source_survey_design_recovery','reason':'Archived deidentified design/targets used. Reconstructing from the original harmonized survey is optional with --plot-data and --rebuild-survey-design.'})
    if not args.skip_figures:
        run('figures/run_all.py','--output-dir',out/'figures');report['completed'].append('all_main_and_supplementary_figure_exports')
    else:report['not_reproduced'].append({'analysis':'figure_exports','reason':'--skip-figures requested'})
    report['finished_utc']=datetime.now(timezone.utc).isoformat()
    report['status']='completed_with_reported_provenance_limits'
    (out/'workflow_report.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Public-data workflow completed. See reproduced/workflow_report.json for what ran and the remaining provenance limits.')

if __name__=='__main__':main()
