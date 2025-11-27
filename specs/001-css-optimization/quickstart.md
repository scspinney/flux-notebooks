# Quickstart: CSS Split and Page Refactoring

**Feature**: CSS Split and Page Refactoring  
**Branch**: `001-css-optimization`  
**Date**: November 27, 2025

## For Developers: Understanding the Refactored Structure

### Overview

This refactoring splits a large global CSS file into page-specific files and moves helper functions from page modules into organized source modules. The goal is faster page loads (30% improvement) and better code maintainability.

### CSS Loading Mechanism

**Dash Automatic Loading**: Dash automatically loads all CSS files from the `assets/` folder in alphabetical order. No explicit registration required.

**Current State (Progressive Migration)**:
```
assets/
  assistant_sandbox.css      # Assistant page styles (213 lines) - DONE
  common.css                 # Shared styles (67 lines) - DONE
  custom.css                 # LEGACY monolithic CSS (313 lines) - KEPT FOR ROLLBACK
  custom.css.backup          # Original backup
  flux_inputs.css            # Input styling (existing)
```

**Feature Flag**: Set `FLUX_PAGE_CSS=true` environment variable to document intent to use split CSS (currently both old and new CSS files load simultaneously during migration).

### Key Changes

**Before**:
```
pages/mriqc.py                 # Layout + callbacks + helpers (200 lines)
assets/custom.css              # All styles (313 lines)
```

**After**:
```
pages/mriqc.py                 # Layout + callbacks only (120 lines)
src/flux_notebooks/pages/
  └── mriqc_helpers.py         # Helper functions (80 lines)
assets/
  ├── common.css               # Shared styles (~67 lines)
  ├── assistant_sandbox.css    # Assistant-specific styles (~213 lines)
  └── mriqc.css                # MRIQC-specific styles (~50 lines)
```

### Adding a New Page

When creating a new dashboard page:

1. **Create page module** in `pages/new_page.py`:
   ```python
   import dash
   from dash import html, dcc, callback, Input, Output
   from flux_notebooks.pages.new_page_helpers import some_helper
   
   dash.register_page(__name__, path="/new-page", name="New Page")
   
   def layout():
       return html.Div([
           html.H1("New Page", className="new-page-title"),
           # Your layout here
       ])
   
   @callback(Output(...), Input(...))
   def some_callback(input_value):
       result = some_helper(input_value)
       return result
   ```

2. **Create helper module** in `src/flux_notebooks/pages/new_page_helpers.py`:
   ```python
   """Helper functions for new_page dashboard."""
   
   def some_helper(value):
       """Process value for new page."""
       return value.upper()
   ```

3. **Create page CSS** in `assets/new_page.css`:
   ```css
   /* Styles for New Page dashboard */
   
   .new-page-title {
       color: #2c3e50;
       font-size: 2rem;
   }
   
   .new-page-card {
       background: white;
       border-radius: 8px;
   }
   ```

4. **CSS is auto-loaded**: Dash automatically loads all CSS files from `assets/` folder (including `common.css` and `new_page.css`)

### Modifying an Existing Page

**To add a new helper function**:

1. Add function to appropriate helper module:
   ```python
   # src/flux_notebooks/pages/mriqc_helpers.py
   def new_helper(data):
       """New functionality for MRIQC page."""
       return process(data)
   ```

2. Import in page module:
   ```python
   # pages/mriqc.py
   from flux_notebooks.pages.mriqc_helpers import existing_helper, new_helper
   ```

**To add page-specific styles**:

1. Add to page's CSS file with namespaced classes:
   ```css
   /* assets/mriqc.css */
   .mriqc-new-component {
       background: #ecf0f1;
   }
   ```

2. Use in page layout:
   ```python
   html.Div("Content", className="mriqc-new-component")
   ```

**To add shared styles** (used by 2+ pages):

1. Add to common.css WITHOUT namespace:
   ```css
   /* assets/common.css */
   .flux-shared-button {
       padding: 10px 20px;
   }
   ```

2. Use in any page:
   ```python
   html.Button("Click", className="flux-shared-button")
   ```

### Troubleshooting

**ImportError: No module named 'flux_notebooks.pages.X_helpers'**

- Ensure helper module exists: `src/flux_notebooks/pages/X_helpers.py`
- Check `__init__.py` exists in `src/flux_notebooks/pages/` (should be empty or import helpers)

**CSS styles not applying**

- Check browser DevTools Network tab - is the CSS file loading?
- Verify CSS file name matches page name: `pages/mriqc.py` → `assets/mriqc.css`
- Check class name spelling in both Python and CSS
- Ensure page-specific classes use correct prefix (e.g., `.mriqc-`)

**Function not found after refactoring**

- Verify import statement: `from flux_notebooks.pages.X_helpers import function_name`
- Check function was actually moved to helper module (grep for function name)
- Ensure helper module is in correct location: `src/flux_notebooks/pages/`

**Tests failing after changes**

