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

## Customization

### Adding/Removing Seed URLs

Edit the `get_seed_urls()` function in `scraper.py` to modify the starting URLs.

### Changing URL Filters

Modify the `is_valid_url()` method in the `ReactomeScraper` class to change which URLs are scraped or skipped.

### Extracting Different Elements

Modify the `extract_content()` method to target different HTML elements.
