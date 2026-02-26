#!/usr/bin/env python3
"""
Fix image path mismatches in scraped HTML files.

The scraper had a bug where when the same image URL was downloaded by multiple pages,
each page got a different relative path written into the HTML, but the image was only 
saved once at the first location.

This script:
1. Finds all image references in HTML files
2. Checks if the referenced image exists
3. If not, searches for the image by filename in the uploads directory
4. Either creates a copy/symlink or updates the HTML to point to the correct location
"""

import os
import re
import shutil
from pathlib import Path


def find_all_uploads(uploads_dir):
    """Build a dictionary mapping filenames to their full paths."""
    uploads = {}
    for root, dirs, files in os.walk(uploads_dir):
        for f in files:
            full_path = os.path.join(root, f)
            if f not in uploads:
                uploads[f] = []
            uploads[f].append(full_path)
    return uploads


def find_image_references(scraped_dir):
    """Find all image src references in HTML files."""
    references = []
    for root, dirs, files in os.walk(scraped_dir):
        for f in files:
            if f.endswith('.html'):
                html_path = os.path.join(root, f)
                with open(html_path, 'r', encoding='utf-8') as fp:
                    content = fp.read()
                
                # Find all image src attributes
                for match in re.finditer(r'src="(uploads/[^"]+)"', content):
                    img_path = match.group(1)
                    references.append({
                        'html_file': html_path,
                        'img_ref': img_path,
                        'full_expected_path': os.path.join(scraped_dir, img_path)
                    })
    return references


def fix_uploads(scraped_dir='scraped_pages', mode='copy'):
    """
    Fix missing image references.
    
    mode: 'copy' - copy uploads to expected locations
          'symlink' - create symlinks
          'update_html' - update HTML to point to existing uploads
    """
    uploads_dir = os.path.join(scraped_dir, 'uploads')
    
    # Build image index
    print("Building image index...")
    all_uploads = find_all_uploads(uploads_dir)
    print(f"Found {len(all_uploads)} unique image filenames")
    
    # Find all references
    print("Finding image references in HTML...")
    references = find_image_references(scraped_dir)
    print(f"Found {len(references)} image references")
    
    # Find missing uploads
    missing = []
    for ref in references:
        if not os.path.exists(ref['full_expected_path']):
            missing.append(ref)
    
    print(f"Found {len(missing)} missing image references")
    
    if not missing:
        print("All uploads are correctly placed!")
        return
    
    # Fix missing uploads
    fixed = 0
    not_found = []
    
    for ref in missing:
        filename = os.path.basename(ref['img_ref'])
        
        if filename not in all_uploads:
            not_found.append(ref)
            continue
        
        # Get the source image path
        source_path = all_uploads[filename][0]  # Use first occurrence
        target_path = ref['full_expected_path']
        
        if mode == 'copy':
            # Create directory if needed
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            shutil.copy2(source_path, target_path)
            print(f"Copied: {source_path} -> {target_path}")
            fixed += 1
        
        elif mode == 'symlink':
            # Create directory if needed
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            # Calculate relative path for symlink
            rel_path = os.path.relpath(source_path, os.path.dirname(target_path))
            os.symlink(rel_path, target_path)
            print(f"Linked: {target_path} -> {rel_path}")
            fixed += 1
        
        elif mode == 'update_html':
            # Update the HTML file to point to the correct image
            html_path = ref['html_file']
            with open(html_path, 'r', encoding='utf-8') as fp:
                content = fp.read()
            
            # Calculate the correct relative path
            correct_rel = os.path.relpath(source_path, scraped_dir)
            old_ref = ref['img_ref']
            content = content.replace(f'src="{old_ref}"', f'src="{correct_rel}"')
            
            with open(html_path, 'w', encoding='utf-8') as fp:
                fp.write(content)
            print(f"Updated: {html_path} ({old_ref} -> {correct_rel})")
            fixed += 1
    
    print(f"\nFixed {fixed} missing image references")
    
    if not_found:
        print(f"\n{len(not_found)} uploads could not be found:")
        for ref in not_found[:10]:  # Show first 10
            print(f"  - {ref['img_ref']} (referenced in {os.path.basename(ref['html_file'])})")
        if len(not_found) > 10:
            print(f"  ... and {len(not_found) - 10} more")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Fix image path mismatches')
    parser.add_argument('--mode', choices=['copy', 'symlink', 'update_html'], 
                        default='copy', help='How to fix: copy uploads, create symlinks, or update HTML')
    parser.add_argument('--input', '-i', default='scraped_pages',
                        help='Input directory containing scraped HTML files')
    args = parser.parse_args()
    
    fix_uploads(args.input, args.mode)
