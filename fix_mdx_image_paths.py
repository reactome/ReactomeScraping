#!/usr/bin/env python3
"""
Fix image paths in MDX files to match the actual image locations after flattening.
Handles:
1. Malformed image references (trailing >)
2. Flattened folder paths (folder/subfolder/image.png -> folder/subfolder.png)
3. General path mismatches
"""

import os
import re
from pathlib import Path

MDX_DIR = Path("mdx_pages")
uploads_DIR = MDX_DIR / "uploads"

def build_image_index():
    """Build an index of all uploads by filename and also by parent folder name."""
    image_index = {}
    path_index = {}  # Full path -> relative path mapping
    
    for root, dirs, files in os.walk(uploads_DIR):
        for f in files:
            if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.emf')):
                full_path = Path(root) / f
                rel_path = str(full_path.relative_to(MDX_DIR))
                
                # Store by filename
                if f not in image_index:
                    image_index[f] = []
                image_index[f].append(rel_path)
                
                # Also store the full relative path
                path_index['/' + rel_path] = rel_path
                
                # If this looks like a flattened file (parent-folder.ext),
                # also map the original nested path
                stem = Path(f).stem
                parent = Path(root).name
                if stem == parent or stem.replace('-', '_') == parent.replace('-', '_'):
                    # This might be a flattened file
                    # e.g., uploads/documentation/inferred-events.png was uploads/documentation/inferred-events/something.png
                    pass
    
    return image_index, path_index

def find_best_match(old_path, image_index, path_index):
    """Find the best matching image for an old path."""
    # First, check if the path exists as-is
    if old_path in path_index:
        return '/' + path_index[old_path]
    
    # Extract the filename
    filename = os.path.basename(old_path)
    
    # Check direct filename match
    if filename in image_index:
        candidates = image_index[filename]
        if len(candidates) == 1:
            return '/' + candidates[0]
        
        # Multiple candidates - score by path similarity
        old_parts = set(old_path.lower().split('/'))
        best_match = candidates[0]
        best_score = 0
        for candidate in candidates:
            cand_parts = set(candidate.lower().split('/'))
            score = len(old_parts & cand_parts)
            if score > best_score:
                best_score = score
                best_match = candidate
        return '/' + best_match
    
    # Check if this is a flattened path
    # e.g., /uploads/documentation/inferred-events/reaction_release_stats.png
    # -> /uploads/documentation/inferred-events.png
    parts = old_path.split('/')
    if len(parts) >= 4:  # /uploads/category/folder/file.png
        # Try the folder name as the filename
        folder_name = parts[-2]  # The folder containing the file
        ext = Path(filename).suffix
        flattened_name = folder_name + ext
        
        if flattened_name in image_index:
            candidates = image_index[flattened_name]
            if len(candidates) == 1:
                return '/' + candidates[0]
            # Find best match by path
            old_parts = set(old_path.lower().split('/'))
            best_match = candidates[0]
            best_score = 0
            for candidate in candidates:
                cand_parts = set(candidate.lower().split('/'))
                score = len(old_parts & cand_parts)
                if score > best_score:
                    best_score = score
                    best_match = candidate
            return '/' + best_match
    
    return None

def fix_image_paths_in_file(mdx_file, image_index, path_index):
    """Fix image paths in a single MDX file."""
    with open(mdx_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Fix malformed image references with trailing >
    content = re.sub(r'\]\(([^)]+\.(?:png|jpg|jpeg|gif|svg|webp|emf))>\)', r'](\1)', content, flags=re.IGNORECASE)
    content = re.sub(r'src="([^"]+\.(?:png|jpg|jpeg|gif|svg|webp|emf))>"', r'src="\1"', content, flags=re.IGNORECASE)
    
    def fix_md_image(match):
        alt = match.group(1)
        old_path = match.group(2)
        
        # Check if image exists at the referenced path
        check_path = MDX_DIR / old_path.lstrip('/')
        if check_path.exists():
            return match.group(0)  # Path is valid, keep it
        
        new_path = find_best_match(old_path, image_index, path_index)
        if new_path:
            return f'![{alt}]({new_path})'
        
        return match.group(0)
    
    def fix_html_src(match):
        old_path = match.group(1)
        
        check_path = MDX_DIR / old_path.lstrip('/')
        if check_path.exists():
            return match.group(0)
        
        new_path = find_best_match(old_path, image_index, path_index)
        if new_path:
            return f'src="{new_path}"'
        
        return match.group(0)
    
    # Pattern for markdown uploads
    content = re.sub(r'!\[([^\]]*)\]\((/uploads/[^)]+)\)', fix_md_image, content)
    # Pattern for HTML img tags
    content = re.sub(r'src="(/uploads/[^"]+)"', fix_html_src, content)
    
    if content != original_content:
        with open(mdx_file, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    print("Building image index...")
    image_index, path_index = build_image_index()
    print(f"Found {len(image_index)} unique image filenames")
    print(f"Total image paths: {len(path_index)}")
    
    print("\nFixing image paths in MDX files...")
    fixed_count = 0
    checked_count = 0
    
    for root, dirs, files in os.walk(MDX_DIR):
        for f in files:
            if f.endswith('.mdx'):
                mdx_file = Path(root) / f
                checked_count += 1
                if fix_image_paths_in_file(mdx_file, image_index, path_index):
                    print(f"Fixed: {mdx_file}")
                    fixed_count += 1
    
    print(f"\nDone! Checked {checked_count} MDX files, fixed {fixed_count}")
    
    # Report still missing uploads
    print("\nChecking for still-missing image references...")
    missing = set()
    for root, dirs, files in os.walk(MDX_DIR):
        for f in files:
            if f.endswith('.mdx'):
                mdx_file = Path(root) / f
                with open(mdx_file, 'r') as mf:
                    content = mf.read()
                # Find all image paths
                for match in re.finditer(r'/uploads/[^)"\'>\s]+', content):
                    path = match.group(0)
                    check_path = MDX_DIR / path.lstrip('/')
                    if not check_path.exists():
                        missing.add(path)
    
    if missing:
        print(f"\nStill missing {len(missing)} image references:")
        for m in sorted(missing)[:20]:
            print(f"  {m}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
    else:
        print("All image references are valid!")

if __name__ == "__main__":
    main()
