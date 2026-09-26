"""
Author  : Abhijit Bangal
Project : Snowflake CI/CD Framework

Build Jinja variables injected at deploy time.
"""

DEFAULT_LAYER_CODES = {
    "RAW": "RAW",
    "TRANSFORM": "TRF",
    "CONSUMPTION": "CON",
}

DEFAULT_SCHEMA_CODES = {
    "CUSTOMER_HUB": "CUSTOMERHUB",
    "HUBSPOT": "HUBSPOT",
    "QUICKBOOKS": "QUICKBOOKS",
    "REPORTING": "REPORTING",
    "ASANA": "ASANA",
    "UTILS": "SDT",
}

ACCESS_PRIVILEGES = ("ALL", "RO", "RW")


def get_database_layers(deployment_config: dict) -> list[str]:
    """Return configured database layer names (RAW, TRANSFORM, etc.)."""

    configured_layers = deployment_config.get("database_layers")

    if configured_layers:
        return [layer.upper() for layer in configured_layers]

    layer_codes = deployment_config.get("access_roles", {}).get("layer_codes")

    if layer_codes:
        return sorted(layer.upper() for layer in layer_codes.keys())

    return ["RAW", "TRANSFORM", "CONSUMPTION"]


def build_warehouses(environment: str, deployment_config: dict) -> dict[str, str]:
    """
    Map logical warehouse names to Snowflake warehouse names for the environment.

    Example (DEV): DEVELOPER -> WH_DEV_DEVELOPER_XS, ELT -> WH_DEV_ELT_XS
    Example (PROD): DEVELOPER -> WH_PROD_DEVELOPER_XS, ELT -> WH_PROD_ELT_XS
    """

    warehouse_config = deployment_config.get("warehouses", {})
    env = environment.upper()
    warehouses = {}

    for name, env_map in warehouse_config.items():
        if env not in env_map:
            raise ValueError(
                f"No warehouse configured for '{name}' in environment '{env}'."
            )

        warehouses[name.upper()] = env_map[env]

    return warehouses


def build_databases(environment: str, layers: list[str]) -> dict[str, str]:
    """
    Map layer folder names to Snowflake database names for the environment.

    Example (DEV): RAW -> DEV_RAW, TRANSFORM -> DEV_TRANSFORM
    Example (PROD): RAW -> PROD_RAW, TRANSFORM -> PROD_TRANSFORM
    """

    env = environment.upper()
    return {layer.upper(): f"{env}_{layer.upper()}" for layer in layers}


def get_layer_codes(deployment_config: dict) -> dict[str, str]:
    configured = deployment_config.get("access_roles", {}).get("layer_codes", {})
    layer_codes = configured or DEFAULT_LAYER_CODES
    return {layer.upper(): code.upper() for layer, code in layer_codes.items()}


def get_schema_codes(deployment_config: dict) -> dict[str, str]:
    configured = deployment_config.get("access_roles", {}).get("schema_codes", {})
    schema_codes = configured or DEFAULT_SCHEMA_CODES
    return {schema.upper(): code.upper() for schema, code in schema_codes.items()}


def resolve_schema_code(schema_folder: str, schema_codes: dict[str, str]) -> str:
    normalized = schema_folder.upper()

    if normalized in schema_codes:
        return schema_codes[normalized]

    return normalized.replace("_", "")


def build_access_role(
    environment: str,
    layer: str,
    schema: str,
    privilege: str,
    deployment_config: dict,
) -> str:
    """
    Build AR role name: AR_{ENV}_{LAYER}_{SCHEMA}_{PRIVILEGE}

    Example: AR_DEV_RAW_CUSTOMERHUB_RW
    """

    layer_codes = get_layer_codes(deployment_config)
    schema_codes = get_schema_codes(deployment_config)

    layer_key = layer.upper()
    if layer_key not in layer_codes:
        raise ValueError(
            f"Unknown database layer '{layer}' for access role resolution."
        )

    layer_code = layer_codes[layer_key]
    schema_code = resolve_schema_code(schema, schema_codes)
    env = environment.upper()
    priv = privilege.upper()

    return f"AR_{env}_{layer_code}_{schema_code}_{priv}"


def build_access_roles_for_target(
    environment: str,
    layer: str,
    schema: str,
    deployment_config: dict,
) -> dict[str, str]:
    """Return ALL, RO, and RW access roles for one deploy target."""

    return {
        privilege: build_access_role(
            environment,
            layer,
            schema,
            privilege,
            deployment_config,
        )
        for privilege in ACCESS_PRIVILEGES
    }


def default_grant_privilege(deployment_config: dict) -> str:
    privilege = deployment_config.get("access_roles", {}).get(
        "default_privilege",
        "RW",
    )
    return privilege.upper()


def build_dbt_vars(environment: str, deployment_config: dict) -> dict:
    """
    Resolve dbt project object name, target, and EXECUTE args for the environment.

    Used both when rendering dbt YAML for `snow dbt deploy` and when SchemaChange
    creates the task that runs EXECUTE DBT PROJECT.
    """

    dbt_config = deployment_config.get("dbt", {})
    env = environment.upper()
    default_targets = dbt_config.get("default_target", {})
    target = default_targets.get(env) or ("prod" if env == "PROD" else "dev")
    args_by_env = dbt_config.get("args", {})
    args = args_by_env.get(env) or f"run --target {target}"
    schema = str(dbt_config.get("schema") or "POSTGRES").upper()
    database_layer = dbt_config.get("database_layer", "TRANSFORM").upper()
    databases = build_databases(environment, get_database_layers(deployment_config))

    if database_layer not in databases:
        raise ValueError(
            f"dbt.database_layer '{database_layer}' is not a configured "
            "database layer."
        )

    return {
        "dbt_project_name": dbt_config.get("project_name", "DBT"),
        "dbt_target": target,
        "dbt_schema": schema,
        "dbt_database_layer": database_layer,
        "dbt_database": databases[database_layer],
        "dbt_args": args,
        "snowflake_role": deployment_config["snowflake"]["role"],
    }
