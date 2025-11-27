# Research: CSS Split and Page Refactoring

**Feature**: CSS Split and Page Refactoring  
**Branch**: `001-css-optimization`  
**Date**: November 27, 2025

## Overview

This document consolidates research findings for implementing a code reorganization refactoring that splits CSS files and relocates helper functions without changing functionality. All decisions prioritize minimal changes, zero behavioral modifications, and progressive rollback capability.

## Research Topics

### 1. Dash CSS Loading Mechanisms

**Decision**: Use `app.external_stylesheets` list with conditional loading based on page routes

**Rationale**:
- Dash supports multiple external stylesheets registered at app initialization
- Each page can specify its required CSS files via metadata or naming convention
- Flask routing in Dash allows inspection of current page path to determine which CSS to load
- No runtime overhead after initial registration - all CSS paths determined at startup

**Alternatives Considered**:
- **Dynamic injection via callbacks**: Rejected because it adds runtime overhead and complexity
- **CSS modules/webpack**: Rejected because it requires new build tooling (violates FR-007)
- **Inline styles**: Rejected because it defeats the purpose of CSS optimization

**Implementation Approach**:
```python
# At app startup in app.py:
# 1. Scan pages/ directory for all .py files
# 2. For each page_name.py, check if assets/page_name.css exists
# 3. Register assets/common.css globally (always loaded)
# 4. Register page-specific CSS files with Dash app.external_stylesheets
```

**References**:
- Dash documentation: https://dash.plotly.com/external-resources
- Flask routing integration: Built-in Dash capability via `@app.callback` and `dash.page_registry`

---

### 2. CSS Class Namespace Strategy

**Decision**: Use page-specific prefixes for all CSS classes (e.g., `.mriqc-`, `.redcap-`, `.assistant-`)

**Rationale**:
- Prevents naming collisions when multiple CSS files are loaded
- Makes it immediately clear which page "owns" each style
- Common components use generic names (e.g., `.flux-table`, `.flux-card`) since common.css is always loaded
- Easy to implement via find-and-replace during CSS split

**Alternatives Considered**:
- **BEM methodology**: Rejected as too complex for refactoring (would require extensive renaming)
- **CSS Modules**: Rejected because it requires build tooling
- **No prefixes**: Rejected because it risks collisions and breaks page isolation

