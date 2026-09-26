# Developer Guide — File Conventions, Snowpark SPs, Streamlit Apps, and Do's / Don'ts

Author: Abhijit Bangal

This guide is for developers adding or changing Snowflake objects in this repository. It covers **naming rules**, **folder layout**, **Snowpark stored procedure setup**, **Streamlit in Snowflake (SiS) setup**, and common mistakes to avoid.

For CI/CD workflow and grants configuration, see the main [README](README.md).

---

## 1. Golden rules

| Do | Don't |
|---|---|
| Put SQL under `snowflake/<object_type>/<database>/<schema>/` | Hardcode `DEV_RAW`, `PROD_RAW`, or schema names in SQL/Python |
| Use folder path to define database and schema | Add database/schema mapping in config or Jinja |
| Create a **`V__description.sql`** placeholder for table changes | Pick version numbers manually or edit a deployed `V*.sql` file |
| Keep **Python** in `snowflake/snowpark/` and **DDL** in `snowflake/storedprocedures/` | Put Python inline inside the SP DDL file |
| Keep **Streamlit Python** in `snowflake/streamlit_apps/` and **DDL** in `snowflake/streamlit/` | Put Streamlit Python inline inside CREATE STREAMLIT SQL |
| Put **GRANT** statements in `snowflake/grants/` | Put `GRANT` / `GRANT OWNERSHIP` inside table or SP DDL |
| Use `{{ grant_role }}` or `{{ access_roles.RW }}` for grants | Hardcode access role names like `AR_DEV_RAW_CUSTOMERHUB_RW` in grant SQL |
| Use Jinja for Git repo path, branch, grant roles, cross-layer DB refs, and warehouses | Hardcode `DEV_RAW` / `PROD_RAW`, Git branch paths, or `WH_DEV_*` / `WH_PROD_*` |
| Open a PR to `dev` or `main` | Commit directly to `dev` or `main` |
  
---

## 2. Folder structure

```
snowflake/
├── tables/<DATABASE>/<SCHEMA>/V__create_emp.sql
├── views/<DATABASE>/<SCHEMA>/R__my_view.sql
├── storedprocedures/<DATABASE>/<SCHEMA>/R__create_my_sp.sql
├── grants/<DATABASE>/<SCHEMA>/R__grant_my_sp.sql
├── snowpark/<DATABASE>/<SCHEMA>/<PROCEDURE_NAME>/src/main.py
├── streamlit/<DATABASE>/<SCHEMA>/R__create_my_app.sql
└── streamlit_apps/<DATABASE>/<SCHEMA>/<APP_NAME>/streamlit_app.py
```

### How folder names map to Snowflake

| Folder segment | Example | Resolves to (on `dev` branch) |
|---|---|---|
| `<DATABASE>` | `RAW` | Database prefix → `DEV_RAW` |
| `<SCHEMA>` | `CUSTOMER_HUB` | Schema → `CUSTOMER_HUB` |
| Full path | `snowflake/tables/RAW/CUSTOMER_HUB/` | `DEV_RAW.CUSTOMER_HUB` |

On `main` branch the same path deploys to `PROD_RAW.CUSTOMER_HUB`.

**You never type `DEV_RAW` or `PROD_RAW` in migration files.** The deployment engine sets session context from the folder.

Valid folder names: uppercase letters, numbers, underscore (e.g. `RAW`, `CUSTOMER_HUB`, `HUBSPOT`).

---

## 3. File naming conventions

Only three migration filename patterns are allowed (enforced in PR validation):

### Versioned migrations (run once) — use placeholders

**What developers commit:**

```
V__<description>.sql
```

Examples:

```
V__create_emp_table.sql
V__add_dept_id_to_emp.sql
V__create_department_table.sql
V__create_customer.sql
```

Rules:

- Must start with `V__` (no version number in the filename you create).
- Must contain `__` (double underscore) before the description.
- Extension must be `.sql`.
- **Do not pick `V1.0.0` yourself** — the deploy workflow assigns the number after merge.

**What CI assigns before deploy** (you do not create these manually):

```
V<major>.<minor>.<patch>__<description>.sql
```

Examples after assignment:

```
V1.0.0__create_emp_table.sql
V1.0.1__add_dept_id_to_emp.sql
V1.1.0__create_department_table.sql
V2.0.0__create_customer.sql
```

