"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Snowflake Connection Utility
"""

from cryptography.hazmat.primitives import serialization
import snowflake.connector


class SnowflakeConnection:

    def __init__(self, config, logger):

        self.logger = logger
        self.config = config
        self.connection = None

    def __load_private_key(self):

        self.logger.info("Loading Snowflake Private Key...")

        private_key_path = self.config["snowflake"]["private_key_path"]
        passphrase = self.config["snowflake"].get("private_key_passphrase")
        passphrase = passphrase.strip() if isinstance(passphrase, str) else passphrase

        password = passphrase.encode() if passphrase else None

        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=password,
            )

        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def connect(self):

        try:
            self.logger.info("Connecting to Snowflake...")

            private_key = self.__load_private_key()

            self.connection = snowflake.connector.connect(
                account=self.config["snowflake"]["account"],
                user=self.config["snowflake"]["user"],
                private_key=private_key,
                role=self.config["snowflake"]["role"],
                warehouse=self.config["snowflake"]["warehouse"],
            )

            self.logger.info("Connection Successful.")

            return self.connection

        except Exception as exc:
            self.logger.exception(str(exc))
            raise

    def execute(self, sql):

        self.logger.info(sql)

        cursor = self.connection.cursor()

        try:
            cursor.execute(sql)
            return cursor.fetchall()

        except Exception as exc:
            self.logger.error(f"Snowflake SQL failed: {exc}")
            raise

        finally:
            cursor.close()

    def close(self):

        if self.connection:
            self.connection.close()
            self.logger.info("Snowflake Connection Closed.")
