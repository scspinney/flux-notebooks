# Feature Specification: CSS Split and Page Refactoring

**Feature Branch**: `001-css-optimization`  
**Created**: November 27, 2025  
**Status**: Draft  
**Input**: User description: "There's a pages folder and in there each page has its own python script that defines some functions and the html element layout for the page, and you can add css styling there, or use a global file like I did. But its so big now every page loads it and its slow, so the right thing to do is split it up. Then the src folder that mostly has the actual functions for each back end stuff. I need to cleanly move all helper functions out of the pages/*.py scripts so its just setting up the page and if needed calling the src .py functions. Lets keep the changes minimal and functional. Lets not add dependencies unless this is explicitly asked for. The goal is to optimize the performance of the dashboards when loading the respective css styling. Any markdown files procudes as part of the features should be placed under the feature folder and not the root."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Page-Specific CSS Loading (Priority: P1)

Dashboard pages load only the CSS styles relevant to their specific functionality rather than loading a single large global stylesheet, resulting in faster initial page load times.

**Why this priority**: This directly addresses the performance bottleneck identified in the user description where the large global CSS file slows down all page loads. This is the core technical problem affecting user experience.

**Independent Test**: Can be fully tested by measuring page load time before and after CSS split for any dashboard page (e.g., MRIQC, fMRIPrep, RedCap) and verifying that only page-specific CSS files are loaded in browser DevTools.

**Acceptance Scenarios**:

1. **Given** a user navigates to the MRIQC page, **When** the page loads, **Then** only the base CSS and MRIQC-specific CSS files are loaded (not CSS for assistant, RedCap, or other pages)
2. **Given** a user navigates to the RedCap page, **When** the page loads, **Then** only the base CSS and RedCap-specific CSS files are loaded
3. **Given** a user navigates to the Assistant Sandbox page, **When** the page loads, **Then** only the base CSS and assistant-specific CSS files are loaded
4. **Given** a user switches between different dashboard pages, **When** each page renders, **Then** page load time is reduced by at least 30% compared to the current implementation

---

### User Story 2 - Clean Page Module Structure (Priority: P2)

Page Python scripts contain only layout definitions and UI callbacks, with all business logic and helper functions moved to appropriate modules in the src/ directory, making the codebase more maintainable.

**Why this priority**: This improves code organization and maintainability, which is essential for long-term development but doesn't directly impact immediate user experience like CSS performance does.

