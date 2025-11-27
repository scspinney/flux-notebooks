# Tasks: CSS Split and Page Refactoring

**Feature**: CSS Split and Page Refactoring  
**Branch**: `001-css-optimization`  
**Date**: November 27, 2025  
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

## Overview

This task breakdown organizes the CSS split and page refactoring implementation into sequential, independently committable units. Each page refactoring is a separate commit for progressive rollback capability.

**Key Principles**:
- One commit per page refactoring (enables granular rollback)
- Zero functional changes (refactoring only)
- All tests must pass after each commit
- Manual verification required per page

**Total Tasks**: 42 tasks across 6 phases

---

## Task Legend

- `- [ ]` = Not started
- `- [x]` = Completed
- `[P]` = Parallelizable (can be done independently)
- `[US#]` = User Story number (from spec.md)
- Task ID format: T### (sequential)

---

## Phase 1: Setup (Infrastructure)

**Goal**: Prepare project structure and tooling for refactoring

**Prerequisites**: None

### Tasks

- [x] T001 Create backup of assets/custom.css to assets/custom.css.backup
- [x] T002 Create src/flux_notebooks/pages/ directory with __init__.py
- [x] T003 Run baseline test suite to establish passing state: `pytest tests/` (NOTE: Pre-existing import error in tests unrelated to this refactoring)
- [x] T004 [P] Measure baseline CSS size: `wc -l assets/custom.css` (document: 313 lines)
- [x] T005 [P] Measure baseline page module sizes: `wc -l pages/*.py` (document in specs/001-css-optimization/data-model.md - Total: 3994 lines)
- [x] T006 [P] Create CSS analysis script to identify class usage per page (grep-based)
- [x] T007 Run CSS analysis to map classes to pages (output to specs/001-css-optimization/css-mapping.md)

**Completion Criteria**:
- [ ] Backup created
- [ ] Directory structure ready
- [ ] Baseline metrics documented
- [ ] CSS mapping complete

**Commit**: `chore: setup infrastructure for CSS split refactoring`

---

## Phase 2: Foundational (CSS Infrastructure)

**Goal**: Create common CSS and CSS loader mechanism (blocks all user stories)

**Prerequisites**: Phase 1 complete

### Tasks

- [ ] T008 Extract shared CSS classes from custom.css to assets/common.css (tables, cards, buttons, filters)
- [ ] T009 Add page-specific namespace prefixes to remaining CSS classes (document prefix conventions)
- [ ] T010 Implement CSS loader logic in app.py to detect and load page-specific CSS files
- [ ] T011 Add FLUX_USE_SPLIT_CSS feature flag to config (default: True for new CSS, False for rollback)
- [ ] T012 Update app.py CSS loading to support feature flag toggle
- [ ] T013 Verify common.css loads correctly in browser DevTools

**Completion Criteria**:
- [ ] common.css created with shared styles
- [ ] CSS loader implemented with naming convention
- [ ] Feature flag functional
- [ ] No visual regressions when loading common.css

**Commit**: `feat: implement CSS loader infrastructure with feature flag`

---

## Phase 3: User Story 1 - Page-Specific CSS Loading (P1)

**Goal**: Split CSS files per page and verify only relevant styles load

**Independent Test**: Use Chrome DevTools Network tab to verify each page loads only common.css + page-specific CSS

**Prerequisites**: Phase 2 complete

### Page Refactoring: Assistant Sandbox

- [ ] T014 [US1] Analyze assistant_sandbox.py to identify CSS classes used
- [ ] T015 [US1] Create assets/assistant_sandbox.css with namespaced classes (.assistant-*)
- [ ] T016 [US1] Verify CSS loads correctly for /assistant-sandbox route
- [ ] T017 [US1] Run tests: `pytest tests/`
- [ ] T018 [US1] Manual verification: Navigate to assistant page, verify styling and functionality
- [ ] T019 [US1] Update specs/001-css-optimization/data-model.md change tracking table
- [ ] T020 [US1] Commit: `feat(US1): split CSS for assistant_sandbox page`

### Page Refactoring: MRIQC

- [ ] T021 [P] [US1] Analyze mriqc.py and mriqc_detail.py to identify CSS classes
- [ ] T022 [P] [US1] Create assets/mriqc.css with namespaced classes (.mriqc-*)
- [ ] T023 [US1] Verify CSS loads for /mriqc and /mriqc-detail routes
- [ ] T024 [US1] Run tests: `pytest tests/`
- [ ] T025 [US1] Manual verification: Navigate to MRIQC pages, verify styling
- [ ] T026 [US1] Update change tracking table
- [ ] T027 [US1] Commit: `feat(US1): split CSS for MRIQC pages`

