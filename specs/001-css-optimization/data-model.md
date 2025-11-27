# Data Model: CSS Split and Page Refactoring

**Feature**: CSS Split and Page Refactoring  
**Branch**: `001-css-optimization`  
**Date**: November 27, 2025

## Overview

This document defines the logical structure of code entities involved in the refactoring. Since this is a code reorganization (not data modeling), "entities" here refer to code artifacts and their relationships.

## Entities

### 1. Page Module

**Location**: `pages/*.py`  
**Purpose**: Dash page module containing layout and callbacks for a single dashboard page  
**Current State**: Contains layout(), callbacks, AND helper functions (to be refactored)  
**Target State**: Contains ONLY layout() and callbacks; imports helpers from src/

**Attributes**:
- `module_name`: str - Base name without .py extension (e.g., "mriqc", "assistant_sandbox")
- `layout`: function - Returns Dash component tree for the page
- `callbacks`: list[function] - Dash callback functions decorated with @app.callback
- `imports`: list[str] - Module dependencies (should include helper module after refactoring)

**Relationships**:
- **has-one** CSS Stylesheet (page-specific)
- **has-one** Helper Module (in src/flux_notebooks/pages/)
- **uses** Common CSS Stylesheet (shared)
- **may-use** Common Helper Module (shared)

**Validation Rules**:
- MUST have layout() function
- MUST NOT contain helper functions after refactoring (FR-005)
- MUST import helpers from src/flux_notebooks/pages/ if needed

**Lifecycle**:
1. **Current**: Contains mixed concerns (UI + logic)
2. **Transition**: Helper functions moved to src/, imports added
3. **Final**: Clean separation - UI only

---

### 2. CSS Stylesheet

**Location**: `assets/*.css`  
**Purpose**: Cascading style sheet defining visual styles for UI components  
**Current State**: Single global `custom.css` (313 lines)  
**Target State**: Multiple page-specific files + `common.css`

**Attributes**:
- `file_name`: str - Name of CSS file (e.g., "mriqc.css", "common.css")
- `page_scope`: str | "common" - Which page it belongs to, or "common" for shared
- `class_prefix`: str | None - Namespace prefix for classes (e.g., "mriqc-", or None for common)
- `selectors`: list[str] - CSS class names defined in the file
- `size_bytes`: int - File size for performance tracking

**Relationships**:
- **belongs-to** Page Module (1:1 for page-specific CSS)
- **used-by** Multiple Page Modules (for common.css)
- **loaded-via** CSS Loader (at app startup)

**Validation Rules**:
- Page-specific CSS MUST use namespaced classes (FR-009)
- Common CSS MUST contain only styles used by 2+ pages
- Total CSS loaded per page MUST be <50% of original custom.css size (SC-002)

**State Transitions**:
```
custom.css (single file)
    ↓ [analyze + split]
├── common.css (shared components)
├── assistant_sandbox.css (assistant page)
├── mriqc.css (MRIQC pages)
├── redcap.css (RedCap page)
├── home.css (home page)
├── bids.css (BIDS browser)
├── fmriprep.css (fMRIPrep pages)
├── freesurfer.css (FreeSurfer page)
└── subject.css (subject detail)
```

---

### 3. Helper Function

