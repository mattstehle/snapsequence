#!/usr/bin/env python3
"""Rename photos in a folder sequentially (01.jpg, 02.jpg, etc.)."""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path


IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic'}


def get_creation_date(file_path: Path) -> datetime:
    """Get file creation date from filesystem metadata."""
    stat = file_path.stat()
    # Use st_birthtime on macOS/Windows if available
    if hasattr(stat, 'st_birthtime'):
        return datetime.fromtimestamp(stat.st_birthtime)
    # On Windows, st_ctime is creation time; on Unix it's metadata change time
    if os.name == 'nt':
        return datetime.fromtimestamp(stat.st_ctime)
    # Fallback to modification time on Unix
    return datetime.fromtimestamp(stat.st_mtime)


def find_images(folder: Path) -> list[Path]:
    """Find all image files in the folder, sorted by file creation date."""
    images = [
        f for f in folder.iterdir()
        if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(images, key=get_creation_date)


def generate_new_names(images: list[Path]) -> list[tuple[Path, Path]]:
    """Generate new sequential names for images, preserving extensions."""
    renames = []
    for i, image in enumerate(images, start=1):
        new_name = f"{i:02d}{image.suffix.lower()}"
        new_path = image.parent / new_name
        renames.append((image, new_path))
    return renames


def preview_renames(renames: list[tuple[Path, Path]]) -> None:
    """Display preview of old -> new names."""
    print("\nPreview of changes:")
    print("-" * 50)
    for old_path, new_path in renames:
        print(f"  {old_path.name} -> {new_path.name}")
    print("-" * 50)
    print(f"Total: {len(renames)} file(s) to rename\n")


def confirm_action() -> bool:
    """Ask user for confirmation."""
    while True:
        response = input("Proceed with rename? (y/n): ").strip().lower()
        if response in ('y', 'yes'):
            return True
        if response in ('n', 'no'):
            return False
        print("Please enter 'y' or 'n'")


def rename_files(renames: list[tuple[Path, Path]]) -> int:
    """Rename files and return count of successful renames."""
    # Use temporary names to avoid conflicts (e.g., 01.jpg already exists)
    temp_renames = []
    for old_path, new_path in renames:
        temp_path = old_path.parent / f"__temp_rename_{old_path.name}"
        temp_renames.append((old_path, temp_path, new_path))

    # First pass: rename to temp names
    for old_path, temp_path, _ in temp_renames:
        try:
            old_path.rename(temp_path)
        except PermissionError:
            print(f"Error: Permission denied for '{old_path.name}'")
            raise
        except OSError as e:
            print(f"Error renaming '{old_path.name}': {e}")
            raise

    # Second pass: rename to final names
    renamed_count = 0
    for _, temp_path, new_path in temp_renames:
        try:
            temp_path.rename(new_path)
            renamed_count += 1
        except PermissionError:
            print(f"Error: Permission denied for '{new_path.name}'")
            raise
        except OSError as e:
            print(f"Error renaming to '{new_path.name}': {e}")
            raise

    return renamed_count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rename photos in a folder sequentially (01.jpg, 02.jpg, etc.)"
    )
    parser.add_argument("folder", help="Path to folder containing images")
    args = parser.parse_args()

    folder = Path(args.folder)

    # Validate folder
    if not folder.exists():
        print(f"Error: Folder '{folder}' does not exist")
        return 1

    if not folder.is_dir():
        print(f"Error: '{folder}' is not a directory")
        return 1

    # Check if folder is empty
    try:
        contents = list(folder.iterdir())
    except PermissionError:
        print(f"Error: Permission denied accessing '{folder}'")
        return 1

    if not contents:
        print(f"Error: Folder '{folder}' is empty")
        return 1

    # Find images
    images = find_images(folder)

    if not images:
        print(f"Error: No image files found in '{folder}'")
        print(f"Supported formats: {', '.join(sorted(IMAGE_EXTENSIONS))}")
        return 1

    # Generate new names and preview
    renames = generate_new_names(images)
    preview_renames(renames)

    # Confirm and rename
    if not confirm_action():
        print("Operation cancelled")
        return 0

    try:
        count = rename_files(renames)
        print(f"\nSuccess! Renamed {count} file(s)")
        return 0
    except (PermissionError, OSError):
        print("\nRename operation failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
