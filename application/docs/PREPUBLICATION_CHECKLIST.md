# Publication metadata checklist

The unified local package contains the available research files and records its remaining historical-source limits in REPRODUCTION_LIMITS.md. Before a public release, supply the actual repository URL/archive identifier and record the authors' licence choice for study-generated data. CITATION.cff mirrors the supplied manuscript author list, including two identically named Qi Wei entries; clarify their identities with the author record rather than guessing.

Run:

```bash
python scripts/build_integrity_files.py
python scripts/validate_release.py
python scripts/validate_release.py --strict-publication
```

The normal validation checks data counts, prompt manifests, source coverage, machine paths, syntax and integrity. Strict publication mode additionally checks the unresolved publication metadata. No public repository URL or DOI should be invented to make that mode pass.