**Location**: Functions defined in pages/*.py (current) → src/flux_notebooks/pages/*.py (target)  
**Purpose**: Reusable function performing data processing, formatting, or UI generation  
**Current State**: Defined inline in page modules  
**Target State**: Organized in dedicated helper modules

**Attributes**:
- `function_name`: str - Name of the function
- `signature`: str - Function signature (parameters and return type)
- `source_page`: str - Original page module where function was defined
- `usage_count`: int - Number of pages that use this function
- `category`: "page-specific" | "shared" - Whether used by one or multiple pages

**Relationships**:
- **defined-in** Helper Module
- **imported-by** Page Module(s)
- **may-call** Other Helper Functions

**Validation Rules**:
- MUST maintain identical signature when moved (FR-006)
- MUST maintain identical behavior when moved (FR-008)
- Shared functions (usage_count >= 2) MUST go in common_helpers.py
- Page-specific functions MUST go in {page_name}_helpers.py

**Lifecycle**:
1. **Discovery**: Identify function in pages/*.py
2. **Classification**: Determine if page-specific or shared (via grep analysis)
3. **Relocation**: Move to appropriate helper module in src/
4. **Import**: Update original page to import from new location
5. **Validation**: Verify tests pass and functionality unchanged

**Examples**:
```python
# Page-specific helper (used only in pages/mriqc.py)
Function: color_for_modality
Location: src/flux_notebooks/pages/mriqc_helpers.py
Usage: 1 page

# Shared helper (used in pages/home.py and pages/redcap.py)
Function: _height_to_css
Location: src/flux_notebooks/pages/common_helpers.py
Usage: 2+ pages
```

---

### 4. Helper Module

**Location**: `src/flux_notebooks/pages/*.py`  
**Purpose**: Container module holding helper functions for a specific page or shared utilities  
**Current State**: Does not exist (to be created)  
**Target State**: One module per page + one common module

**Attributes**:
- `module_name`: str - Name of helper module (e.g., "mriqc_helpers", "common_helpers")
- `page_association`: str | "common" - Associated page module or "common" for shared
- `function_count`: int - Number of helper functions in module
- `dependencies`: list[str] - Other modules imported by this helper module

**Relationships**:
- **contains** Helper Functions (1:many)
- **imported-by** Page Module (primary) or Multiple Page Modules (if common)
- **may-import** Other Helper Modules

**Validation Rules**:
- MUST be importable from pages/*.py via `from flux_notebooks.pages.{module_name} import ...`
- MUST NOT create circular dependencies with page modules
- Common module MUST contain only functions used by 2+ pages

**Module Mapping**:
```
Page Module              → Helper Module
-----------------           -------------------------
assistant_sandbox.py     → assistant_helpers.py
bids.py                  → bids_helpers.py
fmriprep_detail.py       → fmriprep_helpers.py
fmriprep_index.py        → fmriprep_helpers.py
freesurfer.py            → freesurfer_helpers.py
home.py                  → home_helpers.py
mriqc.py                 → mriqc_helpers.py
mriqc_detail.py          → mriqc_helpers.py
redcap.py                → redcap_helpers.py
subject_detail.py        → subject_helpers.py
(multiple)               → common_helpers.py
```

---

### 5. CSS Loader

**Location**: `app.py` (Dash application initialization)  
**Purpose**: Mechanism that determines which CSS files to load for the application  
**Current State**: Loads single custom.css globally  
**Target State**: Loads common.css + page-specific CSS based on naming convention

**Attributes**:
- `loading_strategy`: "static" - CSS files determined at app startup
- `common_css`: str - Path to common.css (always loaded)
- `page_css_map`: dict[str, str] - Mapping from page name to CSS file path
- `feature_flag`: bool - Toggle to enable/disable split CSS (for rollback)

**Behavior**:
```python
# Pseudocode for CSS Loader logic
def initialize_css_loading():
    css_files = ["assets/common.css"]  # Always load common
    
    if FLUX_USE_SPLIT_CSS:  # Feature flag
        # Scan pages/ directory
        for page_file in list_pages():
            page_name = page_file.stem  # e.g., "mriqc"
            css_path = f"assets/{page_name}.css"
            if css_path.exists():
                css_files.append(css_path)
    else:
        # Fallback to original single CSS
        css_files = ["assets/custom.css"]
    
    # Register with Dash
    app.external_stylesheets = css_files
```

**Relationships**:
- **loads** CSS Stylesheets
- **configured-by** Feature Flag (for rollback)
- **initializes-at** App Startup

**Validation Rules**:
- MUST load common.css for all pages
- MUST use naming convention (page_name.py → page_name.css)
- MUST support rollback via feature flag

---

## Relationships Diagram

```
┌─────────────────┐
│  Page Module    │
│  (pages/*.py)   │
└────┬────────┬───┘
     │        │
     │ uses   │ has
     │        │
     ▼        ▼
┌────────────────┐  ┌──────────────────┐
│ Helper Module  │  │ CSS Stylesheet   │
│ (src/flux_     │  │ (assets/*.css)   │
│  notebooks/    │  │                  │
│  pages/*.py)   │  │                  │
└────┬───────────┘  └────┬─────────────┘
     │                    │
     │ contains           │ loaded by
     │                    │
     ▼                    ▼
┌───────────────┐   ┌──────────────┐
│ Helper        │   │ CSS Loader   │
│ Function      │   │ (app.py)     │
└───────────────┘   └──────────────┘

┌─────────────────────────┐
│ common.css              │ ◄─── loaded by all pages
└─────────────────────────┘

┌─────────────────────────┐
│ common_helpers.py       │ ◄─── imported by multiple pages
└─────────────────────────┘
```

## Refactoring Invariants

These properties MUST remain true throughout and after refactoring:

1. **Functional Equivalence**: `∀ page p, behavior(p, before) ≡ behavior(p, after)`
2. **Complete Coverage**: Every helper function relocated OR justified as page-only
3. **No Orphaned Styles**: Every CSS class in original custom.css appears in exactly one output file
4. **Import Integrity**: All imports resolve correctly; no ImportError at runtime
5. **Test Stability**: All tests pass before AND after refactoring without modification
6. **Progressive Structure**: Each page can be refactored independently; no big-bang migration

## Change Tracking

For each page refactoring:

| Page | Baseline LOC | CSS Created | Helpers Moved | LOC Reduced | Commit SHA | Status |
|------|--------------|-------------|---------------|-------------|------------|--------|
| assistant_sandbox | 687 | assistant_sandbox.css (252 lines) | 0 (no helpers) | 0 (CSS only) | ff02815 | CSS Split Complete |
| mriqc | 645 | mriqc.css | TBD | TBD | - | Pending |
| mriqc_detail | 129 | mriqc.css | TBD | TBD | - | Pending |
| redcap | 429 | redcap.css | TBD | TBD | - | Pending |
| home | 694 | home.css | TBD | TBD | - | Pending |
| bids | 453 | bids.css | TBD | TBD | - | Pending |
| fmriprep_index | 348 | fmriprep.css | TBD | TBD | - | Pending |
| fmriprep_detail | 155 | fmriprep.css | TBD | TBD | - | Pending |
| freesurfer | 16 | freesurfer.css | TBD | TBD | - | Pending |
| subject_detail | 438 | subject.css | TBD | TBD | - | Pending |

**Baseline Total**: 3994 LOC in pages/  
**Target**: <2397 LOC (40% reduction = 1597 LOC removed)  

**CSS Baseline**: 313 lines in assets/custom.css  
**CSS Current State**:
- common.css: 68 lines (shared: floating-info-panel)
- assistant_sandbox.css: 252 lines (complete .flux-assistant-sandbox namespace)
- custom.css: 14 lines (legacy placeholder with migration notes)
- **Total Split**: 334 lines across 3 files (+21 lines for headers/docs, -299 lines of duplication removed from custom.css)
