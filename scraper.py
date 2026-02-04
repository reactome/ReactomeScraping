#!/usr/bin/env python3
"""
Reactome.org Web Scraper

Scrapes reactome.org pages and saves:
- <div class="item-page"> elements
- <div class="leading-n" itemprop="blogpost"> elements

Files are organized in directories based on their URL routes.
"""

import os
import re
import time
import logging
import hashlib
from urllib.parse import urljoin, urlparse
from collections import deque

import requests
from bs4 import BeautifulSoup

# Configuration
BASE_URL = "https://reactome.org"
OUTPUT_DIR = "scraped_pages"
DELAY_BETWEEN_REQUESTS = 1.0  # seconds, be polite to the server
MAX_PAGES = 1000  # Set to a number to limit pages, None for unlimited
REQUEST_TIMEOUT = 30

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ReactomeScraper:
    def __init__(self, base_url=BASE_URL, output_dir=OUTPUT_DIR, delay=DELAY_BETWEEN_REQUESTS, max_pages=MAX_PAGES):
        self.base_url = base_url
        self.output_dir = output_dir
        self.delay = delay
        self.max_pages = max_pages
        self.visited_urls = set()
        self.downloaded_images = set()  # Track downloaded images to avoid duplicates
        self.urls_to_visit = deque()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; ReactomeScraper/1.0; Educational purposes)',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
        })
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
    
    def is_valid_url(self, url):
        """Check if URL should be scraped."""
        parsed = urlparse(url)
        
        # Only scrape URLs from reactome.org
        if parsed.netloc and parsed.netloc not in ['reactome.org', 'www.reactome.org']:
            return False
        
        # Skip non-HTML resources
        skip_extensions = ['.pdf', '.png', '.jpg', '.jpeg', '.gif', '.svg', 
                          '.css', '.js', '.zip', '.tar', '.gz', '.xml', '.json']
        path_lower = parsed.path.lower()
        if any(path_lower.endswith(ext) for ext in skip_extensions):
            return False
        
        # Skip API endpoints and special paths
        skip_paths = ['/ContentService', '/AnalysisService', '/PathwayBrowser', 
                      '/download', '/icon-lib', '/gsa']
        if any(parsed.path.startswith(skip) for skip in skip_paths):
            return False
        
        return True
    
    def normalize_url(self, url):
        """Normalize URL for deduplication."""
        parsed = urlparse(url)
        # Remove fragment and normalize
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        # Remove trailing slash for consistency
        return normalized.rstrip('/')
    
    def get_route_path(self, url):
        """Extract route path from URL for directory structure."""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            return 'index'
        
        return path
    
    def get_image_local_path(self, img_url, page_route):
        """
        Determine the local path for an image based on the page route.
        Images are stored in: scraped_pages/images/<page_route>/<filename>
        """
        parsed = urlparse(img_url)
        
        # Get the original filename
        original_filename = os.path.basename(parsed.path)
        if not original_filename:
            # Generate filename from URL hash
            url_hash = hashlib.md5(img_url.encode()).hexdigest()[:10]
            original_filename = f"image_{url_hash}.png"
        
        # Clean up the filename
        original_filename = re.sub(r'[^\w\-_\.]', '_', original_filename)
        
        # Build the path: images/<page_route>/<filename>
        image_dir = os.path.join(self.output_dir, 'images', page_route)
        local_path = os.path.join(image_dir, original_filename)
        
        return local_path, original_filename
    
    def download_image(self, img_url, page_route):
        """
        Download an image and save it locally.
        Returns the relative path to the image from the page's perspective.
        """
        # Normalize the image URL
        if img_url.startswith('//'):
            img_url = 'https:' + img_url
        
        # Skip data URLs
        if img_url.startswith('data:'):
            return None
        
        # Check if already downloaded
        if img_url in self.downloaded_images:
            local_path, filename = self.get_image_local_path(img_url, page_route)
            # Return relative path from page to image
            return os.path.join('images', page_route, filename)
        
        try:
            response = self.session.get(img_url, timeout=REQUEST_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Verify it's an image
            content_type = response.headers.get('Content-Type', '')
            if not any(t in content_type for t in ['image/', 'application/octet-stream']):
                logger.debug(f"Skipping non-image content: {img_url}")
                return None
            
            local_path, filename = self.get_image_local_path(img_url, page_route)
            
            # Create directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Write the image
            with open(local_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            self.downloaded_images.add(img_url)
            logger.info(f"Downloaded image: {img_url} -> {local_path}")
            
            # Return relative path from page to image
            return os.path.join('images', page_route, filename)
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to download image {img_url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error saving image {img_url}: {e}")
            return None
    
    def process_images_in_content(self, soup, current_url, page_route):
        """
        Find all images in the content, download them, and update src attributes.
        Returns the modified soup.
        """
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, src)
            
            # Download the image
            local_path = self.download_image(absolute_url, page_route)
            
            if local_path:
                # Update the src to point to local image
                # Path is relative from scraped_pages root
                img['src'] = local_path
                img['data-original-src'] = absolute_url  # Keep original for reference
        
        return soup
    
    def save_content(self, url, item_page_content, blog_post_content):
        """Save extracted content to files organized by route."""
        route_path = self.get_route_path(url)
        
        # Create directory structure
        dir_path = os.path.join(self.output_dir, os.path.dirname(route_path))
        if dir_path:
            os.makedirs(dir_path, exist_ok=True)
        
        base_filename = os.path.basename(route_path) or 'index'
        
        # Save item-page content
        if item_page_content:
            filepath = os.path.join(self.output_dir, route_path)
            if not filepath.endswith('.html'):
                # Create as directory with index.html
                os.makedirs(filepath, exist_ok=True)
                filepath = os.path.join(filepath, 'item-page.html')
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Source: {url} -->\n")
                f.write(f"<!-- Scraped: {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n")
                f.write(item_page_content)
            logger.info(f"Saved item-page: {filepath}")
        
        # Save blog post content
        if blog_post_content:
            filepath = os.path.join(self.output_dir, route_path)
            os.makedirs(filepath, exist_ok=True)
            
            for i, content in enumerate(blog_post_content):
                blog_filepath = os.path.join(filepath, f'blogpost-{i+1}.html')
                with open(blog_filepath, 'w', encoding='utf-8') as f:
                    f.write(f"<!-- Source: {url} -->\n")
                    f.write(f"<!-- Scraped: {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n")
                    f.write(content)
                logger.info(f"Saved blogpost: {blog_filepath}")
    
    def extract_content(self, soup, url):
        """Extract target div elements from the page."""
        item_page_content = None
        blog_post_content = []
        
        # Get page route for image organization
        page_route = self.get_route_path(url)
        
        # Find <div class="item-page">
        item_page = soup.find('div', class_='item-page')
        if item_page:
            # Process images in this content
            self.process_images_in_content(item_page, url, page_route)
            item_page_content = str(item_page)
            logger.debug(f"Found item-page in {url}")
        
        # Find <div class="leading-n" itemprop="blogpost">
        # The class might be "leading-0", "leading-1", etc.
        blog_posts = soup.find_all('div', attrs={'itemprop': 'blogPost'})
        if not blog_posts:
            # Try alternate case
            blog_posts = soup.find_all('div', attrs={'itemprop': 'blogpost'})
        
        # Also try finding by class pattern
        if not blog_posts:
            blog_posts = soup.find_all('div', class_=re.compile(r'^leading-\d+$'))
        
        for post in blog_posts:
            # Process images in this content
            self.process_images_in_content(post, url, page_route)
            blog_post_content.append(str(post))
            logger.debug(f"Found blogpost in {url}")
        
        return item_page_content, blog_post_content
    
    def extract_links(self, soup, current_url):
        """Extract all valid internal links from the page."""
        links = set()
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Skip empty, javascript, and mailto links
            if not href or href.startswith(('javascript:', 'mailto:', '#')):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)
            normalized_url = self.normalize_url(absolute_url)
            
            if self.is_valid_url(normalized_url):
                links.add(normalized_url)
        
        return links
    
    def scrape_page(self, url):
        """Scrape a single page."""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            
            # Check content type
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' not in content_type:
                logger.debug(f"Skipping non-HTML content: {url}")
                return set()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract and save content
            item_page_content, blog_post_content = self.extract_content(soup, url)
            
            if item_page_content or blog_post_content:
                self.save_content(url, item_page_content, blog_post_content)
            else:
                logger.debug(f"No target content found: {url}")
            
            # Extract links for crawling
            new_links = self.extract_links(soup, url)
            return new_links
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return set()
        except Exception as e:
            logger.error(f"Error processing {url}: {e}")
            return set()
    
    def crawl(self, start_urls=None):
        """Crawl the website starting from given URLs."""
        if start_urls is None:
            start_urls = [self.base_url]
        
        # Track URLs already queued to avoid duplicates in the queue
        queued_urls = set()
        
        # Initialize queue with start URLs
        for url in start_urls:
            normalized = self.normalize_url(url)
            if normalized not in self.visited_urls and normalized not in queued_urls:
                self.urls_to_visit.append(normalized)
                queued_urls.add(normalized)
        
        pages_scraped = 0
        
        while self.urls_to_visit:
            if self.max_pages and pages_scraped >= self.max_pages:
                logger.info(f"Reached maximum pages limit: {self.max_pages}")
                break
            
            url = self.urls_to_visit.popleft()
            
            if url in self.visited_urls:
                continue
            
            logger.info(f"Scraping ({pages_scraped + 1}): {url}")
            self.visited_urls.add(url)
            
            new_links = self.scrape_page(url)
            
            # Add new links to queue (only if not visited and not already queued)
            for link in new_links:
                if link not in self.visited_urls and link not in queued_urls:
                    self.urls_to_visit.append(link)
                    queued_urls.add(link)
            
            pages_scraped += 1
            
            # Be polite - wait between requests
            time.sleep(self.delay)
        
        logger.info(f"Crawling complete. Total pages scraped: {pages_scraped}")
        return pages_scraped


def get_seed_urls():
    """Get initial URLs to start crawling from the navigation structure."""
    return [
        "https://reactome.org",
        "https://reactome.org/what-is-reactome",
        "https://reactome.org/about/news",
        "https://reactome.org/about/team",
        "https://reactome.org/sab",
        "https://reactome.org/about/funding",
        "https://reactome.org/about/editorial-calendar",
        "https://reactome.org/about/release-calendar",
        "https://reactome.org/about/statistics",
        "https://reactome.org/about/logo",
        "https://reactome.org/license",
        "https://reactome.org/about/privacy-notice",
        "https://reactome.org/about/disclaimer",
        "https://reactome.org/about/digital-preservation",
        "https://reactome.org/staff",
        "https://reactome.org/about/contact-us",
        "https://reactome.org/content/toc",
        "https://reactome.org/content/doi",
        "https://reactome.org/content/schema",
        "https://reactome.org/content/reactome-research-spotlight",
        "https://reactome.org/orcid",
        "https://reactome.org/covid-19",
        "https://reactome.org/documentation",
        "https://reactome.org/userguide",
        "https://reactome.org/userguide/pathway-browser",
        "https://reactome.org/userguide/searching",
        "https://reactome.org/userguide/details-panel",
        "https://reactome.org/userguide/analysis",
        "https://reactome.org/userguide/diseases",
        "https://reactome.org/userguide/cytomics",
        "https://reactome.org/userguide/review-status",
        "https://reactome.org/userguide/reactome-fiviz",
        "https://reactome.org/dev",
        "https://reactome.org/dev/graph-database",
        "https://reactome.org/dev/analysis",
        "https://reactome.org/dev/content-service",
        "https://reactome.org/dev/pathways-overview",
        "https://reactome.org/dev/diagram",
        "https://reactome.org/icon-info",
        "https://reactome.org/icon-info/ehld-specs-guideline",
        "https://reactome.org/icon-info/icons-guidelines",
        "https://reactome.org/documentation/data-model",
        "https://reactome.org/documentation/curator-guide",
        "https://reactome.org/documentation/release-documentation",
        "https://reactome.org/documentation/inferred-events",
        "https://reactome.org/documentation/faq",
        "https://reactome.org/linking-to-us",
        "https://reactome.org/cite",
        "https://reactome.org/tools/reactome-fiviz",
        "https://reactome.org/tools/site-search",
        "https://reactome.org/community",
        "https://reactome.org/community/collaboration",
        "https://reactome.org/community/outreach",
        "https://reactome.org/community/events",
        "https://reactome.org/community/publications",
        "https://reactome.org/community/partners",
        "https://reactome.org/content/contributors",
        "https://reactome.org/community/resources",
    ]


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape reactome.org pages')
    parser.add_argument('--output', '-o', default=OUTPUT_DIR,
                        help='Output directory for scraped pages')
    parser.add_argument('--delay', '-d', type=float, default=1.0,
                        help='Delay between requests in seconds')
    parser.add_argument('--max-pages', '-m', type=int, default=None,
                        help='Maximum number of pages to scrape')
    parser.add_argument('--seed-only', '-s', action='store_true',
                        help='Only scrape seed URLs, do not crawl further')
    args = parser.parse_args()
    
    delay = args.delay
    max_pages = args.max_pages
    
    scraper = ReactomeScraper(output_dir=args.output, delay=delay, max_pages=max_pages)
    
    seed_urls = get_seed_urls()
    
    if args.seed_only:
        # Only scrape the seed URLs
        for url in seed_urls:
            if url not in scraper.visited_urls:
                logger.info(f"Scraping: {url}")
                scraper.visited_urls.add(url)
                scraper.scrape_page(url)
                time.sleep(scraper.delay)
    else:
        # Full crawl
        scraper.crawl(seed_urls)
    
    print(f"\nScraping complete!")
    print(f"Output directory: {os.path.abspath(args.output)}")
    print(f"Total pages visited: {len(scraper.visited_urls)}")


if __name__ == '__main__':
    main()