**Independent Test**: Can be fully tested by code inspection - verify that pages/*.py files contain only dash layout definitions and callback decorators, with all data processing, formatting, and utility functions relocated to src/ modules.

**Acceptance Scenarios**:

1. **Given** a developer opens any pages/*.py file, **When** reviewing the code structure, **Then** the file contains only layout() function, callback definitions, and imports (no helper functions, data processing, or utility logic)
2. **Given** a developer needs to modify data formatting logic, **When** searching for the function, **Then** it is located in the appropriate src/ module (not in a page file)
3. **Given** a developer runs the application after refactoring, **When** interacting with any dashboard page, **Then** all functionality works identically to before the refactoring
4. **Given** a developer examines the src/ directory, **When** reviewing module organization, **Then** functions are logically grouped (e.g., formatting utilities, data queries, visualization helpers)

---

### User Story 3 - Zero Regression in Functionality (Priority: P1)

All existing dashboard features, visualizations, and interactions continue to work exactly as before the refactoring, ensuring no disruption to users or data workflows.

**Why this priority**: While this is technically a constraint on the implementation, maintaining functionality is critical for production systems and user trust. This ties with P1 because any functional regression would negate performance gains.

**Independent Test**: Can be fully tested by executing existing test suite and performing manual verification of each dashboard page's features (navigation, filtering, data display, interactive components).

**Acceptance Scenarios**:

1. **Given** a user performs any action on any dashboard page, **When** the action completes, **Then** the behavior and results are identical to pre-refactoring behavior
2. **Given** a user navigates through the BIDS browser, **When** clicking on subjects or sessions, **Then** all data displays correctly with proper styling
3. **Given** a user interacts with the Assistant Sandbox chat, **When** sending messages, **Then** the chat interface responds and displays correctly
4. **Given** a user views QC reports (MRIQC/fMRIPrep), **When** the reports render, **Then** all visualizations, tables, and links function properly

---

### Edge Cases

- What happens when a page attempts to use CSS classes that were in the global file but are now split into a different page's CSS file?
- How does the system handle CSS conflicts if multiple pages define similar class names? (Resolved: use page-specific prefixes for all classes to prevent conflicts)
- What happens if a helper function moved to src/ has dependencies on other page-specific utilities?
- How does the application handle pages that share common UI patterns? (Resolved: shared UI components use common.css loaded by all pages)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST split the current global CSS file (assets/custom.css) into page-specific CSS files based on which pages use which styles
- **FR-002**: System MUST create a base/common CSS file (common.css) containing all shared UI component styles used across multiple pages (e.g., data tables, filter dropdowns, cards)
- **FR-003**: Each page MUST load only its specific CSS file plus the common CSS file via static analysis at app startup (using naming convention where page_name.py loads page_name.css)
- **FR-004**: System MUST move all helper functions from pages/*.py files to appropriate modules in src/flux_notebooks/ (each page gets its own helper module, with common_helpers.py for functions shared across multiple pages)
- **FR-005**: Page files MUST retain only layout() functions, callback decorators, and necessary imports after refactoring
- **FR-006**: System MUST maintain existing function signatures and return values when moving functions to src/
- **FR-007**: System MUST not introduce any new external dependencies (no new packages in requirements.txt or pyproject.toml)
- **FR-008**: System MUST preserve all existing dashboard functionality without any behavioral changes
- **FR-009**: CSS file organization MUST follow a clear naming convention (e.g., page_name.css for page-specific styles) with page-specific class prefixes to prevent conflicts (e.g., `.mriqc-table`, `.redcap-card`)
- **FR-010**: All refactored code MUST pass existing tests without modification to test assertions
- **FR-011**: System MUST support progressive rollback capability where individual pages can be reverted to original structure independently

### Key Entities

- **Page Module**: Python file in pages/ directory containing Dash layout and callbacks (e.g., mriqc.py, assistant_sandbox.py, redcap.py)
- **CSS Stylesheet**: Cascading style sheet file defining visual styles for UI components (currently one large custom.css, to be split into multiple files)
- **Helper Function**: Utility function that performs data processing, formatting, or computation (currently in pages/*.py, to be moved to src/)
- **Source Module**: Python module in src/flux_notebooks/ containing business logic and utilities (destination for moved helper functions)

## Clarifications

### Session 2025-11-27

- Q: How should the system determine which CSS files to load for each page? → A: Static analysis at build/startup combined with naming convention (analyze page imports/dependencies at app startup and register CSS files, with automatic loading of CSS files matching page module names)
- Q: When moving helper functions from pages/*.py to src/, how should functions be organized if they're shared across multiple pages? → A: Per-page modules with shared - Each page gets its own module in src/, plus a common_helpers.py for truly shared functions
- Q: How should CSS be handled for UI components that appear on multiple pages (e.g., data tables, filter dropdowns, cards)? → A: Common component CSS - Create common.css containing all shared UI component styles, loaded by all pages
- Q: How should CSS class naming conflicts be prevented when splitting styles into multiple files? → A: Namespace with page prefixes - Use page-specific prefixes for all classes (e.g., `.mriqc-table`, `.redcap-card`)
- Q: What rollback strategy should be used if CSS split or refactoring causes issues in production? → A: Progressive rollback per page - Ability to revert individual pages to original structure while keeping others refactored

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Dashboard page initial load time is reduced by at least 30% when measured with browser DevTools (comparing before and after CSS split)
- **SC-002**: Total CSS loaded per page is reduced by at least 50% compared to loading the single global CSS file
- **SC-003**: Number of lines of code in pages/*.py files is reduced by at least 40% after moving helper functions to src/
- **SC-004**: All existing automated tests pass without modification
- **SC-005**: Manual verification of all dashboard pages shows zero functional regressions
- **SC-006**: Browser DevTools Network tab shows that only relevant CSS files are loaded for each page (no unused CSS loaded)
