"""Tools for clinical trial enrollment agent."""

from pathlib import Path

import duckdb
from rapidfuzz import fuzz
from rapidfuzz.process import extractOne

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

FIND_PERSON_BY_NAME_TOOL_DEF = {
    "name": "find_person_by_name",
    "description": "Find a person/candidate by their name using fuzzy matching.",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name (or part of the name) of the person to find (first name, last name, or full name).",
            },
        },
        "required": ["name"],
    },
}

def find_person_by_name(name: str) -> dict:
    """Find person by name using fuzzy matching (RapidFuzz)."""
    db = get_db_conn()
    # Get all persons
    persons = db.execute("SELECT person_id, first_name, last_name, age, gender FROM persons").fetchall()
    # Create full names for matching
    person_names = [f"{p[1]} {p[2]}" for p in persons]
    # Use rapidfuzz to find best match
    match = extractOne(
        name,
        person_names,
        scorer=fuzz.WRatio,
        score_cutoff=60,
        processor=lambda x: x.lower()
    )
    if not match:
        return {"error": f"No person found matching '{name}'"}
    for p in persons:
        if f"{p[1]} {p[2]}" == match[0]:
            return {
                "person_id": str(p[0]),
                "first_name": str(p[1]),
                "last_name": str(p[2]),
                "full_name": match[0],
                "age": int(p[3]),
                "gender": str(p[4]),
                "match_score": match[1],
            }
    return {"error": f"No person found matching '{name}'"}

FIND_PROGRAM_BY_NAME_TOOL_DEF = {
    "name": "find_program_by_name",
    "description": "Find a clinical program by its name using fuzzy matching.",
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
    """Find clinical program by name using fuzzy matching (RapidFuzz)."""
    db = get_db_conn()
    # Get all program names and ids
    programs = db.execute("SELECT program_id, program_name, phase, description FROM programs").fetchall()
    program_names = [p[1] for p in programs]
    # Use rapidfuzz to find best match
    match = extractOne(
        program_name,
        program_names,
        scorer=fuzz.WRatio,
        score_cutoff=60,
        processor=lambda x: x.lower()
    )
    if not match:
        return {"error": f"No program found matching '{program_name}'"}
    for p in programs:
        if p[1] == match[0]:
            return {
                "program_id": str(p[0]),
                "program_name": str(p[1]),
                "phase": str(p[2]),
                "description": str(p[3]),
                "match_score": match[1],
            }
    return {"error": f"No program found matching '{program_name}'"}

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

FIND_PROGRAMS_FOR_CANDIDATE_TOOL_DEF = {
    "name": "find_programs_for_candidate",
    "description": "Find all clinical programs that a candidate is eligible for based on their medical profile.",
    "parameters": {
        "type": "object",
        "properties": {
            "person_id": {
                "type": "string",
                "description": "The ID of the person/candidate to find eligible programs for (e.g., P001).",
            },
        },
        "required": ["person_id"],
    },
}

def find_programs_for_candidate(person_id: str) -> dict:
    """Find all clinical programs that a candidate is eligible for using SQL."""
    db = get_db_conn()

    # Get candidate details first
    candidate = db.execute("SELECT person_id, first_name, last_name, age, gender FROM persons WHERE person_id = ?", [person_id]).fetchone()
    if not candidate:
        return {"error": f"Candidate {person_id} not found"}

    # Single query with CROSS JOIN to check all programs
    results = db.execute("""
        SELECT p.program_id, p.program_name, p.phase, p.description,
               p.required_conditions, p.excluded_conditions, p.required_medications, p.excluded_medications,
               c.diabetes, c.hypertension, c.heart_disease, c.asthma, c.copd, c.kidney_disease,
               c.cancer_history, c.medications
        FROM programs p
        CROSS JOIN persons c
        WHERE c.person_id = ?
          AND (p.min_age IS NULL OR c.age >= p.min_age)
          AND (p.max_age IS NULL OR c.age <= p.max_age)
          AND (p.eligible_genders IS NULL OR CONTAINS(p.eligible_genders, c.gender))
          AND (p.min_bmi IS NULL OR c.bmi >= p.min_bmi)
          AND (p.max_bmi IS NULL OR c.bmi <= p.max_bmi)
          AND (p.smoking_allowed IS NULL OR CONTAINS(p.smoking_allowed, c.smoking_status))
          AND (p.min_hemoglobin_a1c IS NULL OR c.hemoglobin_a1c >= p.min_hemoglobin_a1c)
          AND (p.max_hemoglobin_a1c IS NULL OR c.hemoglobin_a1c <= p.max_hemoglobin_a1c)
          AND (p.min_egfr IS NULL OR c.egfr >= p.min_egfr)
          AND (p.max_egfr IS NULL OR c.egfr <= p.max_egfr)
    """, [person_id]).fetchall()

    eligible_programs = []

    # Only need to check complex conditions/medications in Python
    for row in results:
        conditions_map = {"diabetes": row[8], "hypertension": row[9], "heart_disease": row[10],
                         "asthma": row[11], "copd": row[12], "kidney_disease": row[13]}
        cancer_history = row[14]
        medications = row[15] or ""

        eligible = True

        # Check required/excluded conditions
        if row[4]:  # required_conditions
            for cond in row[4].split(";"):
                if cond in conditions_map and conditions_map[cond] != "yes":
                    eligible = False
                    break
                elif cond not in conditions_map and cancer_history != cond:
                    eligible = False
                    break

        if eligible and row[5]:  # excluded_conditions
            for cond in row[5].split(";"):
                if cond in conditions_map and conditions_map[cond] == "yes":
                    eligible = False
                    break
                elif cond not in conditions_map and cancer_history == cond:
                    eligible = False
                    break

        # Check required/excluded medications
        if eligible and row[6]:  # required_medications
            if not all(med in medications for med in row[6].split(";")):
                eligible = False

        if eligible and row[7]:  # excluded_medications
            if any(med in medications for med in row[7].split(";")):
                eligible = False

        if eligible:
            eligible_programs.append({
                "program_id": str(row[0]),
                "program_name": str(row[1]),
                "phase": str(row[2]),
                "description": str(row[3]),
            })

    return {
        "person_id": str(candidate[0]),
        "name": f"{candidate[1]} {candidate[2]}",
        "age": int(candidate[3]),
        "gender": str(candidate[4]),
        "total_eligible_programs": len(eligible_programs),
        "eligible_programs": eligible_programs,
    }
