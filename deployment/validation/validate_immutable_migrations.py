"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Prevent edits to already-committed versioned migration files.
"""

import re
import subprocess
from pathlib import Path


class ImmutableMigrationValidator:

    VERSIONED_FILE_PATTERN = re.compile(
        r"^V\d+\.\d+\.\d+__.+\.sql$",
        re.IGNORECASE,
    )

    def __init__(self, logger, base_ref=None, root_folder="snowflake"):
        self.logger = logger
        self.base_ref = base_ref
        self.root_folder = Path(root_folder)

    def validate(self):

        if not self.base_ref:
            self.logger.info(
                "Skipping immutable migration validation (no base ref supplied)."
            )
            return

        self.logger.info(
            f"Validating immutable versioned migrations against {self.base_ref}..."
        )

        result = subprocess.run(
            [
                "git",
                "diff",
                "--name-status",
                f"{self.base_ref}...HEAD",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Unable to compare migrations with base ref: "
                f"{result.stderr.strip()}"
            )

        modified_files = []

        for line in result.stdout.splitlines():
            if not line.strip():
                continue

            parts = line.split("\t")

            if len(parts) < 2:
                continue

            status = parts[0].strip()
            file_path = parts[-1].strip()

            if status.startswith("R") and len(parts) >= 3:
                file_path = parts[-1].strip()

            if status not in {"M", "R"}:
                continue

            if not file_path.startswith(f"{self.root_folder}/"):
                continue

            filename = Path(file_path).name

            if self.VERSIONED_FILE_PATTERN.match(filename):
                modified_files.append(file_path)

        if modified_files:
            self.logger.error(
                "Versioned migration files must remain immutable after deployment."
            )

            for file_path in modified_files:
                self.logger.error(file_path)

            raise ValueError("Immutable migration validation failed.")

        self.logger.info("Immutable migration validation successful.")
