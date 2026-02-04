#!/usr/bin/env python3
"""
Rename all item-page.mdx files to index.mdx.
This provides cleaner URLs for static site generators.
"""

import os
from pathlib import Path

MDX_DIR = Path("mdx_pages")

def rename_item_pages():
    """Rename all item-page.mdx files to index.mdx."""
    count = 0
    
    for root, dirs, files in os.walk(MDX_DIR):
        for f in files:
            if f == "item-page.mdx":
                old_path = Path(root) / f
                new_path = Path(root) / "index.mdx"
                
                if new_path.exists():
                    print(f"Skipped (index.mdx already exists): {old_path}")
                    continue
                
                old_path.rename(new_path)
                print(f"Renamed: {old_path} -> {new_path}")
                count += 1
    
    return count

def main():
    print("Renaming item-page.mdx files to index.mdx...")
    count = rename_item_pages()
    print(f"\nDone! Renamed {count} files.")

if __name__ == "__main__":
    main()
