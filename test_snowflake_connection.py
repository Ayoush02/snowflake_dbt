import os
import snowflake.connector
from cryptography.hazmat.primitives import serialization

key_path = os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]

with open(key_path, "rb") as key_file:
    private_key = serialization.load_pem_private_key(
        key_file.read(),
        password=None,
    )

private_key_bytes = private_key.private_bytes(
    encoding=serialization.Encoding.DER,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    private_key=private_key_bytes,
    role="ACCOUNTADMIN",
    warehouse="COMPUTE_WH",
)

cursor = conn.cursor()

try:
    cursor.execute("""
        SELECT
            CURRENT_USER(),
            CURRENT_ROLE(),
            CURRENT_WAREHOUSE(),
            CURRENT_ACCOUNT()
    """)

    print(cursor.fetchone())

finally:
    cursor.close()
    conn.close()