- **Immutable after merge** — never edit an assigned `V*.sql` file; add a new `V__*.sql` placeholder instead.

### Repeatable migrations (re-run when content changes)

```
R__<description>.sql
```

Examples:

```
R__create_emp_dept_sp.sql
R__customer_summary_view.sql
R__grant_emp_dept_sp.sql
```

Rules:

- Must start with `R__`.
- Used for views, stored procedures, grants, and other replaceable objects.
- SchemaChange re-applies when the file checksum changes.

### Invalid names (will fail validation)

```
create_emp.sql              ❌ missing V prefix
V1.0.0__create_emp.sql      ❌ do not pick versions manually — use V__create_emp.sql
V1.0__create_emp.sql        ❌ only two version parts
v1.0.0_create_emp.sql       ❌ single underscore
R_grant.sql                 ❌ missing second underscore
```

---

## 4. Version numbering strategy

**Developers do not maintain version numbers.** Commit `V__description.sql` and let the deploy workflow assign `V*.*.*__description.sql`.

### How assignment works

1. You open a PR with `V__add_email_to_customer.sql`.
2. PR validation accepts the placeholder (no duplicate check on unassigned files).
3. After merge, deploy runs `python -m deployment.assign_versions`.
4. The file is renamed to the next repo-wide version, e.g. `V3.2.0__add_email_to_customer.sql`.
5. CI commits that rename, then SchemaChange deploys it.

Versions must remain **globally unique** across the entire repository. The assigner always picks a number higher than any existing `V*.*.*` in the repo.

### Assigned version meaning

When CI assigns a number, it follows this convention:

```
V<SourceSystem>.<TableNumber>.<ChangeNumber>__<description>.sql
```

| Digit | Meaning | Example |
|---|---|---|
| First | Source system | `1` = Postgres, `2` = HubSpot |
| Second | Table sequence within source | `0` = first table, `1` = second table |
| Third | Change number for that table | `0` = create, `1` = first alter |

Examples (after CI assignment):

```
V__create_emp_table.sql             -- you commit this
V1.0.0__create_emp_table.sql        -- CI assigns this after merge

V__add_dept_id_to_emp.sql           -- you commit this
V1.0.1__add_dept_id_to_emp.sql       -- CI assigns this after merge
```

Suggested source ranges:

| Source | Version range |
|---|---|
| Postgres / internal | V1.x.x |
| HubSpot | V2.x.x |
| QuickBooks | V3.x.x |

First migration in an empty schema can start from configured prefixes in `deployment/config/deployment.yml`:

```yaml
version_prefixes:
  RAW:
    CUSTOMER_HUB: "1.0.0"
    HUBSPOT: "2.0.0"
    QUICKBOOKS: "3.0.0"
```

After that, all new placeholders increment from the repo-wide maximum.

## 5. Deployment order (why it matters)

Objects deploy in this order for each schema target:

```
file_formats → stages → tables → streams → views → functions
→ storedprocedures → dynamic_tables → tasks → pipes → snowpark → streamlit → grants
```

Implications:

- Create **tables** before **stored procedures** that read them.
- Create **stored procedures** and **Streamlit apps** before **grants** that reference them.
- **Grants always deploy last.**

---

## 5a. Views and dynamic tables — cross-layer database references

When a **view** or **dynamic table** selects from another database layer (e.g. CONSUMPTION reading RAW), use Jinja `{{ databases.<LAYER> }}`. The pipeline resolves it from branch/environment:

| Jinja | On `dev` (DEV) | On `main` (PROD) |
|---|---|---|
| `{{ databases.RAW }}` | `DEV_RAW` | `PROD_RAW` |
| `{{ databases.TRANSFORM }}` | `DEV_TRANSFORM` | `PROD_TRANSFORM` |
| `{{ databases.CONSUMPTION }}` | `DEV_CONSUMPTION` | `PROD_CONSUMPTION` |

Layers are configured in `deployment/config/deployment.yml` under `database_layers`.

**Example view** (`snowflake/views/CONSUMPTION/COMMERCIAL_SCH/R__vw_customers.sql`):

```sql
CREATE OR REPLACE VIEW VW_CUSTOMERS AS
SELECT
    c.CUSTOMER_ID,
    c.FIRST_NAME,
    c.LAST_NAME
FROM {{ databases.RAW }}.HUBSPOT.CUSTOMERS c;
```

