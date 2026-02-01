#!/usr/bin/env python3
"""End-to-end tests for rename_photos.py"""

import os
import shutil
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

# Import the module under test
import rename_photos


class TestFindImages(unittest.TestCase):
    """Tests for find_images function."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="snapsequence_test_"))

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_file(self, name: str, delay: float = 0.0) -> Path:
        """Create a test file with optional delay to ensure different timestamps."""
        if delay > 0:
            time.sleep(delay)
        file_path = self.test_dir / name
        file_path.write_bytes(b"test content")
        return file_path

    def test_finds_heic_files(self):
        """Should find .heic image files."""
        self._create_file("photo1.heic")
        self._create_file("photo2.HEIC")  # Test case insensitivity

        images = rename_photos.find_images(self.test_dir)

        self.assertEqual(len(images), 2)
        names = {img.name for img in images}
        self.assertIn("photo1.heic", names)
        self.assertIn("photo2.HEIC", names)

    def test_finds_jpg_files(self):
        """Should find .jpg and .jpeg image files."""
        self._create_file("photo1.jpg")
        self._create_file("photo2.jpeg")
        self._create_file("photo3.JPG")

        images = rename_photos.find_images(self.test_dir)

        self.assertEqual(len(images), 3)

    def test_finds_png_files(self):
        """Should find .png image files."""
        self._create_file("photo1.png")
        self._create_file("photo2.PNG")

        images = rename_photos.find_images(self.test_dir)

        self.assertEqual(len(images), 2)

    def test_ignores_non_image_files(self):
        """Should ignore non-image files."""
        self._create_file("photo.heic")
        self._create_file("document.txt")
        self._create_file("data.json")
        self._create_file("script.py")
        self._create_file("readme.md")

        images = rename_photos.find_images(self.test_dir)

        self.assertEqual(len(images), 1)
        self.assertEqual(images[0].name, "photo.heic")

    def test_empty_directory(self):
        """Should return empty list for empty directory."""
        images = rename_photos.find_images(self.test_dir)

        self.assertEqual(images, [])

    def test_directory_with_only_non_images(self):
        """Should return empty list when no image files exist."""
        self._create_file("document.txt")
        self._create_file("data.json")

        images = rename_photos.find_images(self.test_dir)

        self.assertEqual(images, [])

    def test_sorted_by_creation_date(self):
        """Should return images sorted by creation date (oldest first)."""
        # Create files in any order
        file1 = self._create_file("third.heic")
        file2 = self._create_file("first.heic")
        file3 = self._create_file("second.heic")

        # Mock get_creation_date to return controlled timestamps
        mock_dates = {
            file1: datetime(2024, 1, 1, 10, 0, 0),  # Oldest -> should be first
            file2: datetime(2024, 1, 1, 11, 0, 0),  # Middle -> should be second
            file3: datetime(2024, 1, 1, 12, 0, 0),  # Newest -> should be third
        }

        def mock_get_creation_date(path):
            return mock_dates[path]

        with patch.object(rename_photos, "get_creation_date", mock_get_creation_date):
            images = rename_photos.find_images(self.test_dir)

        # Verify order (oldest first)
        self.assertEqual(len(images), 3)
        names = [img.name for img in images]
        self.assertEqual(names, ["third.heic", "first.heic", "second.heic"])

    def test_mixed_file_types(self):
        """Should find all supported image types."""
        self._create_file("a.heic")
        self._create_file("b.jpg")
        self._create_file("c.jpeg")
        self._create_file("d.png")
        self._create_file("e.txt")  # Should be ignored

        images = rename_photos.find_images(self.test_dir)

        self.assertEqual(len(images), 4)
        extensions = {img.suffix.lower() for img in images}
        self.assertEqual(extensions, {".heic", ".jpg", ".jpeg", ".png"})


class TestGenerateNewNames(unittest.TestCase):
    """Tests for generate_new_names function."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="snapsequence_test_"))

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_file(self, name: str) -> Path:
        """Create a test file."""
        file_path = self.test_dir / name
        file_path.write_bytes(b"test")
        return file_path

    def test_sequential_numbering(self):
        """Should generate sequential numbers starting from 01."""
        images = [
            self._create_file("IMG_001.heic"),
            self._create_file("IMG_002.heic"),
            self._create_file("IMG_003.heic"),
        ]

        renames = rename_photos.generate_new_names(images)

        self.assertEqual(len(renames), 3)
        self.assertEqual(renames[0][1].name, "01.heic")
        self.assertEqual(renames[1][1].name, "02.heic")
        self.assertEqual(renames[2][1].name, "03.heic")

    def test_preserves_extension(self):
        """Should preserve original file extension (lowercased)."""
        images = [
            self._create_file("photo.HEIC"),
            self._create_file("image.JPG"),
            self._create_file("pic.PNG"),
        ]

        renames = rename_photos.generate_new_names(images)

        self.assertEqual(renames[0][1].name, "01.heic")
        self.assertEqual(renames[1][1].name, "02.jpg")
        self.assertEqual(renames[2][1].name, "03.png")

    def test_two_digit_padding(self):
        """Should pad numbers to two digits."""
        images = [self._create_file(f"img{i}.jpg") for i in range(1, 10)]

        renames = rename_photos.generate_new_names(images)

        self.assertEqual(renames[0][1].name, "01.jpg")
        self.assertEqual(renames[8][1].name, "09.jpg")

    def test_handles_more_than_nine_files(self):
        """Should handle more than 9 files correctly."""
        images = [self._create_file(f"img{i}.jpg") for i in range(1, 15)]

        renames = rename_photos.generate_new_names(images)

        self.assertEqual(renames[9][1].name, "10.jpg")
        self.assertEqual(renames[13][1].name, "14.jpg")

    def test_empty_list(self):
        """Should handle empty list."""
        renames = rename_photos.generate_new_names([])

        self.assertEqual(renames, [])

    def test_preserves_parent_directory(self):
        """Should keep files in the same directory."""
        images = [self._create_file("photo.heic")]

        renames = rename_photos.generate_new_names(images)

        self.assertEqual(renames[0][1].parent, self.test_dir)


