#!/usr/bin/env python3
"""
Convert scraped HTML files to MDX format.

For pages: Title, Category (route), body
For articles (news, spotlight): Title, Author (if present), Date, tags, body
"""

import os
import re
import shutil
import argparse
import logging
import uuid
from pathlib import Path
from datetime import datetime

from bs4 import BeautifulSoup
import html2text

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configure html2text
def get_html_converter():
    """Create and configure html2text converter."""
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.ignore_emphasis = False
    h.body_width = 0  # Don't wrap lines
    h.unicode_snob = True
    h.skip_internal_links = False
    h.inline_links = True
    h.protect_links = True
    h.ignore_tables = False
    h.single_line_break = False
    return h


def copy_images_for_page(input_dir, output_dir, category):
    """
    Copy images from scraped_pages/images/<category> to mdx_pages/images/<category>.
    Returns the mapping of source to destination paths.
    """
    if not category:
        return {}
    
    src_image_dir = os.path.join(input_dir, 'images', category)
    dst_image_dir = os.path.join(output_dir, 'images', category)
    
    if not os.path.exists(src_image_dir):
        return {}
    
    os.makedirs(dst_image_dir, exist_ok=True)
    
    copied = {}
    for filename in os.listdir(src_image_dir):
        src_path = os.path.join(src_image_dir, filename)
        dst_path = os.path.join(dst_image_dir, filename)
        
        if os.path.isfile(src_path):
            shutil.copy2(src_path, dst_path)
            copied[filename] = dst_path
            logger.debug(f"Copied image: {src_path} -> {dst_path}")
    
    return copied


def fix_image_paths_in_html(soup, category, output_dir):
    """
    Update image src attributes to use proper relative paths for MDX.
    Images are stored at: mdx_pages/images/<category>/<filename>
    MDX files are at: mdx_pages/<category>/<file>.mdx
    
    So from the MDX file, the relative path to images is: ../images/<category>/<filename>
    Or we can use absolute paths from the mdx_pages root: /images/<category>/<filename>
    """
    for img in soup.find_all('img'):
        src = img.get('src', '')
        
        # Handle paths that were already processed by the scraper
        # Format: images/<page_route>/<filename>
        if src.startswith('images/'):
            # Extract just the filename and rebuild the path
            parts = src.split('/')
            if len(parts) >= 3:
                # Keep the structure: images/<category>/<filename>
                # This will be converted to markdown and work relative to mdx_pages root
                img['src'] = '/' + src  # Make it absolute from site root
        
        # Handle data-original-src attribute (kept for reference)
        # No changes needed
    
    return soup