**Example dynamic table**:

```sql
CREATE OR REPLACE DYNAMIC TABLE DT_CUSTOMER_ORDERS
  TARGET_LAG = '1 hour'
  WAREHOUSE = {{ warehouses.ELT }}
AS
SELECT *
FROM {{ databases.RAW }}.HUBSPOT.ORDERS;
```

**Example task**:

```sql
CREATE OR REPLACE TASK TASK_REFRESH_ORDERS
  WAREHOUSE = {{ warehouses.ELT }}
  SCHEDULE = 'USING CRON 0 * * * * UTC'
AS
  CALL SOME_PROC();
```

Rules:

- **Same database/schema** as deploy target → use unqualified names (`EMP`, not `DEV_RAW...EMP`).
- **Cross-layer SELECT** in views/dynamic tables → use `{{ databases.RAW }}`, etc.
- **WAREHOUSE clause** in dynamic tables/tasks → use `{{ warehouses.ELT }}` or `{{ warehouses.DEVELOPER }}`.
- **Never** hardcode `DEV_RAW` or `PROD_RAW` in views/dynamic_tables (PR validation fails).
- **Never** hardcode `WH_DEV_*` or `WH_PROD_*` in dynamic_tables/tasks (PR validation fails).

---

## 5b. Dynamic tables and tasks — warehouse references

When a **dynamic table** or **task** needs a warehouse, use Jinja `{{ warehouses.<NAME> }}`. The pipeline resolves it from branch/environment:

| Jinja | On `dev` (DEV) | On `main` (PROD) |
|---|---|---|
| `{{ warehouses.DEVELOPER }}` | `WH_DEV_DEVELOPER_XS` | `WH_PROD_DEVELOPER_XS` |
| `{{ warehouses.ELT }}` | `WH_DEV_ELT_XS` | `WH_PROD_ELT_XS` |

Warehouses are configured in `deployment/config/deployment.yml` under `warehouses`.

**Note:** `CICD_DEPLOY_WH` in the same config file is only for the CI/CD deploy connection — not for object DDL.

---

## 6. Snowpark stored procedure setup

A Snowpark SP is **two separate artifacts** in Git:

| What | Where | Deployed by |
|---|---|---|
| SP DDL (`CREATE PROCEDURE`) | `snowflake/storedprocedures/<DB>/<SCHEMA>/R__*.sql` | SchemaChange (SQL) |
| Python handler code | `snowflake/snowpark/<DB>/<SCHEMA>/<PROC_NAME>/src/main.py` | Snowflake Git Repository (IMPORTS) |

They are **not** the same file and **not** in the same folder.

### Step-by-step: new Snowpark SP

**Example:** `EMP_DEPT_SP` in `RAW.CUSTOMER_HUB`

#### Step 1 — Python code

Path:

```
snowflake/snowpark/RAW/CUSTOMER_HUB/EMP_DEPT_SP/src/main.py
```

```python
from snowflake.snowpark import Session


def run(session: Session) -> str:
    current_db = session.get_current_database().replace('"', '')
    current_schema = session.get_current_schema().replace('"', '')
    table_fqn = f"{current_db}.{current_schema}.EMP"

    emp_df = session.table(table_fqn)
    return f"Row count: {emp_df.count()}"
```

Optional config (not required for deploy):

```
snowflake/snowpark/RAW/CUSTOMER_HUB/EMP_DEPT_SP/config/settings.yml
```

#### Step 2 — SP DDL (separate file)

Path:

```
snowflake/storedprocedures/RAW/CUSTOMER_HUB/R__create_emp_dept_sp.sql
```

```sql
CREATE OR REPLACE PROCEDURE EMP_DEPT_SP()
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.11'
PACKAGES = ('snowflake-snowpark-python')
IMPORTS = (
    '@{{ git_repository }}/branches/{{ git_branch }}/snowflake/snowpark/RAW/CUSTOMER_HUB/EMP_DEPT_SP/src/main.py'
)
HANDLER = 'main.run'
EXECUTE AS OWNER;
```

Notes:

- `git_repository` and `git_branch` are injected at deploy time (`dev` → DEV, `main` → PROD).
- Import the **file** (`main.py`), not the directory, when using `HANDLER = 'main.run'`.
- Do **not** put `GRANT` in this file.

