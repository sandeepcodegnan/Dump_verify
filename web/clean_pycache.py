#!/usr/bin/env python3
import os
import shutil

def remove_pycache(start_path='.'):
    for root, dirs, files in os.walk(start_path, topdown=False):
        if '__pycache__' in dirs:
            cache_dir = os.path.join(root, '__pycache__')
            try:
                shutil.rmtree(cache_dir)
                print(f"Removed: {cache_dir}")
            except Exception as e:
                print(f"Failed to remove {cache_dir}: {e}")

if __name__ == '__main__':
    remove_pycache()
