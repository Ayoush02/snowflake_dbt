"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Fetch the latest code into a Snowflake Git Repository object.
"""


class GitRepository:
    """Trigger ALTER GIT REPOSITORY ... FETCH in Snowflake."""

    def __init__(self, snowflake_connection, logger, config):
        self.snowflake = snowflake_connection
        self.logger = logger
        self.config = config

    def fetch(self):
        """Fetch the configured Snowflake Git Repository when enabled."""

        if not self.config.get("features", {}).get("fetch_git_repository", False):
            self.logger.info("Snowflake Git Repository fetch disabled.")
            return

        repository_name = self.config["git"]["repository_name"]
        sql = f"ALTER GIT REPOSITORY {repository_name} FETCH;"

        self.logger.info(f"Fetching Snowflake Git Repository: {repository_name}")

        self.snowflake.execute(sql)

        self.logger.info("Snowflake Git Repository fetch completed.")
