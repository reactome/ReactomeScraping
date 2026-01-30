#!/usr/bin/env python3
"""
Fix categories in MDX files to be one of the allowed values:
about, content, documentation, tools, community, download
"""

import os
import re

MDX_DIR = "mdx_pages"

# Map path prefixes to allowed categories
CATEGORY_MAP = {
    "about": "about",
    "cite": "about",
    "license": "about",
    "sab": "about",
    "what-is-reactome": "about",
    "orcid": "about",
    
    "content": "content",
    "covid-19": "content",
    
    "documentation": "documentation",
    "dev": "documentation",
    "icon-info": "documentation",
    "linking-to-us": "documentation",
    "user": "documentation",
    "userguide": "documentation",
    
    "tools": "tools",
    
    "community": "community",
    
    "download": "download",
}


def get_allowed_category(filepath):
    """Determine the allowed category based on file path."""
    rel_path = os.path.relpath(filepath, MDX_DIR)
    # Get the first directory component
    first_dir = rel_path.split(os.sep)[0]
    
    return CATEGORY_MAP.get(first_dir, "content")


def fix_category(filepath):
    """Fix the category in a single MDX file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find and replace the category line
    allowed_category = get_allowed_category(filepath)
    
    # Match the category line in frontmatter
    pattern = r'^(category:\s*)["\']?[^"\'\n]+["\']?\s*$'
    replacement = f'category: "{allowed_category}"'
    
    new_content = re.sub(pattern, replacement, content, count=1, flags=re.MULTILINE)
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False


def main():
    fixed_count = 0
    total_count = 0
    
    for root, dirs, files in os.walk(MDX_DIR):
        for file in files:
            if file.endswith('.mdx'):
                filepath = os.path.join(root, file)
                total_count += 1
                if fix_category(filepath):
                    fixed_count += 1
                    print(f"Fixed: {filepath}")
    
    print(f"\nDone! Fixed {fixed_count}/{total_count} files.")


if __name__ == '__main__':
    main()