class TestRenameFiles(unittest.TestCase):
    """Tests for rename_files function."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="snapsequence_test_"))

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_file(self, name: str, content: bytes = b"test") -> Path:
        """Create a test file with specific content."""
        file_path = self.test_dir / name
        file_path.write_bytes(content)
        return file_path

    def test_renames_files(self):
        """Should rename files to new names."""
        old1 = self._create_file("IMG_001.heic", b"content1")
        old2 = self._create_file("IMG_002.heic", b"content2")
        new1 = self.test_dir / "01.heic"
        new2 = self.test_dir / "02.heic"

        renames = [(old1, new1), (old2, new2)]
        count = rename_photos.rename_files(renames)

        self.assertEqual(count, 2)
        self.assertTrue(new1.exists())
        self.assertTrue(new2.exists())
        self.assertFalse(old1.exists())
        self.assertFalse(old2.exists())

    def test_preserves_content(self):
        """Should preserve file content after rename."""
        content = b"important photo data"
        old_path = self._create_file("original.heic", content)
        new_path = self.test_dir / "01.heic"

        rename_photos.rename_files([(old_path, new_path)])

        self.assertEqual(new_path.read_bytes(), content)

    def test_handles_name_conflicts(self):
        """Should handle case where new name already exists (via temp names)."""
        # Create files where renaming could conflict
        # e.g., 01.heic -> 02.heic, 02.heic -> 01.heic (swap)
        file1 = self._create_file("01.heic", b"first")
        file2 = self._create_file("02.heic", b"second")
        new1 = self.test_dir / "02.heic"
        new2 = self.test_dir / "01.heic"

        renames = [(file1, new1), (file2, new2)]
        count = rename_photos.rename_files(renames)

        self.assertEqual(count, 2)
        self.assertEqual((self.test_dir / "01.heic").read_bytes(), b"second")
        self.assertEqual((self.test_dir / "02.heic").read_bytes(), b"first")

    def test_returns_correct_count(self):
        """Should return correct count of renamed files."""
        files = [self._create_file(f"img{i}.jpg") for i in range(5)]
        renames = [(f, self.test_dir / f"{i+1:02d}.jpg") for i, f in enumerate(files)]

        count = rename_photos.rename_files(renames)

        self.assertEqual(count, 5)

    def test_empty_list(self):
        """Should handle empty rename list."""
        count = rename_photos.rename_files([])

        self.assertEqual(count, 0)


class TestEndToEnd(unittest.TestCase):
    """End-to-end integration tests."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="snapsequence_test_"))

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def _create_file(self, name: str, mtime_offset: float = 0) -> Path:
        """Create a test file with controlled modification time."""
        file_path = self.test_dir / name
        file_path.write_bytes(b"test image data")
        # Set modification time relative to now
        mtime = time.time() + mtime_offset
        os.utime(file_path, (mtime, mtime))
        return file_path

    def test_full_workflow_heic_files(self):
        """Test complete workflow with HEIC files."""
        # Create files with different timestamps (older files first)
        self._create_file("IMG_9999.heic", mtime_offset=-300)
        self._create_file("IMG_0001.heic", mtime_offset=-200)
        self._create_file("IMG_5555.heic", mtime_offset=-100)

        # Run the workflow
        images = rename_photos.find_images(self.test_dir)
        renames = rename_photos.generate_new_names(images)
        rename_photos.rename_files(renames)

        # Verify results
        expected_files = {"01.heic", "02.heic", "03.heic"}
        actual_files = {f.name for f in self.test_dir.iterdir()}
        self.assertEqual(actual_files, expected_files)

    def test_full_workflow_mixed_types(self):
        """Test complete workflow with mixed image types."""
        self._create_file("photo.heic")
        self._create_file("image.jpg")
        self._create_file("picture.png")
        self._create_file("snapshot.jpeg")

        images = rename_photos.find_images(self.test_dir)
        renames = rename_photos.generate_new_names(images)
        rename_photos.rename_files(renames)

        # Verify all files were renamed with sequential numbers
        actual_files = {f.name for f in self.test_dir.iterdir()}
        self.assertEqual(len(actual_files), 4)

        # Verify each original extension is preserved in some renamed file
        extensions = {f.suffix for f in self.test_dir.iterdir()}
        self.assertEqual(extensions, {".heic", ".jpg", ".png", ".jpeg"})

        # Verify sequential numbering
        stems = sorted(f.stem for f in self.test_dir.iterdir())
        self.assertEqual(stems, ["01", "02", "03", "04"])

    def test_full_workflow_preserves_non_images(self):
        """Test that non-image files are not affected."""
        self._create_file("photo.heic", mtime_offset=-200)
        self._create_file("readme.txt", mtime_offset=-100)

        images = rename_photos.find_images(self.test_dir)
        renames = rename_photos.generate_new_names(images)
        rename_photos.rename_files(renames)

        actual_files = {f.name for f in self.test_dir.iterdir()}
        self.assertIn("01.heic", actual_files)
        self.assertIn("readme.txt", actual_files)  # Untouched

    def test_files_sorted_by_date(self):
        """Verify files are renamed in order of creation date."""
        # Create files with any order
        file_c = self._create_file("C_last_alphabetically.heic")
        file_a = self._create_file("A_first_alphabetically.heic")
        file_b = self._create_file("B_middle_alphabetically.heic")

        # Mock get_creation_date to return controlled timestamps
        # C is oldest, A is middle, B is newest
        mock_dates = {
            file_c: datetime(2024, 1, 1, 10, 0, 0),  # Oldest
            file_a: datetime(2024, 1, 1, 11, 0, 0),  # Middle
            file_b: datetime(2024, 1, 1, 12, 0, 0),  # Newest
        }

        def mock_get_creation_date(path):
            return mock_dates[path]

        with patch.object(rename_photos, "get_creation_date", mock_get_creation_date):
            images = rename_photos.find_images(self.test_dir)
            renames = rename_photos.generate_new_names(images)

        # Verify sorting - oldest should become 01
        self.assertEqual(renames[0][0].name, "C_last_alphabetically.heic")
        self.assertEqual(renames[0][1].name, "01.heic")
        self.assertEqual(renames[1][0].name, "A_first_alphabetically.heic")
        self.assertEqual(renames[1][1].name, "02.heic")
        self.assertEqual(renames[2][0].name, "B_middle_alphabetically.heic")
        self.assertEqual(renames[2][1].name, "03.heic")


