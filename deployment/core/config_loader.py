"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

YAML configuration loader with environment variable expansion.
"""

import os
from pathlib import Path

import yaml


def expand_env(value):
    """Recursively expand ${VAR} placeholders using the process environment."""

    if isinstance(value, str):
        return os.path.expandvars(value)

    if isinstance(value, dict):
        return {key: expand_env(item) for key, item in value.items()}

    if isinstance(value, list):
        return [expand_env(item) for item in value]

    return value


def load_yaml(file_path):
    """Load a YAML file and expand environment variables."""

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        config = yaml.safe_load(file) or {}

    return expand_env(config)