#### Step 3 — Grants (separate file)

Path:

```
snowflake/grants/RAW/CUSTOMER_HUB/R__grant_emp_dept_sp.sql
```

```sql
GRANT OWNERSHIP ON PROCEDURE EMP_DEPT_SP()
    TO ROLE {{ grant_role }}
    COPY CURRENT GRANTS;
```

`{{ grant_role }}` resolves automatically from folder path + branch:

```text
snowflake/grants/RAW/CUSTOMER_HUB/  →  AR_DEV_RAW_CUSTOMERHUB_RW  (on dev)
                                      →  AR_PROD_RAW_CUSTOMERHUB_RW (on main)
```

Use `{{ access_roles.RO }}` or `{{ access_roles.ALL }}` when a different privilege is needed.

#### Step 4 — Deploy flow

```text
1. Merge to dev/main
2. CI fetches Snowflake Git Repository (Python code available to Snowflake)
3. SchemaChange creates/replaces procedure (IMPORTS from Git repo)
4. SchemaChange applies grants last
```

### Snowpark IMPORTS / HANDLER pairing

| IMPORTS path ends with | HANDLER |
|---|---|
| `.../src/main.py` (single file) | `main.run` |
| `.../src/` (directory) | `main.run` (directory import — prefer single file) |

---

## 6a. Streamlit in Snowflake (SiS) setup

A Streamlit app is **two separate artifacts** in Git (same pattern as Snowpark SPs):

| What | Where | Deployed by |
|---|---|---|
| `CREATE STREAMLIT` SQL | `snowflake/streamlit/<DB>/<SCHEMA>/R__*.sql` | SchemaChange (SQL) |
| Python app code | `snowflake/streamlit_apps/<DB>/<SCHEMA>/<APP_NAME>/streamlit_app.py` | Snowflake Git Repository (`FROM` path in SQL) |

### Step-by-step: new Streamlit app

**Example:** `CUSTOMER_DASHBOARD` in `CONSUMPTION.CUSTOMER_HUB`

#### Step 1 — Python app

Path:

```
snowflake/streamlit_apps/CONSUMPTION/CUSTOMER_HUB/CUSTOMER_DASHBOARD/streamlit_app.py
```

```python
import streamlit as st
from snowflake.snowpark.context import get_active_session

session = get_active_session()
st.title("Customer Dashboard")

df = session.sql("SELECT * FROM CUSTOMERS LIMIT 100").to_pandas()
st.dataframe(df)
```

Use **unqualified** table names for objects in the same deploy target schema.

#### Step 2 — Streamlit DDL (separate file)

Path:

```
snowflake/streamlit/CONSUMPTION/CUSTOMER_HUB/R__create_customer_dashboard.sql
```

```sql
CREATE OR REPLACE STREAMLIT CUSTOMER_DASHBOARD
  FROM @{{ git_repository }}/branches/{{ git_branch }}/snowflake/streamlit_apps/CONSUMPTION/CUSTOMER_HUB/CUSTOMER_DASHBOARD/
  MAIN_FILE = 'streamlit_app.py'
  QUERY_WAREHOUSE = {{ warehouses.DEVELOPER }};
```

Notes:

- `git_repository` and `git_branch` are injected at deploy time (`dev` → DEV, `main` → PROD).
- Use `{{ warehouses.DEVELOPER }}` or `{{ warehouses.ELT }}` for `QUERY_WAREHOUSE`.
- Do **not** hardcode `WH_DEV_*` / `WH_PROD_*` or `dev` / `main` in the Git path.
- Do **not** put `GRANT` in this file.

#### Step 3 — Grants (optional, separate file)

Path:

```
snowflake/grants/CONSUMPTION/CUSTOMER_HUB/R__grant_customer_dashboard.sql
```

```sql
GRANT USAGE ON STREAMLIT CUSTOMER_DASHBOARD TO ROLE {{ grant_role }};
```

#### Step 4 — Deploy flow

```text
1. Merge to dev/main
2. CI fetches Snowflake Git Repository (Python code available to Snowflake)
3. SchemaChange creates/replaces Streamlit object (FROM Git repo path)
4. SchemaChange applies grants last
```

