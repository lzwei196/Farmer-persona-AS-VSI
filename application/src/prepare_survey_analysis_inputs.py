"""Create compact deidentified inputs from the exact harmonized Plot file.

The official v2.0 file and checksums are in data/raw/source_data_manifest.json.
This preparation does not query models or change the frozen experimental profiles.
Use --plot-data /authorized/path/Plot_dataset.dta; outputs default to data/processed.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

WAVES = {'Ethiopia': 3, 'Malawi': 4, 'Mali': 2, 'Niger': 1,
         'Nigeria': 4, 'Tanzania': 3, 'Uganda': 8}
ORIGINAL = {'Ethiopia', 'Malawi', 'Nigeria', 'Tanzania'}
STRATA = ['fert_user', 'female_manager', 'formal_education_manager']


def blank(x):
    return x.isna() | x.astype(str).str.strip().isin(['', 'nan'])


def prepare(plot_data: Path, output: Path):
    cols = ['country', 'wave', 'pw', 'ea_id_merge', 'hh_id_merge',
            'plot_area_GPS', 'farm_size', 'age_manager', 'female_manager',
            'formal_education_manager', 'plot_owned', 'intercropped',
            'main_crop', 'nitrogen_kg', 'inorganic_fertilizer']
    r = pd.read_stata(plot_data, columns=cols, convert_categoricals=True)
    r['country'] = r.country.astype(str)
    r = r[r.country.map(WAVES).eq(r.wave) & r.plot_area_GPS.between(.05, 20)].copy()
    for col in ['female_manager', 'formal_education_manager', 'plot_owned',
                'inorganic_fertilizer', 'intercropped']:
        if not pd.api.types.is_numeric_dtype(r[col]):
            r[col] = r[col].astype(str).map({'Yes': 1., 'No': 0.})
    r['rate'] = r.nitrogen_kg / r.plot_area_GPS
    r['rate_excl'] = r.rate.where(r.rate.le(300))
    r['rate_cap'] = r.rate.clip(upper=300)
    r['adoption_indicator_missing'] = r.inorganic_fertilizer.isna().astype(int)
    r['adoption'] = r.inorganic_fertilizer.fillna(0)
    r.loc[r.country.eq('Ethiopia'), 'adoption'] = (
        r.inorganic_fertilizer.eq(1) & r.nitrogen_kg.gt(0)).astype(float)
    x = pd.DataFrame({
        'age10': r.age_manager / 10, 'female': r.female_manager,
        'education': r.formal_education_manager, 'log2plot': np.log2(r.plot_area_GPS),
        'log2farm': np.log2(r.farm_size), 'owned': r.plot_owned,
        'intercropped': r.intercropped,
        'maize': r.main_crop.astype(str).eq('MAIZE').astype(float)
    }, index=r.index).replace([np.inf, -np.inf], np.nan)
    ok = x.notna().all(axis=1) & r.pw.notna() & np.isfinite(r.pw) & r.pw.gt(0)
    t = r.loc[ok].copy()
    # Retain source record order; new indices never expose original row IDs.
    t['row_id'] = np.arange(len(t))
    for col, prefix in [('ea_id_merge', 'EA'), ('hh_id_merge', 'HH')]:
        b = blank(t[col])
        levels = sorted(t.loc[~b, col].astype(str).unique())
        mapping = {v: f'{prefix}_{i:08d}' for i, v in enumerate(levels)}
        # Ordered codes preserve GroupKFold's lexicographic group order.
        t[col] = t[col].astype(str).map(mapping).where(~b, '')
    t['main_crop'] = np.where(t.main_crop.astype(str).eq('MAIZE'), 'MAIZE', 'OTHER')
    keep = ['row_id', 'country', 'pw', 'ea_id_merge', 'hh_id_merge', 'age_manager',
            'female_manager', 'formal_education_manager', 'plot_area_GPS', 'farm_size',
            'plot_owned', 'intercropped', 'main_crop', 'adoption', 'rate_excl', 'rate_cap',
            'adoption_indicator_missing']
    assert len(t) == 64917 and t.adoption_indicator_missing.sum() == 398
    output.mkdir(parents=True, exist_ok=True)
    t[keep].to_csv(output / 'trait_survey_analysis_input.csv.gz', index=False,
                  compression={'method': 'gzip', 'mtime': 0})
    cells, primary, sensitivity = [], [], []
    for country, wave in WAVES.items():
        eligible = r[r.country.eq(country) & r.female_manager.notna()
                     & r.formal_education_manager.notna() & r.age_manager.notna()
                     & r.main_crop.notna() & r.nitrogen_kg.notna()
                     & r.pw.notna() & np.isfinite(r.pw) & r.pw.gt(0)].copy()
        def targets(p):
            return {
                'country': country, 'wave': wave, 'eligible_plots': len(p),
                'eligible_weight_total': float(p.pw.sum()),
                'survey_weighted_mean_capped_n_kg_per_ha': float(np.average(p.rate_cap, weights=p.pw)),
                'survey_weighted_mean_capped_n_kg_per_plot': float(np.average(p.rate_cap * p.plot_area_GPS, weights=p.pw)),
            }
        sensitivity.append({**targets(eligible), 'pool_definition':
                            'area 0.05-20 ha; observed N and sampling covariates; positive finite pw; all rates above 300 retained and clipped at 300'})
        if country not in ORIGINAL:
            eligible = eligible[eligible.rate_excl.notna()].copy()
        eligible['fert_user'] = eligible.adoption.astype(int)
        for key, g in eligible.groupby(STRATA, dropna=False):
            cells.append({'country': country, **dict(zip(STRATA, map(int, key))),
                          'population_cell_n': len(g),
                          'population_cell_weight_total': float(g.pw.sum())})
        primary.append(targets(eligible))
    assert len(cells) == 55
    pd.DataFrame(cells).to_csv(output / 'paper2_population_poststrata.csv', index=False)
    pd.DataFrame(primary).to_csv(output / 'paper2_country_wave_capped_rate_targets.csv', index=False)
    pd.DataFrame(sensitivity).sort_values('country').to_csv(
        output / 'paper2_country_wave_capped_sensitivity_targets.csv', index=False)
    h = hashlib.sha256()
    with plot_data.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    (output / 'survey_preparation_provenance.json').write_text(json.dumps({
        'source_file': plot_data.name, 'source_sha256': h.hexdigest(),
        'source_doi': '10.5281/zenodo.15774761', 'version': 'v2.0', 'license': 'CC0',
        'trait_records': len(t), 'adoption_indicator_missing': int(t.adoption_indicator_missing.sum()),
        'population_poststrata': len(cells),
        'note': 'Primary extension weighting excludes high-rate rows; capped sensitivity retains and clips them. Anonymous groups retain order, not original identifiers.'
    }, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plot-data', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path,
                        default=Path(__file__).resolve().parents[1] / 'data' / 'processed')
    args = parser.parse_args()
    prepare(args.plot_data, args.output_dir)