def escape_yaml_string(s):
    """Escape a string for YAML frontmatter."""
    if not s:
        return '""'
    # If string contains special characters, quote it
    if any(c in s for c in [':', '#', '[', ']', '{', '}', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`', '"', "'"]):
        # Escape double quotes and wrap in double quotes
        escaped = s.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    return s


def extract_title(soup):
    """Extract title from the HTML."""
    # Try various title sources
    # 1. Look for page-header or article title
    title_elem = soup.find('h2', class_='item-page-title') or \
                 soup.find('h1', class_='page-header') or \
                 soup.find('h2', class_='page-header') or \
                 soup.find('h1') or \
                 soup.find('h2')
    
    if title_elem:
        return title_elem.get_text(strip=True)
    
    # Try the title tag
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
        # Remove common suffixes
        title = re.sub(r'\s*[-|]\s*Reactome.*$', '', title)
        return title
    
    return "Untitled"


def extract_author(soup):
    """Extract author from news/article pages."""
    # Look for author metadata
    author_elem = soup.find('dd', class_='createdby') or \
                  soup.find('span', class_='createdby') or \
                  soup.find(attrs={'itemprop': 'author'}) or \
                  soup.find('meta', attrs={'name': 'author'})
    
    if author_elem:
        if author_elem.name == 'meta':
            return author_elem.get('content', '').strip()
        return author_elem.get_text(strip=True)
    
    # Look for "Written by" or "By" patterns
    text = soup.get_text()
    author_match = re.search(r'(?:Written by|By|Author:?)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', text)
    if author_match:
        return author_match.group(1)
    
    return None


def extract_date(soup, filepath):
    """Extract date from news/article pages."""
    # Look for date metadata
    date_elem = soup.find('dd', class_='published') or \
                soup.find('dd', class_='created') or \
                soup.find('time') or \
                soup.find(attrs={'itemprop': 'datePublished'}) or \
                soup.find(attrs={'itemprop': 'dateCreated'}) or \
                soup.find('meta', attrs={'name': 'date'})
    
    if date_elem:
        if date_elem.name == 'meta':
            date_str = date_elem.get('content', '')
        elif date_elem.name == 'time':
            date_str = date_elem.get('datetime', '') or date_elem.get_text(strip=True)
        else:
            date_str = date_elem.get_text(strip=True)
        
        # Try to parse various date formats
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%d %B %Y',
            '%B %d, %Y',
            '%d/%m/%Y',
            '%m/%d/%Y',
        ]
        
        for fmt in date_formats:
            try:
                parsed = datetime.strptime(date_str.strip(), fmt)
                return parsed.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Return as-is if parsing fails
        if date_str.strip():
            return date_str.strip()
    
    # Try to extract date from filepath (e.g., news/286-new-publication...)
    # or from scraped comment
    return None


def extract_tags(soup, category):
    """Extract or infer tags from the content."""
    tags = []
    
    # Look for explicit tags
    tag_elements = soup.find_all('a', rel='tag') or \
                   soup.find_all(class_=re.compile(r'tag|label|category'))
    
    for elem in tag_elements:
        tag = elem.get_text(strip=True)
        if tag and tag not in tags:
            tags.append(tag)
    
    # Add category-based tags
    if category:
        parts = category.split('/')
        for part in parts:
            if part and part not in tags:
                tags.append(part)
    
    return tags


def extract_body(soup, category=None, output_dir=None):
    """Extract and convert body content to markdown."""
    converter = get_html_converter()
    
    # Find the main content area
    # Remove navigation, headers, footers, scripts, styles
    for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
        tag.decompose()
    
    # Remove breadcrumbs
    for elem in soup.find_all(class_=re.compile(r'breadcrumb')):
        elem.decompose()
    
    # Remove navigation menus
    for elem in soup.find_all(class_=re.compile(r'nav|menu')):
        elem.decompose()
    
    # Remove metadata sections (created date, modified date, etc.)
    for elem in soup.find_all('dl', class_='article-info'):
        elem.decompose()
    
    # Find the actual content
    content = soup.find('div', class_='item-page') or \
              soup.find('article') or \
              soup.find('div', class_='content') or \
              soup.find('main') or \
              soup
    
    # Fix image paths for MDX output
    if category is not None and output_dir is not None:
        fix_image_paths_in_html(content, category, output_dir)
    
    # Preserve <iframe> tags by replacing them with placeholders
    iframe_map = {}
    for iframe in content.find_all('iframe'):
        placeholder = f'IFRAME_PLACEHOLDER_{uuid.uuid4().hex}'
        iframe_map[placeholder] = str(iframe)
        iframe.replace_with(placeholder)

    # Convert to markdown
    html_content = str(content)
    markdown = converter.handle(html_content)

    # Restore <iframe> tags from placeholders
    for placeholder, iframe_html in iframe_map.items():
        markdown = markdown.replace(placeholder, f'\n\n{iframe_html}\n\n')

    # Clean up the markdown
    # Remove excessive newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)
    # Remove leading/trailing whitespace
    markdown = markdown.strip()
    
    return markdown


def is_article_page(filepath, category):
    """Determine if a page is an article (news, spotlight) vs a regular page."""
    article_indicators = ['news', 'spotlight', 'blog', 'article', 'post']
    
    filepath_lower = str(filepath).lower()
    category_lower = (category or '').lower()
    
    for indicator in article_indicators:
        if indicator in filepath_lower or indicator in category_lower:
            return True
    
    return False


def get_category_from_path(filepath, input_dir):
    """Extract category (route) from the file path."""
    rel_path = os.path.relpath(filepath, input_dir)
    # Remove filename and get directory path
    category = os.path.dirname(rel_path)
    # Normalize separators
    category = category.replace(os.sep, '/')
    return category


def convert_file(input_path, output_dir, input_dir):
    """Convert a single HTML file to MDX."""
    try:
        # Read the HTML file
        with open(input_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract metadata
        title = extract_title(soup)
        category = get_category_from_path(input_path, input_dir)
        
        # Copy images for this page
        copy_images_for_page(input_dir, output_dir, category)
        
        # Determine if this is an article or a page
        is_article = is_article_page(input_path, category)
        
        # Build frontmatter
        frontmatter_lines = ['---']
        frontmatter_lines.append(f'title: {escape_yaml_string(title)}')
        frontmatter_lines.append(f'category: {escape_yaml_string(category)}')
        
        if is_article:
            # Extract article-specific metadata
            author = extract_author(soup)
            date = extract_date(soup, input_path)
            tags = extract_tags(soup, category)
            
            if author:
                frontmatter_lines.append(f'author: {escape_yaml_string(author)}')
            if date:
                frontmatter_lines.append(f'date: {escape_yaml_string(date)}')
            if tags:
                tags_formatted = ', '.join(f'"{t}"' for t in tags)
                frontmatter_lines.append(f'tags: [{tags_formatted}]')
        
        frontmatter_lines.append('---')
        frontmatter = '\n'.join(frontmatter_lines)
        
        # Extract body content (with image path fixing)
        body = extract_body(soup, category, output_dir)
        
        # Combine into MDX
        mdx_content = f"{frontmatter}\n\n{body}\n"
        
        # Determine output path
        rel_path = os.path.relpath(input_path, input_dir)
        # Change extension to .mdx
        output_path = os.path.join(output_dir, rel_path)
        output_path = re.sub(r'\.html?$', '.mdx', output_path)
        
        # Create output directory
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Write MDX file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(mdx_content)
        
        logger.info(f"Converted: {input_path} -> {output_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error converting {input_path}: {e}")
        return False


def find_html_files(input_dir):
    """Find all HTML files in the input directory."""
    html_files = []
    for root, dirs, files in os.walk(input_dir):
        for file in files:
            if file.endswith(('.html', '.htm')):
                html_files.append(os.path.join(root, file))
    return html_files


def main():
    parser = argparse.ArgumentParser(description='Convert scraped HTML files to MDX')
    parser.add_argument('--input', '-i', default='scraped_pages',
                        help='Input directory containing HTML files')
    parser.add_argument('--output', '-o', default='mdx_pages',
                        help='Output directory for MDX files')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose logging')
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    input_dir = os.path.abspath(args.input)
    output_dir = os.path.abspath(args.output)
    
    if not os.path.exists(input_dir):
        logger.error(f"Input directory does not exist: {input_dir}")
        return 1
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all HTML files
    html_files = find_html_files(input_dir)
    logger.info(f"Found {len(html_files)} HTML files to convert")
    
    if not html_files:
        logger.warning("No HTML files found in input directory")
        return 0
    
    # Convert each file
    success_count = 0
    fail_count = 0
    
    for html_file in html_files:
        if convert_file(html_file, output_dir, input_dir):
            success_count += 1
        else:
            fail_count += 1
    
    logger.info(f"Conversion complete: {success_count} succeeded, {fail_count} failed")
    print(f"\nConversion complete!")
    print(f"Output directory: {output_dir}")
    print(f"Files converted: {success_count}")
    if fail_count > 0:
        print(f"Files failed: {fail_count}")
    
    return 0 if fail_count == 0 else 1


if __name__ == '__main__':
    exit(main())
