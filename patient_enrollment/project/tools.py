"""Tools for clinical trial enrollment agent."""

from pathlib import Path

import duckdb

from functools import lru_cache


@lru_cache(maxsize=1)  # memoize the DB connection
def get_db_conn() -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection with clinical trial data loaded."""
    # Database connection
    data_dir = Path(__file__).parent.parent / "data"
    db = duckdb.connect(":memory:")

    # Load CSVs into DuckDB tables
    db.execute(
        f"CREATE TABLE programs AS SELECT * FROM read_csv_auto('{data_dir}/clinical_programs.csv')"
    )
    db.execute(
        f"CREATE TABLE persons AS SELECT * FROM read_csv_auto('{data_dir}/persons.csv')"
    )

    return db



LIST_ALL_PROGRAMS_TOOL_DEF = {
    "name": "list_all_programs",
    "description": "List all available clinical programs.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

def list_all_programs() -> dict:
    """List all available clinical programs."""
    programs = (
        get_db_conn()
        .execute(
            "SELECT program_id, program_name, phase, description FROM programs ORDER BY program_id"
        )
        .fetchall()
    )

    return {
        "total_programs": len(programs),
        "programs": [
            {
                "program_id": str(p[0]),
                "program_name": str(p[1]),
                "phase": str(p[2]),
                "description": str(p[3]),
            }
            for p in programs
        ],
    }

FIND_PROGRAM_BY_NAME_TOOL_DEF = {
    "name": "find_program_by_name",
    "description": "Find a clinical program by its name using SQL LIKE matching.",
    "parameters": {
        "type": "object",
        "properties": {
            "program_name": {
                "type": "string",
                "description": "The name (or part of the name) of the clinical program to find.",
            },
        },
        "required": ["program_name"],
    },
}

def find_program_by_name(program_name: str) -> dict:
    """Find clinical program by name using SQL LIKE matching."""
    result = (
        get_db_conn()
        .execute(
            "SELECT program_id, program_name, phase, description FROM programs WHERE program_name ILIKE ? LIMIT 1",
            [f"%{program_name}%"],
        )
        .fetchone()
    )

    if not result:
        return {"error": f"No program found matching '{program_name}'"}

    return {
        "program_id": str(result[0]),
        "program_name": str(result[1]),
        "phase": str(result[2]),
        "description": str(result[3]),
    }

FIND_CANDIDATES_FOR_PROGRAM_TOOL_DEF = {
    "name": "find_candidates_for_program",
    "description": "Find eligible candidates for a clinical program based on its criteria.",
    "parameters": {
        "type": "object",
        "properties": {
            "program_id": {
                "type": "string",
                "description": "The ID of the clinical program to find candidates for (e.g., CP001).",
            },
        },
        "required": ["program_id"],
    },
}


def find_candidates_for_program(program_id: str) -> dict:
    """Find eligible candidates for a clinical program using SQL."""

    # Get program details
    program = (
        get_db_conn()
        .execute("SELECT * FROM programs WHERE program_id = ?", [program_id])
        .fetchone()
    )  # type: ignore[assignment]

    if not program:
        return {"error": f"Program {program_id} not found"}

    # Build SQL query dynamically based on program criteria
    conditions = []

    # Age
    if program[4]:  # min_age
        conditions.append(f"age >= {program[4]}")
    if program[5]:  # max_age
        conditions.append(f"age <= {program[5]}")

    # Gender
    if program[6]:  # eligible_genders
        genders = program[6].split(";")
        gender_clause = " OR ".join([f"gender = '{g}'" for g in genders])
        conditions.append(f"({gender_clause})")

    # BMI
    if program[9]:  # min_bmi
        conditions.append(f"bmi >= {program[9]}")
    if program[10]:  # max_bmi
        conditions.append(f"bmi <= {program[10]}")

    # Smoking
    if program[11]:  # smoking_allowed
        allowed = program[11].split(";")
        smoking_clause = " OR ".join([f"smoking_status = '{s}'" for s in allowed])
        conditions.append(f"({smoking_clause})")

    # HbA1c
    if program[12]:  # min_hemoglobin_a1c
        conditions.append(f"hemoglobin_a1c >= {program[12]}")
    if program[13]:  # max_hemoglobin_a1c
        conditions.append(f"hemoglobin_a1c <= {program[13]}")

    # eGFR
    if program[14]:  # min_egfr
        conditions.append(f"egfr >= {program[14]}")
    if program[15]:  # max_egfr
        conditions.append(f"egfr <= {program[15]}")

    # Required conditions
    if program[7]:  # required_conditions
        for cond in program[7].split(";"):
            if cond in [
                "diabetes",
                "hypertension",
                "heart_disease",
                "asthma",
                "copd",
                "kidney_disease",
            ]:
                conditions.append(f"{cond} = 'yes'")
            else:
                conditions.append(f"cancer_history = '{cond}'")

    # Excluded conditions
    if program[8]:  # excluded_conditions
        for cond in program[8].split(";"):
            if cond in [
                "diabetes",
                "hypertension",
                "heart_disease",
                "asthma",
                "copd",
                "kidney_disease",
            ]:
                conditions.append(f"{cond} = 'no'")
            else:
                conditions.append(f"cancer_history != '{cond}'")

    # Required medications
    if program[16]:  # required_medications
        for med in program[16].split(";"):
            conditions.append(f"CONTAINS(medications, '{med}')")

    # Excluded medications
    if program[17]:  # excluded_medications
        for med in program[17].split(";"):
            conditions.append(f"NOT CONTAINS(medications, '{med}')")

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT person_id, first_name, last_name, age, gender
        FROM persons
        WHERE {where_clause}
    """

    candidates = get_db_conn().execute(query).fetchall()

    return {
        "program_id": program_id,
        "program_name": str(program[1]),
        "total_eligible": len(candidates),
        "candidates": [
            {
                "person_id": str(c[0]),
                "name": f"{c[1]} {c[2]}",
                "age": int(c[3]),
                "gender": str(c[4]),
            }
            for c in candidates
        ],
    }