class TestMainFunction(unittest.TestCase):
    """Tests for the main() function."""

    def setUp(self):
        """Create a temporary directory for each test."""
        self.test_dir = Path(tempfile.mkdtemp(prefix="snapsequence_test_"))

    def tearDown(self):
        """Clean up the temporary directory after each test."""
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_nonexistent_folder_returns_error(self):
        """Should return 1 for nonexistent folder."""
        fake_path = self.test_dir / "does_not_exist"

        with patch("sys.argv", ["rename_photos.py", str(fake_path)]):
            result = rename_photos.main()

        self.assertEqual(result, 1)

    def test_file_instead_of_folder_returns_error(self):
        """Should return 1 when path is a file, not directory."""
        file_path = self.test_dir / "file.txt"
        file_path.write_bytes(b"test")

        with patch("sys.argv", ["rename_photos.py", str(file_path)]):
            result = rename_photos.main()

        self.assertEqual(result, 1)

    def test_empty_folder_returns_error(self):
        """Should return 1 for empty folder."""
        with patch("sys.argv", ["rename_photos.py", str(self.test_dir)]):
            result = rename_photos.main()

        self.assertEqual(result, 1)

    def test_no_images_returns_error(self):
        """Should return 1 when folder has no image files."""
        (self.test_dir / "readme.txt").write_bytes(b"test")

        with patch("sys.argv", ["rename_photos.py", str(self.test_dir)]):
            result = rename_photos.main()

        self.assertEqual(result, 1)

    def test_user_cancels_returns_zero(self):
        """Should return 0 when user cancels operation."""
        (self.test_dir / "photo.heic").write_bytes(b"test")

        with patch("sys.argv", ["rename_photos.py", str(self.test_dir)]):
            with patch("rename_photos.confirm_action", return_value=False):
                result = rename_photos.main()

        self.assertEqual(result, 0)
        # Original file should still exist
        self.assertTrue((self.test_dir / "photo.heic").exists())

    def test_successful_rename_returns_zero(self):
        """Should return 0 on successful rename."""
        (self.test_dir / "photo.heic").write_bytes(b"test")

        with patch("sys.argv", ["rename_photos.py", str(self.test_dir)]):
            with patch("rename_photos.confirm_action", return_value=True):
                result = rename_photos.main()

        self.assertEqual(result, 0)
        self.assertTrue((self.test_dir / "01.heic").exists())


if __name__ == "__main__":
    # Run with verbosity for better output
    unittest.main(verbosity=2)
