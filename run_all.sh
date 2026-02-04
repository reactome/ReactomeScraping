#!/bin/bash
# Reactome Scraping and MDX Conversion Pipeline
# This script runs all processing steps in the correct order

set -e  # Exit on any error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Use venv python if available, otherwise system python3
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
else
    PYTHON="python3"
fi

echo "Using Python: $PYTHON"
echo "================================"

echo ""
echo "Step 1/7: Scraping pages from reactome.org..."
echo "----------------------------------------"
$PYTHON scraper.py
echo "✓ Scraping complete"

echo ""
echo "Step 2/7: Fixing image paths in scraped HTML..."
echo "----------------------------------------"
$PYTHON fix_image_paths.py
echo "✓ Image paths fixed"

echo ""
echo "Step 3/7: Converting HTML to MDX..."
echo "----------------------------------------"
$PYTHON convert_to_mdx.py
echo "✓ MDX conversion complete"

echo ""
echo "Step 4/7: Reorganizing pages..."
echo "----------------------------------------"
$PYTHON reorganize_pages.py
echo "✓ Pages reorganized"

echo ""
echo "Step 5/7: Flattening folder structure..."
echo "----------------------------------------"
$PYTHON flatten_folders.py
echo "✓ Folders flattened"

echo ""
echo "Step 6/7: Fixing category metadata..."
echo "----------------------------------------"
$PYTHON fix_categories.py
echo "✓ Categories fixed"

echo ""
echo "Step 7/8: Fixing MDX image paths..."
echo "----------------------------------------"
$PYTHON fix_mdx_image_paths.py
echo "✓ MDX image paths fixed"

echo ""
echo "Step 8/8: Renaming item-page.mdx to index.mdx..."
echo "----------------------------------------"
$PYTHON rename_to_index.py
echo "✓ Files renamed to index.mdx"

echo ""
echo "================================"
echo "✓ All steps completed successfully!"
echo ""
echo "Output directories:"
echo "  - scraped_pages/  (original HTML files and images)"
echo "  - mdx_pages/      (converted MDX files with images)"
