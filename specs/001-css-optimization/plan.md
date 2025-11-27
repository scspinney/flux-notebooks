# Implementation Plan: CSS Split and Page Refactoring

**Branch**: `001-css-optimization` | **Date**: November 27, 2025 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-css-optimization/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

This is a code reorganization refactoring to improve dashboard performance and maintainability without changing functionality. The plan splits a large global CSS file (assets/custom.css, 313 lines) into page-specific CSS files and moves helper functions from pages/*.py modules into src/flux_notebooks/ for better separation of concerns. The implementation uses static analysis at app startup with naming conventions (page_name.py → page_name.css) to load only required CSS per page. All changes are purely structural - no new features, no dependency additions, and zero behavioral modifications. Each phase commits progress to enable easy rollback.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: Dash, dash-bootstrap-components, Flask (via Dash), pybids, pandas, plotly  
**Storage**: File-based (BIDS datasets, MRIQC/fMRIPrep derivatives, RedCap CSVs)  
**Testing**: pytest (existing test suite in tests/)  
**Target Platform**: Linux/macOS server (web application)  
**Project Type**: Web application (Dash multi-page app with Flask backend)  
**Performance Goals**: 30% reduction in page load time, 50% reduction in CSS loaded per page  
**Constraints**: No new dependencies, no functional changes, all existing tests must pass, progressive rollback capability  
**Scale/Scope**: 10 page modules (pages/*.py), 1 large CSS file (313 lines), ~40-50 helper functions to relocate

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Reproducibility First ✅ PASS
- **Assessment**: This refactoring does not affect artifact generation or data processing
- **Compliance**: Code reorganization maintains all existing provenance tracking and reproducibility features

### II. Data Privacy and Safety ✅ PASS
- **Assessment**: No data handling changes; purely code structure refactoring
- **Compliance**: Existing .gitignore rules remain unchanged, no new data paths introduced

### III. BIDS Compatibility and Provenance ✅ PASS
- **Assessment**: No changes to BIDS validation or derivative generation logic
- **Compliance**: All BIDS processing code remains in src/flux_notebooks/ with identical functionality

### IV. Minimal and Explicit External Effects ✅ PASS
- **Assessment**: Refactoring reduces code complexity and side effects by separating concerns
- **Compliance**: FR-007 explicitly prohibits new dependencies; FR-008 requires identical behavior

### V. Open Governance and Contributor-Friendly ✅ PASS
- **Assessment**: Improved code organization makes codebase more accessible to contributors
- **Compliance**: Cleaner separation between UI (pages/) and logic (src/) improves maintainability

### VI. Stability and Semantic Versioning ✅ PASS
- **Assessment**: Zero API or CLI interface changes; this is internal refactoring only
- **Compliance**: FR-010 requires all existing tests pass without modification; version remains 0.1.0

**GATE RESULT**: ✅ ALL PASSED - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
flux-notebooks/
├── app.py                          # Main Dash application entrypoint
├── pages/                          # Dash page modules (TO BE REFACTORED)
│   ├── assistant_sandbox.py       # LLM chat interface
│   ├── bids.py                     # BIDS browser
│   ├── fmriprep_detail.py          # fMRIPrep subject detail
│   ├── fmriprep_index.py           # fMRIPrep index/listing
│   ├── freesurfer.py               # FreeSurfer QC
│   ├── home.py                     # Dashboard home
│   ├── mriqc.py                    # MRIQC index/listing
│   ├── mriqc_detail.py             # MRIQC subject detail
│   ├── redcap.py                   # RedCap enrollment
│   └── subject_detail.py           # Subject overview
├── assets/                         # Static assets (TO BE REORGANIZED)
│   ├── custom.css                  # Global CSS (TO BE SPLIT)
│   ├── flux_inputs.css             # Input styles
│   ├── assistant_sandbox.js        # Client-side JS
│   └── icons/                      # Icon assets
├── src/flux_notebooks/             # Business logic (DESTINATION FOR HELPERS)
│   ├── bids/                       # BIDS utilities
│   ├── callbacks/                  # Dash callbacks
│   ├── components/                 # Reusable components
│   ├── freesurfer/                 # FreeSurfer processing
│   ├── lib/                        # Core libraries
│   ├── redcap/                     # RedCap integration
│   ├── utils/                      # Utilities
│   └── pages/                      # NEW: Page helper modules
│       ├── assistant_helpers.py    # Assistant page helpers
│       ├── bids_helpers.py         # BIDS page helpers
│       ├── fmriprep_helpers.py     # fMRIPrep helpers
│       ├── home_helpers.py         # Home page helpers
│       ├── mriqc_helpers.py        # MRIQC helpers
│       ├── redcap_helpers.py       # RedCap helpers
│       ├── subject_helpers.py      # Subject detail helpers
│       └── common_helpers.py       # Shared helpers
└── tests/                          # Test suite (NO CHANGES)
    └── test_summarize.py
```

**Structure Decision**: Web application structure maintained. This refactoring adds `src/flux_notebooks/pages/` to hold relocated helper functions from `pages/*.py`, keeping the existing Dash multi-page architecture. CSS files will be split into page-specific files in `assets/` directory alongside the new `assets/common.css`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**Status**: No violations - all constitution checks passed. No complexity tracking required.

---

## Phase Completion Status

### Phase 0: Outline & Research ✅ COMPLETE

**Output**: `research.md`

**Key Decisions Documented**:
1. CSS loading via static analysis at app startup with naming convention
2. CSS namespacing using page-specific prefixes
3. Helper organization in per-page modules + common_helpers.py
4. Progressive rollback via git commits per page + feature flag
5. Manual CSS analysis with grep-based tooling
6. Zero regression testing via existing tests + manual verification

**Status**: All technical unknowns resolved. No further research required.

---

### Phase 1: Design & Contracts ✅ COMPLETE

**Outputs**:
- `data-model.md` - Entity definitions and relationships for refactoring artifacts
- `quickstart.md` - Developer guide for working with split CSS and helper modules
- `CLAUDE.md` - Updated agent context with technology stack

**Key Artifacts**:
1. **Entities Defined**: Page Module, CSS Stylesheet, Helper Function, Helper Module, CSS Loader
2. **Relationships Mapped**: Clear ownership and dependency structure
3. **Validation Rules**: Comprehensive checks for each entity
4. **Developer Guide**: Complete documentation for maintaining refactored code

**Status**: Design complete. Ready for task breakdown.

---

### Phase 2: Task Breakdown ⏳ PENDING

**Next Command**: `/speckit.tasks`

**Expected Output**: `tasks.md` with detailed implementation tasks

**Approach**:
- Break refactoring into per-page tasks (one commit per page)
- Prioritize by page complexity and dependency order
- Include validation checklist for each task
- Ensure progressive rollback capability

---

## Implementation Strategy

### Commit Strategy

Each page refactoring gets its own commit for granular rollback:

```
git log --oneline (expected sequence):
- feat: refactor assistant_sandbox page (css + helpers)
- feat: refactor mriqc page (css + helpers)
- feat: refactor redcap page (css + helpers)
- feat: refactor home page (css + helpers)
- feat: refactor bids page (css + helpers)
- feat: refactor fmriprep pages (css + helpers)
- feat: refactor freesurfer page (css + helpers)
- feat: refactor subject_detail page (css + helpers)
- chore: remove custom.css backup after verification
```

### Validation Per Commit

After each page refactoring commit:
1. Run `pytest tests/` - all tests must pass
2. Start app, navigate to refactored page
3. Verify CSS loaded correctly (DevTools Network tab)
4. Verify no console errors
5. Test all interactive elements on page
6. Update `data-model.md` change tracking table
7. Commit changes with descriptive message

### Rollback Options

- **Per-page rollback**: `git revert <commit-sha>` for specific page
- **Feature flag toggle**: Set `FLUX_USE_SPLIT_CSS=false` in environment
- **Full rollback**: `git checkout main` to abandon entire refactoring

---

## Success Metrics Tracking

### Performance Goals (from Success Criteria)

| Metric | Target | Measurement Method | Status |
|--------|--------|-------------------|--------|
| SC-001: Page load time reduction | ≥30% | Chrome DevTools Network tab | Pending |
| SC-002: CSS size reduction | ≥50% | Compare file sizes | Pending |
| SC-003: LOC reduction in pages/ | ≥40% | Count lines via `wc -l` | Pending |
| SC-004: Tests pass | 100% | `pytest tests/` | Baseline ✓ |
| SC-005: Zero regressions | 100% | Manual verification | Pending |
| SC-006: Only relevant CSS loaded | 100% | DevTools inspection | Pending |

### Baseline Measurements (Before Refactoring)

```bash
# CSS size
wc -l assets/custom.css
# Output: 313 lines

# Page module sizes (sample)
wc -l pages/assistant_sandbox.py  # ~550 lines
wc -l pages/mriqc.py               # ~330 lines
wc -l pages/redcap.py              # ~430 lines
wc -l pages/home.py                # ~500 lines

# Total helper functions to move: ~40-50 (estimated from grep analysis)
```

### Target Measurements (After Refactoring)

```bash
# CSS: common.css + page-specific should be <157 lines per page (50% of 313)
# Page modules: 40% reduction means ~60% remain
# assistant_sandbox.py: 550 → ~330 lines
# mriqc.py: 330 → ~200 lines
# redcap.py: 430 → ~260 lines
# home.py: 500 → ~300 lines
```

---

## Next Steps

**Command**: `/speckit.tasks`

**Purpose**: Generate detailed task breakdown for implementation

**Expected Outcome**:
- `tasks.md` with sequenced implementation tasks
- Each task includes validation checklist
- Tasks ordered by dependency and complexity
- Clear acceptance criteria per task

**Ready to Proceed**: ✅ All prerequisites met
- Constitution check passed
- Research complete
- Design documented
- Agent context updated
- No blocking issues
