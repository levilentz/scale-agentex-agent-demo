# Clinical Trial Enrollment Agent

An AI-powered clinical research coordinator that helps match patients to clinical trials from dummy csv data.

## Features

- **List Clinical Programs**: Browse all available clinical trials
- **Search by Name**: Find specific programs using natural language queries
- **Candidate Matching**: Automatically match patients to trials based on:
  - Demographics (age, gender, BMI)
  - Medical conditions (diabetes, hypertension, heart disease, etc.)
  - Lab values (HbA1c, eGFR, cholesterol, blood pressure)
  - Medications (required and excluded)
  - Lifestyle factors (smoking status)

## Example Queries

Try these queries with the agent:

- "List all available clinical programs"
- "Find the diabetes program"
- "Who is eligible for the diabetes program?"
- "Show me candidates for the asthma control w/ biologic therapy program"
- "Are there any trials for patients with hypertension?"

## Quick Start

See the [root README](../README.md) for Docker-based setup.

## Data

The agent uses two CSV files in the [./data](./data) directory containing synthetic data:

### Clinical Programs (`clinical_programs.csv`)

Contains 15 clinical trial programs with eligibility criteria:

| Column | Type | Description |
|--------|------|-------------|
| program_id | VARCHAR | Unique identifier (e.g., CP001) |
| program_name | VARCHAR | Name of the clinical trial |
| phase | VARCHAR | Trial phase (I, II, III, IV) |
| description | VARCHAR | Trial description |
| min_age / max_age | BIGINT | Age requirements |
| eligible_genders | VARCHAR | M, F, or Both |
| required_conditions | VARCHAR | Medical conditions required (semicolon-separated) |
| excluded_conditions | VARCHAR | Disqualifying conditions |
| min_bmi / max_bmi | BIGINT | BMI range |
| smoking_allowed | VARCHAR | Smoking status restrictions |
| min/max_hemoglobin_a1c | DOUBLE | HbA1c range (diabetes indicator) |
| min/max_egfr | BIGINT | Kidney function range |
| required_medications | VARCHAR | Required current medications |
| excluded_medications | VARCHAR | Disqualifying medications |
| max_participants | BIGINT | Trial capacity |

### Patient Records (`persons.csv`)

Contains 100 synthetic patient records:

| Column | Type | Description |
|--------|------|-------------|
| person_id | VARCHAR | Unique identifier |
| first_name / last_name | VARCHAR | Patient name |
| age | BIGINT | Age in years |
| gender | VARCHAR | M or F |
| bmi | DOUBLE | Body Mass Index |
| smoking_status | VARCHAR | Never, Former, Current |
| diabetes / hypertension / heart_disease / asthma / copd / kidney_disease | BOOLEAN | Medical conditions |
| cancer_history | VARCHAR | Cancer type or "none" |
| hemoglobin_a1c | DOUBLE | HbA1c percentage |
| ldl_cholesterol | BIGINT | LDL cholesterol level |
| systolic_bp / diastolic_bp | BIGINT | Blood pressure |
| egfr | BIGINT | Estimated glomerular filtration rate |
| medications | VARCHAR | Current medications (semicolon-separated) |

## Tools

The agent has access to three tools:

- `list_all_programs()` - Returns all clinical programs with their criteria
- `find_program_by_name(program_name: str)` - Searches for programs by name
- `find_candidates_for_program(program_id: str)` - Finds eligible patients for a specific program

### Adding New Tools

1. Define your function in `tools.py` with type hints:
   ```python
   def my_new_tool(param: str) -> dict:
       """Tool description for the LLM."""
       # Your logic here
       return {"result": "data"}
   ```

2. Create the tool definition (see [documentation](https://scale-egp.readme.io/reference/post-v4-v2agentsexecute-1)):
   ```python
   MY_TOOL_DEF = function_to_tool_dict(my_new_tool)
   ```

3. Add to `AGENT_TOOLS` in `acp.py`:
   ```python
   AGENT_TOOLS = [
       (my_new_tool, MY_TOOL_DEF),
       # ... other tools
   ]
   ```

4. Update `AGENT_INSTRUCTIONS` to describe the new tool to the LLM