Folder names at the app level must be valid Snowflake identifiers: `CUSTOMER_DASHBOARD`, not `customer-dashboard`.

---

## 7. What to avoid in SQL and Python

### Do not hardcode environment-specific database names

```sql
-- ❌ Wrong
CREATE TABLE DEV_RAW.CUSTOMER_HUB.EMP (...);
SELECT * FROM PROD_RAW.CUSTOMER_HUB.EMP;
```

```sql
-- ✅ Correct (session context from folder)
CREATE TABLE IF NOT EXISTS EMP (...);
SELECT * FROM EMP;
```

### Do not hardcode schema in DDL

```sql
-- ❌ Wrong
CREATE TABLE DEV_RAW.CUSTOMER_HUB.EMP (...);
```

```sql
-- ✅ Correct
CREATE TABLE IF NOT EXISTS EMP (...);
```

### Do not hardcode roles in grant scripts

```sql
-- ❌ Wrong
GRANT OWNERSHIP ON PROCEDURE EMP_DEPT_SP() TO ROLE AR_DEV_RAW_CUSTOMERHUB_RW;
```

```sql
-- ✅ Correct
GRANT OWNERSHIP ON PROCEDURE EMP_DEPT_SP() TO ROLE {{ grant_role }};
```

### Do not use wrong Snowflake grant syntax

```sql
-- ❌ Wrong
COPY GRANTS;
```

```sql
-- ✅ Correct
COPY CURRENT GRANTS;
```

### Do not mix concerns in one file

| File type | Should contain | Should NOT contain |
|---|---|---|
| `V*.sql` / table DDL | `CREATE TABLE`, `ALTER TABLE` | `GRANT`, `CREATE PROCEDURE` |
| `R__` stored procedure DDL | `CREATE PROCEDURE` | Python code, `GRANT` |
| `snowpark/.../main.py` | Python handler logic | `CREATE PROCEDURE` SQL |
| `grants/R__*.sql` | `GRANT`, `GRANT OWNERSHIP` | `CREATE TABLE`, `CREATE PROCEDURE` |

### Do not edit deployed version files

```text
❌  Change V1.0.0__create_emp_table.sql after it merged to dev
✅  Add V__add_new_column.sql (CI assigns the version on deploy)
```

PR validation blocks edits to already-committed versioned migrations.

---

## 8. Jinja — where it is allowed

| Variable | Used in | Purpose |
|---|---|---|
| `{{ git_repository }}` | SP DDL `IMPORTS`, Streamlit `FROM` | Snowflake Git Repository object |
| `{{ git_branch }}` | SP DDL `IMPORTS`, Streamlit `FROM` | `dev` or `main` branch path |
| `{{ grant_role }}` | `snowflake/grants/` | Default RW access role for current layer + schema |
| `{{ access_roles.RW }}` | Grants | Read-write access role |
| `{{ access_roles.RO }}` | Grants | Read-only access role |
| `{{ access_roles.ALL }}` | Grants | Full access role |
| `{{ environment }}` | Any (optional) | `DEV` or `PROD` |
| `{{ databases.RAW }}` | `views/`, `dynamic_tables/` | Cross-layer DB: `DEV_RAW` / `PROD_RAW` |
| `{{ databases.TRANSFORM }}` | `views/`, `dynamic_tables/` | Cross-layer DB: `DEV_TRANSFORM` / `PROD_TRANSFORM` |
| `{{ databases.CONSUMPTION }}` | `views/`, `dynamic_tables/` | Cross-layer DB: `DEV_CONSUMPTION` / `PROD_CONSUMPTION` |
| `{{ warehouses.DEVELOPER }}` | `dynamic_tables/`, `tasks/`, `streamlit/` | Developer warehouse: `WH_DEV_DEVELOPER_XS` / `WH_PROD_DEVELOPER_XS` |
| `{{ warehouses.ELT }}` | `dynamic_tables/`, `tasks/`, `streamlit/` | ELT warehouse: `WH_DEV_ELT_XS` / `WH_PROD_ELT_XS` |

Folder structure still sets the **deploy target** database/schema. Use `{{ databases.* }}` for **cross-layer SELECTs** in views and dynamic tables. Use `{{ warehouses.* }}` for **WAREHOUSE** / **QUERY_WAREHOUSE** clauses in dynamic tables, tasks, and Streamlit apps.

