import os
import shutil
import unittest

from phaser_agent.tools.filesystem import edit_file, write_file, read_file


class TestFilesystemEditFile(unittest.TestCase):
    def setUp(self) -> None:
        self.project_id = "testproj_filesystem_edit"
        self.project_root = os.path.join("workspaces", self.project_id)
        os.makedirs(self.project_root, exist_ok=True)

    def tearDown(self) -> None:
        if os.path.isdir(self.project_root):
            shutil.rmtree(self.project_root, ignore_errors=True)

    def test_line_range_edit(self) -> None:
        write_file(self.project_id, "a.txt", "l1\nl2\nl3\nl4\n")
        res = edit_file(self.project_id, "a.txt", "L2-L3\nX\nY")
        self.assertEqual(res["status"], "success")
        out = read_file(self.project_id, "a.txt")["content"]
        self.assertEqual(out, "l1\nX\nY\nl4\n")

    def test_unified_diff_single_hunk_with_headers(self) -> None:
        write_file(self.project_id, "b.txt", "hello\nworld\nend\n")
        patch = "\n".join(
            [
                "--- a/b.txt",
                "+++ b/b.txt",
                "@@ -1,3 +1,3 @@",
                "-hello",
                "+HELLO",
                " world",
                " end",
                "",
            ]
        )
        res = edit_file(self.project_id, "b.txt", patch)
        self.assertEqual(res["status"], "success")
        out = read_file(self.project_id, "b.txt")["content"]
        self.assertEqual(out, "HELLO\nworld\nend\n")

    def test_unified_diff_multi_hunk(self) -> None:
        write_file(self.project_id, "c.txt", "a\nb\nc\nd\ne\nf\n")
        patch = "\n".join(
            [
                "--- a/c.txt",
                "+++ b/c.txt",
                "@@ -1,3 +1,3 @@",
                " a",
                "-b",
                "+B",
                " c",
                "@@ -4,3 +4,3 @@",
                " d",
                "-e",
                "+E",
                " f",
                "",
            ]
        )
        res = edit_file(self.project_id, "c.txt", patch)
        self.assertEqual(res["status"], "success")
        out = read_file(self.project_id, "c.txt")["content"]
        self.assertEqual(out, "a\nB\nc\nd\nE\nf\n")

    def test_unified_diff_without_headers(self) -> None:
        write_file(self.project_id, "d.txt", "one\ntwo\nthree\n")
        patch = "\n".join(
            [
                "@@ -2,1 +2,1 @@",
                "-two",
                "+TWO",
                "",
            ]
        )
        res = edit_file(self.project_id, "d.txt", patch)
        self.assertEqual(res["status"], "success")
        out = read_file(self.project_id, "d.txt")["content"]
        self.assertEqual(out, "one\nTWO\nthree\n")

    def test_invalid_patch_rejected(self) -> None:
        write_file(self.project_id, "e.txt", "x = 1\ny = 2\n")
        res = edit_file(self.project_id, "e.txt", "x = 1\ny = 2")
        self.assertEqual(res["status"], "error")


if __name__ == "__main__":
    unittest.main()
