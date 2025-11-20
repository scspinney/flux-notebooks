<!--
Sync Impact Report:
Version: 0.1.0 → 1.0.0 (initial constitution for BIDS-Flux Dashboard)
Added sections: All core principles defined for BIDS dashboard application
Templates requiring updates: ⚠ pending validation of .specify/templates/*.md
-->

# BIDS-Flux Dashboard Constitution

## Core Principles

### I. Reproducibility First (NON-NEGOTIABLE)
Every artifact (notebooks, summaries, CSVs) MUST be reproducible from the repository plus documented dataset pointers (DataLad/Git/URLs). Store generation commands and versions of dependencies used to create outputs. All processing workflows must include provenance metadata that allows exact reproduction of results from source data.

### II. Data Privacy and Safety (NON-NEGOTIABLE)
Do not commit any PHI or raw datasets to version control. Use small synthetic or example fixtures for tests and examples. Enforce comprehensive .gitignore rules and use Git LFS or DataLad for large/real datasets. All data handling must comply with institutional data governance policies.

### III. BIDS Compatibility and Provenance
Treat BIDS datasets as the ground-truth schema; validate with pybids or bids-validator in CI when possible. When producing derived artifacts, record complete provenance including tool version, command parameters, and dataset version. All neuroimaging data processing must follow BIDS derivative specifications.

### IV. Minimal and Explicit External Effects
CLI commands and library APIs MUST avoid side effects by default (provide dry-run mode or require explicit output specifications). Environment-dependent settings come from validated configuration (e.g., Settings.from_env()); CI and documentation must clearly show all required environment variables.

### V. Open Governance and Contributor-Friendly
Use permissive licensing (MIT). Provide comprehensive CONTRIBUTING.md, CODE_OF_CONDUCT.md, and clear issue/PR templates. All development processes must be documented and accessible to new contributors. Foster inclusive collaboration across neuroimaging research community.

### VI. Stability and Semantic Versioning
Semantic versioning for public APIs and CLI interfaces. Patch releases for bugfixes only, minor releases for new features, major releases for compatibility changes. Dashboard interfaces and data schemas require special consideration for backward compatibility to preserve existing research workflows.

## Data Handling Requirements

All BIDS data processing must maintain strict separation between raw data (never committed), quality control derivatives (MRIQC), preprocessing derivatives (fMRIPrep), and metadata (RedCap integration). Each data type requires appropriate validation, error handling, and user feedback mechanisms. Dashboard must gracefully handle missing or malformed datasets.

## Development Standards

Code quality enforced through pre-commit hooks (black, ruff, mypy). Comprehensive testing strategy with unit tests for pure functions and integration tests for BIDS dataset processing. Environment configuration through Pydantic models with clear validation. Type annotations required for all public interfaces. Documentation must include reproducible examples with synthetic datasets.

## Governance

This constitution supersedes all other development practices. Amendments require documented rationale, community review, and migration plan for existing code. All pull requests must demonstrate compliance with core principles. Development complexity must be justified against reproducibility and maintainability benefits.

**Version**: 1.0.0 | **Ratified**: 2025-11-20 | **Last Amended**: 2025-11-20
