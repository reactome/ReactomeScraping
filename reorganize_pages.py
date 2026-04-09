#!/usr/bin/env python3
"""
Reorganize mdx_pages to match the nav structure.
Also handles moving corresponding uploads from the uploads directory.
"""

import os
import re
import shutil

MDX_DIR = "mdx_pages"
uploads_DIR = os.path.join(MDX_DIR, "uploads")

# Define moves: (source, destination)
# Paths are relative to MDX_DIR
MOVES = [
    # === ABOUT ===
    # what-is-reactome -> about/what-is-reactome
    ("what-is-reactome", "about/what-is-reactome"),
    # sab -> about/sab
    ("sab", "about/sab"),
    # license -> about/license
    ("license", "about/license"),
    
    # === CONTENT ===
    # orcid -> content/orcid
    ("orcid", "content/orcid"),
    # covid-19 -> content/covid-19
    ("covid-19", "content/covid-19"),
    
    # === DOCUMENTATION ===
    # userguide -> documentation/userguide
    ("userguide", "documentation/userguide"),
    # dev -> documentation/dev
    ("dev", "documentation/dev"),
    # icon-info -> documentation/icon-info
    ("icon-info", "documentation/icon-info"),
    # linking-to-us -> documentation/linking-to-us
    ("linking-to-us", "documentation/linking-to-us"),
    # cite -> documentation/cite
    ("cite", "documentation/cite"),
    # user/guide -> documentation/userguide (merge with existing after move)
    ("user", "documentation/user"),
]


def move_uploads(src_rel, dst_rel):
    """Move uploads from old location to new location to match page reorganization."""
    src_uploads = os.path.join(uploads_DIR, src_rel)
    dst_uploads = os.path.join(uploads_DIR, dst_rel)
    
    if not os.path.exists(src_uploads):
        return False
    
    if os.path.exists(dst_uploads):
        print(f"Skip uploads (destination exists): {dst_uploads}")
        return False
    
    # Create parent directory if needed
    os.makedirs(os.path.dirname(dst_uploads), exist_ok=True)
    
    # Move the uploads directory
    shutil.move(src_uploads, dst_uploads)
    print(f"Moved uploads: {src_uploads} -> {dst_uploads}")
    return True


def update_image_paths_in_mdx(dst_path, src_rel, dst_rel):
    """
    Update image paths in MDX files after reorganization.
    Image paths change from /uploads/<src_rel>/... to /uploads/<dst_rel>/...
    """
    if not os.path.exists(dst_path):
        return
    
    # Process all MDX files in the destination
    for root, dirs, files in os.walk(dst_path):
        for filename in files:
            if not filename.endswith('.mdx'):
                continue
            
            filepath = os.path.join(root, filename)
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace image paths: /uploads/<src_rel>/ -> /uploads/<dst_rel>/
                old_path = f'/uploads/{src_rel}/'
                new_path = f'/uploads/{dst_rel}/'
                
                if old_path in content:
                    updated_content = content.replace(old_path, new_path)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    print(f"Updated image paths in: {filepath}")
            except Exception as e:
                print(f"Error updating {filepath}: {e}")


def main():
    for src_rel, dst_rel in MOVES:
        src = os.path.join(MDX_DIR, src_rel)
        dst = os.path.join(MDX_DIR, dst_rel)
        
        if not os.path.exists(src):
            print(f"Skip (not found): {src}")
            # Still try to move uploads even if pages don't exist
            move_uploads(src_rel, dst_rel)
            continue
        
        if os.path.exists(dst):
            print(f"Skip (destination exists): {dst}")
            continue
        
        # Create parent directory if needed
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        # Move pages
        shutil.move(src, dst)
        print(f"Moved: {src} -> {dst}")
        
        # Move corresponding uploads
        move_uploads(src_rel, dst_rel)
        
        # Update image paths in the moved MDX files
        update_image_paths_in_mdx(dst, src_rel, dst_rel)
    
    print("\nDone!")


if __name__ == '__main__':
    main()
