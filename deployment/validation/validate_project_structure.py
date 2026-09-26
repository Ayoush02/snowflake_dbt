"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Validate Project Structure
"""

from pathlib import Path


class ProjectStructureValidator:

    def __init__(self, logger):

        self.logger = logger

        self.required_directories = [
            "snowflake",
            "snowflake/storedprocedures",
            "snowflake/functions",
            "snowflake/streams",
            "snowflake/tasks",
            "snowflake/dynamic_tables",
            "snowflake/stages",
            "snowflake/file_formats",
            "snowflake/pipes",
            "snowflake/grants",
            "snowflake/snowpark",
            "snowflake/streamlit",
            "snowflake/streamlit_apps",
            "dbt",
            "deployment",
            "deployment/core",
            "deployment/config",
            "deployment/validation",
            "python",
        ]

    def validate(self):

        self.logger.info("Validating Project Structure...")

        missing = [
            folder
            for folder in self.required_directories
            if not Path(folder).exists()
        ]

        if missing:
            self.logger.error("Repository Structure Validation Failed.")

            for folder in missing:
                self.logger.error(folder)

            raise ValueError("Repository Structure Validation Failed.")

        self.logger.info("Repository Structure Validation Successful.")
