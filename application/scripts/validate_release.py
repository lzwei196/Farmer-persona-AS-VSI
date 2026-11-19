from __future__ import annotations
import argparse,ast,csv,gzip,hashlib,json,re
from pathlib import Path
from collections import Counter
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
EXCLUDED={'.git','.venv','__pycache__','.pytest_cache','.matplotlib','reproduced','results','rendered'}
INTEGRITY={'FILE_MANIFEST.csv','SHA256SUMS.txt'}
SECRET_PATTERNS=[r'sk-[A-Za-z0-9]{20,}',r'ghp_[A-Za-z0-9]{20,}',r'github_pat_[A-Za-z0-9_]{20,}',r'AKIA[0-9A-Z]{16}']
LOCAL_PATH_PATTERNS=[r'[A-Za-z]:\\Users\\',r'/Users/',r'/media/server/',r'/home/']
def files():return sorted([p for p in ROOT.rglob('*') if p.is_file() and p.name!='.DS_Store' and not set(p.relative_to(ROOT).parts)&EXCLUDED],key=lambda p:p.relative_to(ROOT).as_posix())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 ap=argparse.ArgumentParser(description='Validate all unified release inputs, source coverage and checksums.');ap.add_argument('--strict-publication',action='store_true');ap.add_argument('--skip-integrity',action='store_true',help='Only while intentionally rebuilding checksum manifests.');a=ap.parse_args();fail=[];pending=[];allfiles=files()
 for p in allfiles:
  rel=p.relative_to(ROOT).as_posix()
  if p.suffix.lower() in {'.env','.dta','.docx'}:fail.append(f'Unexpected credential, external survey or manuscript file: {rel}')
  if p.stat().st_size>100*1024*1024:fail.append(f'File exceeds100MiB; use official data acquisition route: {rel}')
  if p.suffix.lower()=='.py':
   try:ast.parse(p.read_text(encoding='utf-8'))
   except SyntaxError:fail.append(f'Python syntax error: {rel}')
  if p.suffix.lower() in {'.md','.py','.txt','.json','.csv','.cff','.yml','.yaml','.gz'} and p.name not in INTEGRITY:
   if p.suffix.lower()=='.gz':
    with gzip.open(p,'rt',encoding='utf-8',errors='strict') as handle:text=handle.read()
   else:text=p.read_text(encoding='utf-8',errors='ignore')
   patterns=SECRET_PATTERNS+(LOCAL_PATH_PATTERNS if p.resolve()!=Path(__file__).resolve() else [])
   for pat in patterns:
    if re.search(pat,text):fail.append(f'Credential or machine-path pattern in {rel}; pattern={pat!r}')
 # Check package structure before data reads.
 required=['README.md','README_zh.md','CITATION.cff','LICENSE','DATA_LICENSE.md','requirements.txt','run_all.py','docs/REPRODUCIBILITY.md','docs/REPOSITORY_MAP.md','docs/REPRODUCTION_LIMITS.md','data/processed/frozen_profiles.csv','data/model_outputs/benchmark_predictions.csv','data/model_outputs/raw_model_responses.jsonl.gz','data/processed/trait_survey_analysis_input.csv.gz','data/processed/paper2_population_poststrata.csv','data/raw/source_data_manifest.json','docs/ANALYSIS_COVERAGE.csv','data/provenance/table_data_coverage.csv','figures/run_all.py']
 required += [f'figures/Fig{i}/Fig{i}.py'for i in range(2,9)]+['figures/Fig1/export_fig1.py','figures/SuppFigS1/SuppFigS1.py']
 required += [f'figures/{n}/outputs/{n}.{ext}' for n in [f'Fig{i}'for i in range(2,9)]+['SuppFigS1'] for ext in ['png','pdf','svg']]+['figures/Fig1/outputs/Fig1.png','figures/Fig1/outputs/Fig1.pdf']
 required += [f'data/manuscript_tables/Table_{i}.csv'for i in range(1,4)]
 required += [f'data/manuscript_tables/Supplementary_Table_S{i}.csv'for i in list(range(1,8))+list(range(9,13))]
 # S8 is a two-panel table, not a missing S number.
 required += ['data/manuscript_tables/Supplementary_Table_S8a.csv','data/manuscript_tables/Supplementary_Table_S8b.csv']
 for n in required:
  if not (ROOT/n).is_file():fail.append(f'Missing required release file: {n}')
 if fail:raise SystemExit('Release validation failed:\n- '+'\n- '.join(fail))
 profiles=pd.read_csv(ROOT/'data/processed/frozen_profiles.csv');assert len(profiles)==490
 if not profiles.groupby('country').size().eq(70).all():fail.append('Frozen profiles are not70/country')
 pred=pd.read_csv(ROOT/'data/model_outputs/benchmark_predictions.csv')
 if not pred.groupby(['provider','country']).size().eq(70).all():fail.append('Benchmark adoption cohorts are not70/interface/country')
 if pred.provider.eq('ensemble').sum()!=490:fail.append('Benchmark ensemble is not490profiles')
 with gzip.open(ROOT/'data/model_outputs/raw_model_responses.jsonl.gz','rt',encoding='utf-8') as f:records=[json.loads(x)for x in f]
 expected={'benchmark_original':840,'benchmark_extension':630,'country_label_ablation':630,'country_prior_matrix':1470}
 if dict(Counter(r.get('experiment')for r in records))!=expected:fail.append('Core experiment row counts differ')
 distinct={tuple(r.get(k)for k in ['provider','profile_key','prompt_sha256','timestamp_utc','raw_response'])for r in records}
 if len(distinct)!=3150:fail.append('Distinct core accepted-response count differs from3150')
 for r in records:
  if {'farmer_id','hh_id','plot_id','source_file','profile_id'}&r.keys():fail.append('Core response archive includes original-source ID fields');break
 manifest_specs={'benchmark_extension':('extension_confirmatory_manifest.csv',['profile_key']),'country_label_ablation':('country_label_ablation_manifest.csv',['profile_key','arm']),'country_prior_matrix':('country_prior_matrix_manifest.csv',['profile_key','assigned_country'])}
 for experiment,(fn,keys) in manifest_specs.items():
  mf=pd.read_csv(ROOT/'config/manifests'/fn,dtype=str);hashes={tuple(row[k]for k in keys):row['prompt_sha256']for _,row in mf.iterrows()}
  if any(r.get('prompt_sha256')!=hashes.get(tuple(str(r[k])for k in keys))for r in records if r['experiment']==experiment):fail.append(f'Prompt manifest mismatch: {experiment}')
 # Preserve pseudonyms in every released study profile/design table.
 for p in list((ROOT/'data/profiles').glob('*.csv'))+[ROOT/'data/processed/profile_survey_design.csv']:
  d=pd.read_csv(p,dtype=str)
  for c,prefix in [('hh_id_merge','HH_'),('plot_id_merge','PL_')]:
   if c in d and not d[c].dropna().str.startswith(prefix).all():fail.append(f'Original identifiers in {p.name}:{c}')
 # Additional datasets complete the current supplementary analyses.
 traits=pd.read_csv(ROOT/'data/processed/trait_survey_analysis_input.csv.gz')
 if len(traits)!=64917 or int(traits.adoption_indicator_missing.sum())!=398:fail.append('Full-survey trait input or missing-adoption flag counts differ')
 for col,prefix in [('ea_id_merge','EA_'),('hh_id_merge','HH_')]:
  if not traits[col].dropna().str.startswith(prefix).all():fail.append(f'Unmasked full-survey identifier: {col}')
 poststrata=pd.read_csv(ROOT/'data/processed/paper2_population_poststrata.csv')
 if len(poststrata)!=55:fail.append('Population poststrata count differs from55')
 source=json.loads((ROOT/'data/raw/source_data_manifest.json').read_text())
 if source.get('version')!='v2.0' or source.get('doi')!='10.5281/zenodo.15774761' or source.get('license',{}).get('id')!='cc-zero' or len(source.get('files',[]))!=4:fail.append('Official source version, licence or file count differs')
 # Coverage maps must point to files/directories that are actually distributed.
 for filename,columns in [('docs/ANALYSIS_COVERAGE.csv',['inputs','code']),('data/provenance/table_data_coverage.csv',['display_snapshot','numeric_or_design_sources'])]:
  with (ROOT/filename).open(encoding='utf-8',newline='') as handle:
   for row in csv.DictReader(handle):
    for column in columns:
     for target in row[column].split(';'):
      if not (ROOT/target.strip()).exists():fail.append(f'Missing coverage-map path in {filename}: {target}')
 if not a.skip_integrity:
  data_manifest=pd.read_csv(ROOT/'data/DATA_FILE_MANIFEST.csv')
  data_actual={path.relative_to(ROOT).as_posix()for path in allfiles if path.is_relative_to(ROOT/'data') and path.name!='DATA_FILE_MANIFEST.csv'}
  if set(data_manifest.path)!=data_actual:fail.append('Data manifest coverage differs')
  for row in data_manifest.itertuples(index=False):
   path=ROOT/row.path
   if not path.is_file() or path.stat().st_size!=row.size_bytes or sha(path)!=row.sha256:fail.append(f'Data manifest mismatch: {row.path}')
  figure_manifest=json.loads((ROOT/'figures/SOURCE_MANIFEST.json').read_text())
  figure_actual={path.relative_to(ROOT/'figures').as_posix()for path in allfiles if path.is_relative_to(ROOT/'figures') and path.name!='SOURCE_MANIFEST.json'}
  if {row['path']for row in figure_manifest['files']}!=figure_actual:fail.append('Figure manifest coverage differs')
  for row in figure_manifest['files']:
   path=ROOT/'figures'/row['path']
   if not path.is_file() or path.stat().st_size!=row['bytes'] or sha(path)!=row['sha256']:fail.append(f'Figure manifest mismatch: {row["path"]}')
  mf=pd.read_csv(ROOT/'FILE_MANIFEST.csv');actual={p.relative_to(ROOT).as_posix()for p in allfiles if p.relative_to(ROOT).as_posix()not in INTEGRITY}
  if set(mf.path)!=actual:fail.append('Manifest file coverage does not match release contents')
  for row in mf.itertuples(index=False):
   p=ROOT/row.path
   if not p.is_file() or p.stat().st_size!=row.bytes or sha(p)!=row.sha256:fail.append(f'Integrity mismatch: {row.path}')
  lines={x.split('  ',1)[1]:x.split('  ',1)[0]for x in (ROOT/'SHA256SUMS.txt').read_text().splitlines()if x}
  if lines!=dict(zip(mf.path,mf.sha256)):fail.append('SHA256SUMS differs from manifest')
 citation=(ROOT/'CITATION.cff').read_text()
 if citation.count('family-names: Wei\n    given-names: Qi')>1:pending.append('Two identically named authors mirror the manuscript and need identity confirmation')
 if 'repository-code:'not in citation:pending.append('Public study repository URL/DOI has not been supplied')
 if 'has not been recorded'in (ROOT/'DATA_LICENSE.md').read_text():pending.append('Study-generated data licence choice is not recorded')
 if fail:raise SystemExit('Release validation failed:\n- '+'\n- '.join(fail))
 print(f'Unified release validation PASS: {len(allfiles)} files;490profiles;3570core tagged records;64917survey trait rows;all9current figures/all15numbered tables (16CSV files).')
 if pending:
  print('Publication metadata still to resolve:\n- '+'\n- '.join(pending))
  if a.strict_publication:raise SystemExit(2)
if __name__=='__main__':main()