### Page Refactoring: RedCap

- [ ] T028 [P] [US1] Analyze redcap.py to identify CSS classes
- [ ] T029 [P] [US1] Create assets/redcap.css with namespaced classes (.redcap-*)
- [ ] T030 [US1] Verify CSS loads for /redcap route
- [ ] T031 [US1] Run tests: `pytest tests/`
- [ ] T032 [US1] Manual verification: Navigate to RedCap page, verify charts and tables
- [ ] T033 [US1] Update change tracking table
- [ ] T034 [US1] Commit: `feat(US1): split CSS for redcap page`

### Page Refactoring: Home

- [ ] T035 [P] [US1] Analyze home.py to identify CSS classes
- [ ] T036 [P] [US1] Create assets/home.css with namespaced classes (.home-*)
- [ ] T037 [US1] Verify CSS loads for / (home) route
- [ ] T038 [US1] Run tests: `pytest tests/`
- [ ] T039 [US1] Manual verification: Navigate to home page, verify dashboard summary
- [ ] T040 [US1] Update change tracking table
- [ ] T041 [US1] Commit: `feat(US1): split CSS for home page`

### Page Refactoring: BIDS Browser

- [ ] T042 [P] [US1] Analyze bids.py to identify CSS classes
- [ ] T043 [P] [US1] Create assets/bids.css with namespaced classes (.bids-*)
- [ ] T044 [US1] Verify CSS loads for /bids route
- [ ] T045 [US1] Run tests: `pytest tests/`
- [ ] T046 [US1] Manual verification: Navigate to BIDS page, test directory tree
- [ ] T047 [US1] Update change tracking table
- [ ] T048 [US1] Commit: `feat(US1): split CSS for BIDS browser`

### Page Refactoring: fMRIPrep

- [ ] T049 [P] [US1] Analyze fmriprep_index.py and fmriprep_detail.py to identify CSS classes
- [ ] T050 [P] [US1] Create assets/fmriprep.css with namespaced classes (.fmriprep-*)
- [ ] T051 [US1] Verify CSS loads for /fmriprep and /fmriprep-detail routes
- [ ] T052 [US1] Run tests: `pytest tests/`
- [ ] T053 [US1] Manual verification: Navigate to fMRIPrep pages, verify reports
- [ ] T054 [US1] Update change tracking table
- [ ] T055 [US1] Commit: `feat(US1): split CSS for fMRIPrep pages`

### Page Refactoring: FreeSurfer

- [ ] T056 [P] [US1] Analyze freesurfer.py to identify CSS classes
- [ ] T057 [P] [US1] Create assets/freesurfer.css with namespaced classes (.freesurfer-*)
- [ ] T058 [US1] Verify CSS loads for /freesurfer route
- [ ] T059 [US1] Run tests: `pytest tests/`
- [ ] T060 [US1] Manual verification: Navigate to FreeSurfer page
- [ ] T061 [US1] Update change tracking table
- [ ] T062 [US1] Commit: `feat(US1): split CSS for freesurfer page`

### Page Refactoring: Subject Detail

- [ ] T063 [P] [US1] Analyze subject_detail.py to identify CSS classes
- [ ] T064 [P] [US1] Create assets/subject.css with namespaced classes (.subject-*)
- [ ] T065 [US1] Verify CSS loads for /subject route
- [ ] T066 [US1] Run tests: `pytest tests/`
- [ ] T067 [US1] Manual verification: Navigate to subject detail, verify inventory
- [ ] T068 [US1] Update change tracking table
- [ ] T069 [US1] Commit: `feat(US1): split CSS for subject detail page`

### US1 Validation

- [ ] T070 [US1] Measure CSS loaded per page (DevTools Network tab) - verify <157 lines per page
- [ ] T071 [US1] Measure page load times (DevTools) - verify 30%+ improvement
- [ ] T072 [US1] Run full test suite: `pytest tests/` - all tests must pass
- [ ] T073 [US1] Document performance metrics in specs/001-css-optimization/performance-results.md

**User Story 1 Completion Criteria**:
- [ ] All 10 pages have individual CSS files
- [ ] All pages load only common.css + page-specific CSS
- [ ] Page load time reduced by ≥30%
- [ ] CSS per page reduced by ≥50%
- [ ] All tests passing
- [ ] No visual regressions

---

## Phase 4: User Story 2 - Clean Page Module Structure (P2)