**Implementation Approach**:
1. Analyze current CSS class usage in each page's Python layout code
2. Group styles by page (search for class names used in each pages/*.py)
3. Add page prefix to all page-specific classes
4. Keep common component classes unprefixed in common.css

---

### 3. Helper Function Organization Pattern

**Decision**: Create per-page helper modules in `src/flux_notebooks/pages/` plus `common_helpers.py`

**Rationale**:
- Each page gets its own helper module (e.g., `mriqc_helpers.py` for `pages/mriqc.py`)
- Functions used by 2+ pages go into `common_helpers.py`
- Maintains clear ownership and reduces merge conflicts
- Easy to locate functions (same name pattern as page module)
- Supports progressive rollback (can revert one page's helpers independently)

**Alternatives Considered**:
- **Single utils module**: Rejected because it creates a monolithic file and obscures ownership
- **Category-based (ui_helpers, data_helpers)**: Rejected because it splits related page logic across files
- **Extend existing modules**: Rejected because many helpers don't fit existing domain categories

**Implementation Approach**:
```python
# pages/mriqc.py - BEFORE
def color_for_modality(name: str):
    return {"T1w": "primary", "bold": "success"}.get(name, "secondary")

# src/flux_notebooks/pages/mriqc_helpers.py - AFTER
def color_for_modality(name: str):
    return {"T1w": "primary", "bold": "success"}.get(name, "secondary")

# pages/mriqc.py - AFTER IMPORT
from flux_notebooks.pages.mriqc_helpers import color_for_modality
```

---

### 4. Progressive Rollback Strategy

**Decision**: Git commits per page refactoring + feature flag pattern for CSS loading

**Rationale**:
- Each page refactored in separate commit allows granular `git revert`
- CSS split can be toggled via environment variable or config flag
- Maintains backup of original custom.css until all pages verified
- Supports A/B testing: can compare performance with/without split CSS

**Alternatives Considered**:
- **Feature branch only**: Rejected because it's all-or-nothing rollback
- **Runtime toggle via UI**: Rejected as unnecessary complexity for internal refactoring
- **No rollback plan**: Rejected because production stability is critical (FR-011)

**Implementation Approach**:
1. Create backup: `assets/custom.css.backup`
2. Add config flag: `FLUX_USE_SPLIT_CSS` (default: True)
3. Conditional CSS loading in app.py based on flag
4. Commit sequence:
   - Commit 1: Create common.css + assistant_sandbox.css, refactor assistant_sandbox.py
   - Commit 2: Create mriqc.css, refactor mriqc.py helpers
   - Commit 3: Create redcap.css, refactor redcap.py helpers
   - (Continue for each page)
   - Final commit: Remove custom.css.backup after full verification

---

### 5. CSS Analysis and Splitting Methodology

**Decision**: Manual analysis with grep-based tooling to map classes to pages

**Rationale**:
- CSS file is only 313 lines - manual review is feasible and accurate
- grep can find all uses of each CSS class in pages/*.py
- Avoids complexity of AST parsing or automated tools
- Ensures no styles are lost or misplaced
- Human review catches special cases (e.g., dynamically generated class names)

**Alternatives Considered**:
- **AST parsing tools**: Rejected as overkill for 313-line CSS file
- **CSS coverage tools (Chrome DevTools)**: Rejected because requires running each page and may miss edge cases
- **Full automation**: Rejected because dynamic class names in Python require human judgment

**Implementation Approach**:
```bash
# For each CSS class in custom.css:
# 1. Search which pages use it:
grep -r "className.*flux-assistant" pages/

# 2. Categorize:
#    - Used by 1 page → page-specific CSS
#    - Used by 2+ pages → common.css
#    - Namespaced (e.g., .flux-assistant-*) → obvious page

# 3. Create split files with mappings documented
```

---

### 6. Testing Strategy for Zero Regression

**Decision**: Existing test suite + manual page-by-page verification + CSS audit

**Rationale**:
- FR-004 requires all existing tests pass without modification
- Visual regression can't be caught by unit tests - requires manual verification
- Each page tested immediately after its refactoring commit
- CSS audit ensures no classes are missing or duplicated

**Implementation Approach**:
1. Run existing test suite: `pytest tests/` (baseline before changes)
2. After each page refactoring:
   - Run tests again: `pytest tests/`
   - Manual check: Start app, navigate to refactored page, verify all UI elements styled correctly
   - CSS audit: Verify no "undefined class" warnings in browser console
3. Performance measurement:
   - Use Chrome DevTools Network tab to measure CSS loaded per page
   - Compare before/after load times
   - Verify SC-001 (30% load time reduction) and SC-002 (50% CSS size reduction)

**Validation Checklist** (per page):
- [ ] All tests pass
- [ ] Page renders without console errors
- [ ] All interactive elements functional (buttons, filters, dropdowns)
- [ ] CSS loaded matches expected files (common.css + page-specific only)
- [ ] No visual regressions (compare screenshots if needed)

---

## Summary of Key Decisions

| Topic | Decision | Impact |
|-------|----------|--------|
| CSS Loading | Static registration at app startup with naming convention | Simple, no runtime overhead |
| CSS Namespacing | Page-specific prefixes (`.mriqc-`, `.redcap-`, etc.) | Prevents collisions, clear ownership |
| Helper Organization | Per-page modules + common_helpers.py | Maintainable, supports rollback |
| Rollback Strategy | Git commits per page + config flag toggle | Granular revert capability |
| CSS Splitting | Manual analysis with grep tooling | Accurate, no automation complexity |
| Testing | Existing tests + manual verification | Zero regression guarantee |

## Open Questions

**Status**: None - all clarifications resolved in spec clarification session (2025-11-27)

## Next Steps

Proceed to **Phase 1: Design & Contracts** to create:
1. `data-model.md` - Document refactoring entities and relationships
2. `quickstart.md` - Developer guide for maintaining split CSS and helper modules
3. Update agent context with technology decisions