---

## 9. PR checklist (before you merge)

- [ ] Files are under `snowflake/<object_type>/<DATABASE>/<SCHEMA>/`
- [ ] Versioned table changes use `V__description.sql` placeholders (not manual `V1.0.0__...`)
- [ ] Repeatable files named `R__description.sql`
- [ ] No edits to previously deployed `V*.sql` files
- [ ] No `DEV_RAW`, `PROD_RAW` in **views** or **dynamic_tables** — use `{{ databases.RAW }}` etc.
- [ ] No `WH_DEV_*`, `WH_PROD_*` in **dynamic_tables** or **tasks** — use `{{ warehouses.ELT }}` etc.
- [ ] No hardcoded schema/database in table DDL or SPs (same-layer objects use unqualified names)
- [ ] Snowpark: Python in `snowpark/.../src/`, DDL in `storedprocedures/`
- [ ] Streamlit: Python in `streamlit_apps/.../`, DDL in `streamlit/`
- [ ] SP IMPORTS and Streamlit `FROM` use `{{ git_repository }}` and `{{ git_branch }}`
- [ ] Streamlit `QUERY_WAREHOUSE` uses `{{ warehouses.DEVELOPER }}` or `{{ warehouses.ELT }}`
- [ ] Grants in `snowflake/grants/` using `{{ grant_role }}`
- [ ] No `GRANT` inside table or SP create scripts
- [ ] PR targets `dev` (for DEV) or `main` (for PROD)

---

## 10. Quick reference — EMP_DEPT_SP example

```
snowflake/
├── tables/RAW/CUSTOMER_HUB/
│   ├── V1.0.0__create_emp_table.sql       ← assigned by CI after merge
│   ├── V1.0.1__add_dept_id_to_emp.sql     ← assigned by CI after merge
│   └── V__create_department_table.sql     ← you commit this; CI assigns on deploy
│
├── storedprocedures/RAW/CUSTOMER_HUB/
│   └── R__create_emp_dept_sp.sql          ← CREATE PROCEDURE only
│
├── snowpark/RAW/CUSTOMER_HUB/EMP_DEPT_SP/
│   └── src/main.py                        ← Python handler
│
└── grants/RAW/CUSTOMER_HUB/
    └── R__grant_emp_dept_sp.sql           ← ownership / usage grants
```

Deploy target on `dev`: **`DEV_RAW.CUSTOMER_HUB`** — derived from folders, not written in code.

---

## 11. Automated checks (PR validation)

The pipeline validates automatically:

| Check | What it enforces |
|---|---|
| Project structure | Required folders exist (`tables`, `grants`, `snowpark`, `streamlit`, `streamlit_apps`, etc.) |
| Schema path names | Database/schema folder names are valid identifiers |
| Version format | `V__*.sql` placeholders, assigned `V*.*.*__*.sql`, and `R__*.sql` |
| Duplicate versions | No two files share the same version number |
| Immutable migrations | No changes to existing `V*.sql` in the PR |
| Hardcoded database refs | No `DEV_RAW` / `PROD_RAW` in views or dynamic_tables |
| Hardcoded warehouse refs | No `WH_DEV_*` / `WH_PROD_*` in dynamic_tables or tasks |
| Warehouse config | `warehouses` DEV/PROD mapping when dynamic_tables or tasks exist |
| Access roles config | `access_roles` layer/schema mapping when grant scripts exist |

Run locally before pushing:

```bash
python -m deployment.deploy --validate-only
```

---

## 12. Common mistakes

| Mistake | Fix |
|---|---|
| SP fails: `No module named 'main'` | Import `main.py` explicitly; use `HANDLER = 'main.run'` |
| Table not found in SP | Use `session.get_current_database()` / `get_current_schema()` to build FQN |
| Grant syntax error | Use `COPY CURRENT GRANTS` |
| Grant applied before SP exists | Grants deploy last — ensure SP `R__` script exists |
| Python changes not picked up | Push to branch; CI runs `ALTER GIT REPOSITORY FETCH` before SP deploy |
| Deploy skipped grant script | `R__` file unchanged — edit file to trigger re-run |

---

For questions about CI/CD, secrets, or platform configuration, contact the platform / CI/CD owner.

---

## Related docs

- [README](README.md) — CI/CD architecture, deployment, grants configuration
