#!/usr/bin/env python3
"""
Flatten folders that only contain a single file.
E.g., about/contact-us/item-page.mdx -> about/contact-us.mdx
"""

import os
import shutil

MDX_DIR = "mdx_pages"


def get_single_file_folders(base_dir):
    """Find all folders that contain exactly one file and no subdirectories."""
    single_file_folders = []
    
    for root, dirs, files in os.walk(base_dir, topdown=False):
        # Skip the base directory itself
        if root == base_dir:
            continue
        
        # Check if this folder has no subdirectories and exactly one file
        if len(dirs) == 0 and len(files) == 1:
            single_file_folders.append((root, files[0]))
    
    return single_file_folders


def flatten_folder(folder_path, filename):
    """Flatten a single-file folder into a file in its parent."""
    parent_dir = os.path.dirname(folder_path)
    folder_name = os.path.basename(folder_path)
    
    # Get the file extension from the original file
    _, ext = os.path.splitext(filename)
    
    # New file path: parent/folder_name.ext
    new_file_path = os.path.join(parent_dir, folder_name + ext)
    
    # Original file path
    old_file_path = os.path.join(folder_path, filename)
    
    # Check if destination already exists
    if os.path.exists(new_file_path):
        print(f"Skip (destination exists): {new_file_path}")
        return False
    
    # Move the file
    shutil.move(old_file_path, new_file_path)
    
    # Remove the now-empty folder
    os.rmdir(folder_path)
    
    print(f"Flattened: {old_file_path} -> {new_file_path}")
    return True


def main():
    flattened_count = 0
    
    # Keep flattening until no more single-file folders exist
    # (because flattening can create new single-file parent folders)
    while True:
        single_file_folders = get_single_file_folders(MDX_DIR)
        
        if not single_file_folders:
            break
        
        made_progress = False
        for folder_path, filename in single_file_folders:
            if flatten_folder(folder_path, filename):
                flattened_count += 1
                made_progress = True
        
        if not made_progress:
            break
    
    print(f"\nDone! Flattened {flattened_count} folders.")


if __name__ == '__main__':
    main()
