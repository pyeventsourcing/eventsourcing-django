# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
from pathlib import Path
from subprocess import PIPE, Popen
from tempfile import NamedTemporaryFile

from tests.test_recorders import DjangoTestCase

BASE_DIR = Path(__file__).parents[1]


class TestDocs(DjangoTestCase):
    databases = {"default", "postgres"}

    def setUp(self) -> None:
        super().setUp()
        self.original_django_settings_module = os.environ["DJANGO_SETTINGS_MODULE"]
        os.environ["DJANGO_SETTINGS_MODULE"] = "tests.djangoproject.settings_testdocs"

    def tearDown(self) -> None:
        self.clean_env()
        os.environ["DJANGO_SETTINGS_MODULE"] = self.original_django_settings_module

    def clean_env(self) -> None:
        keys = [
            "PERSISTENCE_MODULE",
            "COMPRESSOR_TOPIC",
        ]
        for key in keys:
            try:
                del os.environ[key]
            except KeyError:
                pass

    def test_readme(self) -> None:
        self._out = ""

        path = BASE_DIR / "README.md"
        if not path.exists():
            self.fail(f"README file not found: {path}")
        self.check_code_snippets_in_file(path)

    def check_code_snippets_in_file(self, doc_path: Path) -> None:  # noqa: C901
        # Extract lines of Python code from the README.md file.

        lines = []
        num_code_lines = 0
        num_code_lines_in_block = 0
        is_code = False
        is_md = False
        is_rst = False
        last_line = ""
        is_literalinclude = False
        with doc_path.open() as doc_file:
            for line_index, orig_line in enumerate(doc_file):
                line = orig_line.strip("\n")
                if line.startswith("```python"):
                    # Start markdown code block.
                    if is_rst:
                        self.fail(
                            "Markdown code block found after restructured text block "
                            "in same file."
                        )
                    is_code = True
                    is_md = True
                    line = ""
                    num_code_lines_in_block = 0
                elif is_code and is_md and line.startswith("```"):
                    # Finish markdown code block.
                    if not num_code_lines_in_block:
                        self.fail(f"No lines of code in block: {line_index + 1}")
                    is_code = False
                    line = ""
                elif is_code and is_rst and line.startswith("```"):
                    # Can't finish restructured text block with markdown.
                    self.fail(
                        "Restructured text block terminated with markdown format '```'"
                    )
                elif (
                    line.startswith(".. code:: python")
                    or line.strip() == ".."
                    # and "exclude-when-testing" not in last_line
                ):
                    # Start restructured text code block.
                    if is_md:
                        self.fail(
                            "Restructured text code block found after markdown block "
                            "in same file."
                        )
                    is_code = True
                    is_rst = True
                    line = ""
                    num_code_lines_in_block = 0
                elif line.startswith(".. literalinclude::"):
                    is_literalinclude = True
                    line = ""

                elif is_literalinclude:
                    if "pyobject" in line:
                        # Assume ".. literalinclude:: ../../xxx/xx.py"
                        # Or ".. literalinclude:: ../xxx/xx.py"
                        module = last_line.strip().split(" ")[-1][:-3]
                        module = module.lstrip("./")
                        module = module.replace("/", ".")
                        # Assume "    :pyobject: xxxxxx"
                        pyobject = line.strip().split(" ")[-1]
                        statement = f"from {module} import {pyobject}"
                        line = statement
                        is_literalinclude = False

                elif is_code and is_rst and line and not line.startswith(" "):
                    # Finish restructured text code block.
                    if not num_code_lines_in_block:
                        self.fail(f"No lines of code in block: {line_index + 1}")
                    is_code = False
                    line = ""
                elif is_code:
                    # Process line in code block.
                    if is_rst:
                        # Restructured code block normally indented with four spaces.
                        if len(line.strip()):
                            if not line.startswith("    "):
                                self.fail(
                                    f"Code line needs 4-char indent: {repr(line)}: "
                                    f"{doc_path}"
                                )
                            # Strip four chars of indentation.
                            line = line[4:]

                    if len(line.strip()):
                        num_code_lines_in_block += 1
                        num_code_lines += 1
                else:
                    line = ""
                lines.append(line)
                last_line = orig_line

        print(f"{num_code_lines} lines of code in {doc_path}")

        self.assertEqual("", lines[0])
        self.assertEqual("", lines[1])
        lines[0] = "import django"
        lines[1] = "django.setup()"

        # Write the code into a temp file.
        tempfile = NamedTemporaryFile("w+")
        source = "\n".join(lines) + "\n"
        tempfile.writelines(source)
        tempfile.flush()

        # exec(
        #     compile(source=source, filename=doc_path, mode="exec"), globals(), globals()
        # )
        # return

        # print(Path.cwd())
        # print("\n".join(lines) + "\n")
        #
        # Run the code and catch errors.
        # - need to run this in a subprocess so we can django.setup() with alternative settings
        env = os.environ.copy()
        env["PYTHONPATH"] = str(BASE_DIR)
        p = Popen(
            [sys.executable, tempfile.name],
            stdout=PIPE,
            stderr=PIPE,
            env=env,
            # cwd=BASE_DIR,
        )
        print(sys.executable, tempfile.name, PIPE)
        out, err = p.communicate()
        decoded_out = out.decode("utf8").replace(tempfile.name, str(doc_path))
        decoded_err = err.decode("utf8").replace(tempfile.name, str(doc_path))
        exit_status = p.wait()

        print(decoded_out)
        print(decoded_err)

        # Check for errors running the code.
        if exit_status:
            self.fail(decoded_out + decoded_err)

        # Close (deletes) the tempfile.
        tempfile.close()