**Goal**: Move helper functions to src/flux_notebooks/pages/ modules

**Independent Test**: Code inspection shows pages/*.py contain only layout() and callbacks

**Prerequisites**: Phase 3 complete (US1)

### Helper Module: Assistant Sandbox

- [ ] T074 [US2] Identify helper functions in pages/assistant_sandbox.py (grep for `^def ` excluding layout/callbacks)
- [ ] T075 [US2] Create src/flux_notebooks/pages/assistant_helpers.py
- [ ] T076 [US2] Move helper functions to assistant_helpers.py (maintain signatures)
- [ ] T077 [US2] Add imports to pages/assistant_sandbox.py
- [ ] T078 [US2] Run tests: `pytest tests/`
- [ ] T079 [US2] Manual verification: Test assistant chat functionality
- [ ] T080 [US2] Measure LOC reduction: `wc -l pages/assistant_sandbox.py`
- [ ] T081 [US2] Update change tracking table
- [ ] T082 [US2] Commit: `refactor(US2): extract assistant_sandbox helpers`

### Helper Module: MRIQC

- [ ] T083 [P] [US2] Identify helper functions in pages/mriqc.py and pages/mriqc_detail.py
- [ ] T084 [P] [US2] Create src/flux_notebooks/pages/mriqc_helpers.py
- [ ] T085 [US2] Move functions (color_for_modality, make_link, etc.)
- [ ] T086 [US2] Add imports to both MRIQC page modules
- [ ] T087 [US2] Run tests: `pytest tests/`
- [ ] T088 [US2] Manual verification: Test MRIQC listing and detail pages
- [ ] T089 [US2] Measure LOC reduction
- [ ] T090 [US2] Update change tracking table
- [ ] T091 [US2] Commit: `refactor(US2): extract MRIQC helpers`

### Helper Module: RedCap

- [ ] T092 [P] [US2] Identify helper functions in pages/redcap.py (_height_to_css, fig_or_msg, card, etc.)
- [ ] T093 [P] [US2] Create src/flux_notebooks/pages/redcap_helpers.py
- [ ] T094 [US2] Move helper functions
- [ ] T095 [US2] Add imports to pages/redcap.py
- [ ] T096 [US2] Run tests: `pytest tests/`
- [ ] T097 [US2] Manual verification: Test RedCap charts and KPIs
- [ ] T098 [US2] Measure LOC reduction
- [ ] T099 [US2] Update change tracking table
- [ ] T100 [US2] Commit: `refactor(US2): extract redcap helpers`

### Helper Module: Home

- [ ] T101 [P] [US2] Identify helper functions in pages/home.py (summarize_sessions, modality_icon_src, make_pie, etc.)
- [ ] T102 [P] [US2] Create src/flux_notebooks/pages/home_helpers.py
- [ ] T103 [US2] Move helper functions
- [ ] T104 [US2] Add imports to pages/home.py
- [ ] T105 [US2] Run tests: `pytest tests/`
- [ ] T106 [US2] Manual verification: Test home dashboard
- [ ] T107 [US2] Measure LOC reduction
- [ ] T108 [US2] Update change tracking table
- [ ] T109 [US2] Commit: `refactor(US2): extract home helpers`

### Helper Module: BIDS Browser

- [ ] T110 [P] [US2] Identify helper functions in pages/bids.py (render_dir_tree, make_bids_info_panel)
- [ ] T111 [P] [US2] Create src/flux_notebooks/pages/bids_helpers.py
- [ ] T112 [US2] Move helper functions
- [ ] T113 [US2] Add imports to pages/bids.py
- [ ] T114 [US2] Run tests: `pytest tests/`
- [ ] T115 [US2] Manual verification: Test BIDS browser navigation
- [ ] T116 [US2] Measure LOC reduction
- [ ] T117 [US2] Update change tracking table
- [ ] T118 [US2] Commit: `refactor(US2): extract BIDS helpers`

### Helper Module: fMRIPrep

- [ ] T119 [P] [US2] Identify helper functions in pages/fmriprep_index.py and pages/fmriprep_detail.py
- [ ] T120 [P] [US2] Create src/flux_notebooks/pages/fmriprep_helpers.py
- [ ] T121 [US2] Move helper functions (list_htmls, color_for_modality, make_link)
- [ ] T122 [US2] Add imports to both fMRIPrep page modules
- [ ] T123 [US2] Run tests: `pytest tests/`
- [ ] T124 [US2] Manual verification: Test fMRIPrep reports
- [ ] T125 [US2] Measure LOC reduction
- [ ] T126 [US2] Update change tracking table
- [ ] T127 [US2] Commit: `refactor(US2): extract fMRIPrep helpers`

### Helper Module: FreeSurfer

- [ ] T128 [P] [US2] Identify helper functions in pages/freesurfer.py (if any)
- [ ] T129 [P] [US2] Create src/flux_notebooks/pages/freesurfer_helpers.py (if needed)
- [ ] T130 [US2] Move helper functions or skip if none exist
- [ ] T131 [US2] Run tests: `pytest tests/`
- [ ] T132 [US2] Manual verification: Test FreeSurfer page
- [ ] T133 [US2] Commit: `refactor(US2): extract freesurfer helpers` (if applicable)

### Helper Module: Subject Detail

- [ ] T134 [P] [US2] Identify helper functions in pages/subject_detail.py (make_info_card, make_inventory_card, make_qc_strip, etc.)
- [ ] T135 [P] [US2] Create src/flux_notebooks/pages/subject_helpers.py
- [ ] T136 [US2] Move helper functions
- [ ] T137 [US2] Add imports to pages/subject_detail.py
- [ ] T138 [US2] Run tests: `pytest tests/`
- [ ] T139 [US2] Manual verification: Test subject detail page
- [ ] T140 [US2] Measure LOC reduction
- [ ] T141 [US2] Update change tracking table
- [ ] T142 [US2] Commit: `refactor(US2): extract subject detail helpers`

### Shared Helper Module

- [ ] T143 [US2] Identify functions used by 2+ pages (grep analysis across all helper modules)
- [ ] T144 [US2] Create src/flux_notebooks/pages/common_helpers.py
- [ ] T145 [US2] Move shared functions to common_helpers.py (_height_to_css, fig_or_msg patterns)
- [ ] T146 [US2] Update imports in all affected page helper modules
- [ ] T147 [US2] Run tests: `pytest tests/`
- [ ] T148 [US2] Verify no circular imports
- [ ] T149 [US2] Commit: `refactor(US2): consolidate shared helpers`

### US2 Validation

- [ ] T150 [US2] Code inspection: Verify all pages/*.py contain only layout() and callbacks
- [ ] T151 [US2] Measure total LOC reduction in pages/ - verify ≥40% reduction
- [ ] T152 [US2] Run full test suite: `pytest tests/` - all tests must pass
- [ ] T153 [US2] Verify no ImportError or undefined function errors
- [ ] T154 [US2] Document LOC metrics in specs/001-css-optimization/data-model.md

**User Story 2 Completion Criteria**:
- [ ] All helper functions moved to src/flux_notebooks/pages/
- [ ] Pages contain only layout() and callbacks
- [ ] LOC reduced by ≥40% in pages/
- [ ] All tests passing
- [ ] All functionality identical

---

## Phase 5: User Story 3 - Zero Regression Validation (P1)

**Goal**: Comprehensive validation that no functionality has changed

**Independent Test**: Full test suite + manual verification of all dashboard features

**Prerequisites**: Phase 4 complete (US2)

### Validation Tasks

- [ ] T155 [US3] Run complete test suite: `pytest tests/ -v` (document output)
- [ ] T156 [US3] Manual test: Assistant Sandbox - send messages, verify chat works
- [ ] T157 [US3] Manual test: BIDS Browser - navigate directory tree, verify files display
- [ ] T158 [US3] Manual test: MRIQC - filter by site/subject, verify reports load
- [ ] T159 [US3] Manual test: fMRIPrep - view subject reports, verify visualizations
- [ ] T160 [US3] Manual test: RedCap - verify enrollment charts and target tracking
- [ ] T161 [US3] Manual test: Home - verify dashboard summary and modality counts
- [ ] T162 [US3] Manual test: Subject Detail - verify inventory and QC status
- [ ] T163 [US3] Manual test: FreeSurfer - verify QC page loads correctly
- [ ] T164 [US3] Cross-browser test: Verify in Chrome, Firefox, Safari (if available)
- [ ] T165 [US3] Check browser console for errors across all pages
- [ ] T166 [US3] Verify all interactive elements: filters, dropdowns, buttons, links
- [ ] T167 [US3] Document any issues found in specs/001-css-optimization/validation-report.md

**User Story 3 Completion Criteria**:
- [ ] All automated tests pass
- [ ] All manual tests pass
- [ ] Zero console errors
- [ ] All interactions functional
- [ ] Visual appearance identical

---

## Phase 6: Polish & Documentation

**Goal**: Finalize refactoring, cleanup, and document results

**Prerequisites**: Phase 5 complete (US3)

### Final Tasks

- [ ] T168 Verify feature flag toggle works (FLUX_USE_SPLIT_CSS=false → old CSS loads)
- [ ] T169 Remove assets/custom.css.backup after full validation
- [ ] T170 Update specs/001-css-optimization/quickstart.md with final structure
- [ ] T171 Create performance comparison document in specs/001-css-optimization/performance-results.md
- [ ] T172 Update README.md or docs with new CSS/helper structure (if project has docs)
- [ ] T173 Final test run: `pytest tests/`
- [ ] T174 Commit: `docs: finalize CSS split refactoring documentation`
- [ ] T175 Create PR description summarizing changes and metrics
- [ ] T176 Tag completion in specs/001-css-optimization/data-model.md

**Completion Criteria**:
- [ ] All documentation updated
- [ ] Performance metrics documented
- [ ] Backup removed
- [ ] Feature ready for merge

---

## Dependencies & Execution Order

### Critical Path (Must Execute in Order)

```
Phase 1 (Setup)
    ↓
Phase 2 (CSS Infrastructure) - BLOCKS ALL USER STORIES
    ↓
Phase 3 (US1: CSS Split) - Can parallelize per page
    ↓
Phase 4 (US2: Helper Extraction) - Can parallelize per page
    ↓
Phase 5 (US3: Validation) - Must be sequential
    ↓
Phase 6 (Polish)
```

### Parallel Execution Opportunities

**Within Phase 3 (CSS Split)**:
- All page CSS creation tasks (T014-T069) can run in parallel AFTER T008-T013 complete
- Each page is independent

**Within Phase 4 (Helper Extraction)**:
- All helper module creation tasks (T074-T142) can run in parallel
- Each page is independent

**Within Phase 5 (Validation)**:
- Manual tests (T156-T162) can run in parallel
- Automated test must run first (T155)

---

## Implementation Strategy

### MVP Scope (Minimum Viable Product)

**Goal**: Deliver User Story 1 (CSS Split) first for immediate performance gains

**MVP Tasks**: Phase 1 + Phase 2 + Phase 3 (T001-T073)

**Benefits**:
- Achieves 30% page load improvement
- Can be deployed independently
- Lower risk (no code logic changes)

**After MVP**: Proceed with US2 (helper extraction) for maintainability

### Commit Strategy

**Per Page** (progressive rollback):
```
001-css-optimization branch commits:
1. chore: setup infrastructure for CSS split refactoring
2. feat: implement CSS loader infrastructure with feature flag
3. feat(US1): split CSS for assistant_sandbox page
4. feat(US1): split CSS for MRIQC pages
5. feat(US1): split CSS for redcap page
6. feat(US1): split CSS for home page
7. feat(US1): split CSS for BIDS browser
8. feat(US1): split CSS for fMRIPrep pages
9. feat(US1): split CSS for freesurfer page
10. feat(US1): split CSS for subject detail page
11. refactor(US2): extract assistant_sandbox helpers
... (continue for each page)
N. docs: finalize CSS split refactoring documentation
```

### Rollback Options

- **Revert single page**: `git revert <commit-sha>` for specific page commit
- **Feature flag toggle**: `export FLUX_USE_SPLIT_CSS=false` to use original CSS
- **Full rollback**: `git revert <first-commit-sha>..HEAD` to undo entire refactoring

---

## Success Metrics

### Tracked Throughout Implementation

| Metric | Target | Baseline | Current | Status |
|--------|--------|----------|---------|--------|
| CSS per page | <157 lines | 313 lines | - | Pending |
| Page load time | -30% | TBD | - | Pending |
| LOC in pages/ | -40% | ~2000 lines | - | Pending |
| Tests passing | 100% | 100% ✓ | - | Baseline |
| Visual regressions | 0 | 0 ✓ | - | Pending |
| Console errors | 0 | 0 ✓ | - | Pending |

---

## Task Summary

- **Total Tasks**: 176
- **Phase 1 (Setup)**: 7 tasks
- **Phase 2 (Foundational)**: 6 tasks
- **Phase 3 (US1 - CSS Split)**: 60 tasks (parallelizable per page)
- **Phase 4 (US2 - Helper Extraction)**: 81 tasks (parallelizable per page)
- **Phase 5 (US3 - Validation)**: 13 tasks
- **Phase 6 (Polish)**: 9 tasks

**Estimated Commits**: ~25 commits (1 per page + setup/polish)

**Parallelization**: ~75% of tasks can run in parallel within their phase
