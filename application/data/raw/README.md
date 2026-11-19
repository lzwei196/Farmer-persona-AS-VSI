# Official harmonized LSMS-ISA data

The exact four study files match the LSMS-ISA harmonised panel v2.0 archived at [DOI 10.5281/zenodo.15774761](https://doi.org/10.5281/zenodo.15774761). The fixed record's API lists open access and the CC0 1.0 license (verified 17 October 2026). Attribution: Thomas Bentze, LSMS-ISA harmonised dataset on agricultural productivity and welfare in Sub-Saharan Africa v2.0. See the source record and its accompanying paper for full citation and methods.

`source_data_manifest.json` records the official individual-file URLs, sizes and MD5 checksums, and the SHA-256 hashes of the four exact harmonized Stata files used for the study. Download from that fixed record rather than automatically following a newer release. Keep attribution and source license information with any redistributed copies.

The uncompressed files are roughly 1 GB in total, and several exceed GitHub's normal 100 MB file limit. They are therefore fetched from the official archive rather than duplicated in this repository. This is a size and provenance choice; the harmonized archive is not described here as restricted data. Compact deidentified analysis inputs and population aggregates in `../processed/` support offline reproduction of the included manuscript analyses.

The underlying country survey records can also be obtained through the World Bank Microdata Library. The [official World Bank reproducibility record](https://reproducibility.worldbank.org/catalog/269) lists the survey sources and instructions for rebuilding the harmonized datasets. Those individual survey terms should be reviewed separately when acquiring or redistributing the original country files.

A previous package README linked to DOI 10.5281/zenodo.14016696 (v1.1). The 17 October 2026 file audit found that those older archive members differ from the study files. All four study files instead match v2.0 byte checksums exactly. This repository corrects the acquisition route; it does not replace the study data with a different version.

## Obtain the original official source

```bash
python scripts/fetch_source_data.py --list
python scripts/fetch_source_data.py --files Plot_dataset.dta
python scripts/fetch_source_data.py --verify-only --output-dir /path/to/lsms --files Plot_dataset.dta
```

The fixed v2.0 DOI is10.5281/zenodo.15774761. Downloaded files are checked against official MD5 values and the exact study SHA256 records. The default download directory is ignored by Git. This step is optional for the included compact-data analysis workflow.
