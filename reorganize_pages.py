#!/usr/bin/env python3
"""
Reorganize mdx_pages to match the nav structure.
"""

import os
import shutil

MDX_DIR = "mdx_pages"

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


def main():
    for src_rel, dst_rel in MOVES:
        src = os.path.join(MDX_DIR, src_rel)
        dst = os.path.join(MDX_DIR, dst_rel)
        
        if not os.path.exists(src):
            print(f"Skip (not found): {src}")
            continue
        
        if os.path.exists(dst):
            print(f"Skip (destination exists): {dst}")
            continue
        
        # Create parent directory if needed
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        
        # Move
        shutil.move(src, dst)
        print(f"Moved: {src} -> {dst}")
    
    print("\nDone!")


if __name__ == '__main__':
    main()
