#!/usr/bin/env bash
# CSS Analysis Script - Identify which pages use which CSS classes
# Usage: ./analyze-css.sh

ASSETS_DIR="assets"
PAGES_DIR="pages"
CUSTOM_CSS="$ASSETS_DIR/custom.css"
OUTPUT_FILE="specs/001-css-optimization/css-mapping.md"

echo "# CSS Class Mapping Analysis" > "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "**Generated**: $(date)" >> "$OUTPUT_FILE"
echo "**Source**: $CUSTOM_CSS" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Extract all class selectors from custom.css
echo "## CSS Classes Found" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Find all class definitions (lines starting with . and capturing the class name)
grep -E '^\.[a-zA-Z0-9_-]+' "$CUSTOM_CSS" | sed 's/[[:space:]]*{.*//' | sort -u > /tmp/css_classes.txt

CLASS_COUNT=$(wc -l < /tmp/css_classes.txt)
echo "**Total unique classes**: $CLASS_COUNT" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# For each class, find which page files use it
echo "## Class Usage by Page" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

while IFS= read -r class_selector; do
    # Remove the leading dot for searching in Python files
    class_name=$(echo "$class_selector" | sed 's/^\.//')
    
    # Search for usage in page files
    pages_using=$(grep -l "className.*[\"'].*$class_name" "$PAGES_DIR"/*.py 2>/dev/null | sed "s|$PAGES_DIR/||g" | sed 's/.py$//' | tr '\n' ', ' | sed 's/,$//')
    
    if [ -n "$pages_using" ]; then
        echo "- **$class_selector**: $pages_using" >> "$OUTPUT_FILE"
    else
        echo "- **$class_selector**: (no usage found - candidate for removal or in JS)" >> "$OUTPUT_FILE"
    fi
done < /tmp/css_classes.txt

echo "" >> "$OUTPUT_FILE"
echo "## Page-Specific Class Groups" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# Group by page
for page_file in "$PAGES_DIR"/*.py; do
    page_name=$(basename "$page_file" .py)
    echo "### $page_name" >> "$OUTPUT_FILE"
    echo "" >> "$OUTPUT_FILE"
    
    # Find classes used in this page
    classes_in_page=$(grep -o 'className[^"]*"[^"]*"' "$page_file" 2>/dev/null | grep -o '"[^"]*"' | tr -d '"' | tr ' ' '\n' | sort -u | grep -v '^$')
    
    if [ -n "$classes_in_page" ]; then
        echo "$classes_in_page" | while IFS= read -r class_name; do
            # Check if this class exists in custom.css
            if grep -q "^\.$class_name" "$CUSTOM_CSS" 2>/dev/null; then
                echo "- .$class_name" >> "$OUTPUT_FILE"
            fi
        done
    else
        echo "- (no className attributes found)" >> "$OUTPUT_FILE"
    fi
    
    echo "" >> "$OUTPUT_FILE"
done

echo "" >> "$OUTPUT_FILE"
echo "## Namespace Recommendations" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "Based on analysis, recommended prefixes:" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"
echo "| Page | Prefix | Example |" >> "$OUTPUT_FILE"
echo "|------|--------|---------|" >> "$OUTPUT_FILE"
echo "| assistant_sandbox | .assistant- | .assistant-chat-window |" >> "$OUTPUT_FILE"
echo "| mriqc | .mriqc- | .mriqc-table |" >> "$OUTPUT_FILE"
echo "| redcap | .redcap- | .redcap-card |" >> "$OUTPUT_FILE"
echo "| home | .home- | .home-summary |" >> "$OUTPUT_FILE"
echo "| bids | .bids- | .bids-tree |" >> "$OUTPUT_FILE"
echo "| fmriprep | .fmriprep- | .fmriprep-report |" >> "$OUTPUT_FILE"
echo "| freesurfer | .freesurfer- | .freesurfer-qc |" >> "$OUTPUT_FILE"
echo "| subject_detail | .subject- | .subject-info |" >> "$OUTPUT_FILE"

echo "✓ CSS analysis complete: $OUTPUT_FILE"
rm /tmp/css_classes.txt
