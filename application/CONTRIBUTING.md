# Contributing

Please open an issue describing the analysis, documentation, or reproducibility problem before
a substantial change. Keep generated outputs synchronized with their source data and scripts.
Do not commit credentials, direct survey identifiers, third-party raw data, or model-account
metadata. Run both validation scripts and re-render affected figures before a pull request.
After the final intentional change, run `python scripts/build_integrity_files.py` and then
`python scripts/validate_release.py` so the release manifests remain synchronized.