- Run full test suite: `pytest tests/`
- Check if any tests import from old locations
- Verify all helper functions maintain exact same signatures and behavior

### CSS Naming Conventions

**Page-specific classes** (used in only one page):
```css
/* assets/mriqc.css */
.mriqc-table { }
.mriqc-header { }
.mriqc-filter-dropdown { }
```

**Shared component classes** (used in multiple pages):
```css
/* assets/common.css */
.flux-table { }
.flux-card { }
.flux-button-primary { }
```

**Namespace prefixes by page**:
- Assistant Sandbox: `.assistant-`
- BIDS Browser: `.bids-`
- fMRIPrep: `.fmriprep-`
- FreeSurfer: `.freesurfer-`
- Home: `.home-`
- MRIQC: `.mriqc-`
- RedCap: `.redcap-`
- Subject Detail: `.subject-`

### Helper Function Organization

**Rule of thumb**: If a function is used by only ONE page, it belongs in that page's helper module. If used by 2+ pages, it belongs in `common_helpers.py`.

**Example - Page-specific helper**:
```python
# src/flux_notebooks/pages/mriqc_helpers.py
def color_for_modality(name: str):
    """Return Bootstrap color class for MRIQC modality."""
    return {"T1w": "primary", "bold": "success"}.get(name, "secondary")
```

**Example - Shared helper**:
```python
# src/flux_notebooks/pages/common_helpers.py
def _height_to_css(height):
    """Convert height specification to CSS value."""
    if isinstance(height, int):
        return f"{height}px"
    return str(height)
```

### Testing Your Changes

1. **Run existing tests**:
   ```bash
   pytest tests/
   ```

2. **Manual verification**:
   ```bash
   python app.py
   # Navigate to your page in browser
   # Open DevTools > Network tab
   # Verify only relevant CSS files loaded
   ```

3. **Check CSS coverage**:
   - Inspect loaded CSS files in DevTools
   - Confirm common.css + page-specific CSS only
   - No 404 errors for missing CSS files

4. **Performance measurement**:
   ```bash
   # Use Chrome DevTools Network tab
   # Record load time before and after changes
   # Verify 30% improvement
   ```

### Rollback Procedure

If issues arise with refactored page:

**Option 1: Revert specific page** (progressive rollback):
```bash
# Find the commit that refactored the problematic page
git log --oneline specs/001-css-optimization/data-model.md

# Revert just that commit
git revert <commit-sha>

# Page returns to original structure, other pages keep improvements
```

**Option 2: Disable split CSS entirely**:
```bash
# Set environment variable
export FLUX_USE_SPLIT_CSS=false

# Restart app - falls back to original custom.css
python app.py
```

**Option 3: Full rollback**:
```bash
# Revert entire feature branch
git checkout main
```

### Performance Monitoring

**Metrics to track**:

1. **CSS size per page**:
   - Before: ~313 lines (entire custom.css)
   - After: ~150 lines (common.css + page-specific)
   - Target: >50% reduction

2. **Page load time**:
   - Measure in DevTools Network tab
   - Target: 30% faster than baseline

3. **Code organization**:
   - Lines in pages/*.py modules
   - Target: 40% reduction via helper extraction

### Common Patterns

**Pattern 1: Data formatting helper**
```python
# src/flux_notebooks/pages/X_helpers.py
def format_metric(value, precision=2):
    """Format numeric metric for display."""
    if value is None:
        return "N/A"
    return f"{value:.{precision}f}"
```

**Pattern 2: UI component generator**
```python
# src/flux_notebooks/pages/X_helpers.py
def make_card(title, content, style_extra=None):
    """Create a styled card component."""
    return html.Div([
        html.H3(title, className="X-card-title"),
        html.Div(content, className="X-card-body")
    ], className="X-card", style=style_extra or {})
```

**Pattern 3: Data query helper**
```python
# src/flux_notebooks/pages/X_helpers.py
def get_filtered_data(df, filters):
    """Apply filters to dataframe."""
    result = df.copy()
    for key, value in filters.items():
        if value:
            result = result[result[key] == value]
    return result
```

### Migration Checklist

When refactoring a page, verify:

- [ ] All helper functions moved to helper module
- [ ] Page module imports helpers correctly
- [ ] CSS split into page-specific file
- [ ] CSS classes use correct namespace prefix
- [ ] All tests pass
- [ ] Manual page verification completed
- [ ] CSS loaded correctly (DevTools check)
- [ ] No console errors
- [ ] Performance improvement measured
- [ ] Commit message describes change
- [ ] data-model.md updated with change tracking

### Getting Help

**Issues or questions?**

1. Check this quickstart guide first
2. Review `data-model.md` for entity relationships
3. Check `research.md` for design decisions and rationale
4. Review commit history: `git log --oneline specs/001-css-optimization/`
5. Open an issue with:
   - What you're trying to do
   - What's not working
   - Error messages or screenshots
   - Which page you're working on
