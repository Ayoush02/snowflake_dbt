"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Assign explicit version numbers to V__ placeholder migration files.
"""

from deployment.core.config_loader import load_yaml
from deployment.core.logger import Logger
from deployment.core.version_assigner import VersionAssigner


def main():
    deployment_config = load_yaml("deployment/config/deployment.yml")
    log_level = deployment_config.get("logging", {}).get("level", "INFO")
    logger = Logger(log_level=log_level)

    assignments = VersionAssigner(logger, deployment_config).assign()

    if assignments:
        logger.info(
            f"Assigned version numbers to {len(assignments)} migration file(s)."
        )
    else:
        logger.info("No migration version assignments were required.")


if __name__ == "__main__":
    main()
