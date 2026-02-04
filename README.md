# Reactome.org Web Scraper

A Python web scraper that extracts content from reactome.org pages and saves them organized by their URL routes.

## What it Scrapes

The scraper extracts two types of content elements:
- `<div class="item-page">` - Main content pages
- `<div class="leading-n" itemprop="blogpost">` - Blog post entries

## Installation

1. Create a virtual environment (recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/Mac
   # or
   .\venv\Scripts\activate  # On Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Usage

Run the scraper with default settings:
```bash
python scraper.py
```

This will:
- Crawl reactome.org starting from predefined seed URLs
- Save extracted content to `./scraped_pages/` directory
- Wait 1 second between requests (to be polite to the server)

### Command Line Options

```bash
python scraper.py [options]

Options:
  -o, --output DIR      Output directory (default: scraped_pages)
  -d, --delay SECONDS   Delay between requests (default: 1.0)
  -m, --max-pages NUM   Maximum pages to scrape (default: unlimited)
  -s, --seed-only       Only scrape seed URLs, don't crawl further
```

### Examples

Scrape only the predefined seed URLs (faster, limited coverage):
```bash
python scraper.py --seed-only
```

Limit to 50 pages with a 2-second delay:
```bash
python scraper.py --max-pages 50 --delay 2.0
```

Specify a custom output directory:
```bash
python scraper.py --output ./my_scraped_data
```

## Output Structure

The scraper organizes files based on their URL routes:

```
scraped_pages/
├── what-is-reactome/
│   └── item-page.html
├── about/
│   ├── news/
│   │   ├── item-page.html
│   │   ├── blogpost-1.html
│   │   └── blogpost-2.html
│   ├── team/
│   │   └── item-page.html
│   └── statistics/
│       └── item-page.html
├── documentation/
│   ├── item-page.html
│   └── faq/
│       └── item-page.html
└── ...
```

Each saved HTML file includes comments with:
- Source URL
- Timestamp when scraped

## Logging

The scraper logs its activity to both:
- Console output
- `scraper.log` file

## Notes

- The scraper respects a configurable delay between requests to avoid overloading the server
- URLs to API endpoints, download pages, and non-HTML resources are automatically skipped
- Only internal reactome.org links are followed
- Duplicate URLs are automatically handled
- Images are automatically downloaded and saved to `scraped_pages/images/<page-route>/`

## Customization

### Adding/Removing Seed URLs

Edit the `get_seed_urls()` function in `scraper.py` to modify the starting URLs.

### Changing URL Filters

Modify the `is_valid_url()` method in the `ReactomeScraper` class to change which URLs are scraped or skipped.

### Extracting Different Elements

Modify the `extract_content()` method to target different HTML elements.

---

# HTML to MDX Converter

Converts scraped HTML files to MDX format with frontmatter metadata.

## Usage

```bash
python3 convert_to_mdx.py [options]

Options:
  -i, --input DIR     Input directory containing HTML files (default: scraped_pages)
  -o, --output DIR    Output directory for MDX files (default: mdx_pages)
  -v, --verbose       Enable verbose logging
```

## Features

- Extracts title, category (route), and body content
- For article pages (news, spotlight): extracts author, date, and tags
- Converts HTML to clean Markdown using html2text
- Copies images from `scraped_pages/images/` to `mdx_pages/images/`
- Updates image paths to work with the MDX output structure

## Output Format

Each MDX file includes YAML frontmatter:

```yaml
---
title: "Page Title"
category: "about/news"
author: "Author Name"       # For articles only
date: "2024-01-15"          # For articles only
tags: ["news", "release"]   # For articles only
---
```

## Output Structure

```
mdx_pages/
├── images/
│   ├── about/
│   │   └── news/
│   │       └── image.png
│   └── userguide/
│       └── diagram.png
├── about/
│   └── news/
│       └── item-page.mdx
├── userguide/
│   └── item-page.mdx
└── ...
```

---

# Reorganize Pages

Reorganizes `mdx_pages` to match a desired navigation structure by moving folders to new locations.

## Usage

```bash
python3 reorganize_pages.py
```

## Configuration

Edit the `MOVES` list in `reorganize_pages.py` to define source and destination paths:

```python
MOVES = [
    ("what-is-reactome", "about/what-is-reactome"),
    ("userguide", "documentation/userguide"),
    # Add more moves as needed
]
```

## Features

- Moves page directories to new locations
- Automatically moves corresponding images from `mdx_pages/images/`
- Updates image paths within MDX files after reorganization
- Skips moves if source doesn't exist or destination already exists

---

# Fix Categories

Updates the `category` field in MDX frontmatter to match the file's actual location after reorganization.

## Usage

```bash
python3 fix_categories.py
```

## What It Does

After running `reorganize_pages.py`, the `category` field in frontmatter may not match the new file location. This script:

1. Scans all `.mdx` files in `mdx_pages/`
2. Compares the `category` value with the actual file path
3. Updates the `category` to match the current location

---

# Flatten Folders

Simplifies the directory structure by moving `item-page.mdx` files up one level and renaming them.

## Usage

```bash
python3 flatten_folders.py
```

## What It Does

Converts structures like:
```
mdx_pages/
└── about/
    └── news/
        └── item-page.mdx
```

To:
```
mdx_pages/
└── about/
    └── news.mdx
```

This creates cleaner URLs and simpler file organization for static site generators.

---

# Fix Image Paths

Fixes broken image references in scraped HTML files caused by the scraper's deduplication logic.

## Usage

```bash
python3 fix_image_paths.py
```

## What It Does

The scraper has a bug where the same image URL downloaded by multiple pages results in different relative paths in HTML, but the image is only saved at the first location encountered. This script:

1. Builds an index of all existing images by filename
2. Scans HTML files for image references
3. Identifies references pointing to non-existent paths
4. Copies images from their actual location to expected locations

---

# Fix MDX Image Paths

Fixes image paths in MDX files to match the actual image locations after flattening and reorganization.

## Usage

```bash
python3 fix_mdx_image_paths.py
```

## What It Does

1. Fixes malformed image references (trailing `>` characters)
2. Updates paths for flattened images (e.g., `folder/subfolder/image.png` → `folder/subfolder.png`)
3. Resolves general path mismatches by looking up images by filename

---

# Complete Workflow

To scrape and convert the Reactome website to MDX:

```bash
# 1. Scrape pages and images from reactome.org
python3 scraper.py

# 2. Fix image path issues in scraped HTML files
python3 fix_image_paths.py

# 3. Convert HTML to MDX format
python3 convert_to_mdx.py

# 4. Reorganize pages to match desired nav structure
python3 reorganize_pages.py

# 5. Flatten folder structure (rename item-page.mdx to parent folder name)
python3 flatten_folders.py

# 6. Fix category metadata in frontmatter to match new locations
python3 fix_categories.py

# 7. Fix any remaining image path issues in MDX files
python3 fix_mdx_image_paths.py
```

## Script Descriptions

| Script | Purpose |
|--------|---------|
| `scraper.py` | Crawls reactome.org and saves HTML pages + images |
| `fix_image_paths.py` | Fixes missing image references in scraped HTML |
| `convert_to_mdx.py` | Converts HTML to MDX with frontmatter metadata |
| `reorganize_pages.py` | Moves pages to match navigation structure |
| `flatten_folders.py` | Renames `item-page.mdx` files to parent folder names |
| `fix_categories.py` | Updates category frontmatter to match file locations |
| `fix_mdx_image_paths.py` | Fixes image paths in MDX after reorganization |

## Output

After running all scripts, you'll have:
- `scraped_pages/` - Original HTML files and images
- `mdx_pages/` - Converted MDX files with proper structure and working image paths
