# Enrollment Demo

## Set Up Environment

Set up your .env file.
```bash
SGP_BASE_URL=
SGP_ACCOUNT_ID=
SGP_API_KEY=
```

## Running Locally

**Tab 1: Backend**
```bash
cd ~/agentex-sdk
uv sync
make dev
```

**Tab 2: Agents**
```bash
cd $THIS_DIRECTORY
uv sync
uv run agentex agents run --manifest manifest.yaml
```

**Tab 3: Front-end**
```bash
cd ~/agentex-sdk/agentex-ui
make install
make dev
```

# Data

For this demo, the data is in two CSV files in the `./data` directory. This is dummy data.

The structure of each CSV is below:

```bash
duckdb :memory: "DESCRIBE TABLE  'data/clinical_programs.csv';"
```

|     column_name      | column_type |
|----------------------|-------------|
| program_id           | VARCHAR     |
| program_name         | VARCHAR     |
| phase                | VARCHAR     |
| description          | VARCHAR     |
| min_age              | BIGINT      |
| max_age              | BIGINT      |
| eligible_genders     | VARCHAR     |
| required_conditions  | VARCHAR     |
| excluded_conditions  | VARCHAR     |
| min_bmi              | BIGINT      |
| max_bmi              | BIGINT      |
| smoking_allowed      | VARCHAR     |
| min_hemoglobin_a1c   | DOUBLE      |
| max_hemoglobin_a1c   | DOUBLE      |
| min_egfr             | BIGINT      |
| max_egfr             | BIGINT      |
| required_medications | VARCHAR     |
| excluded_medications | VARCHAR     |
| max_participants     | BIGINT      |

```bash
duckdb :memory: "DESCRIBE TABLE  'data/persons.csv';"
```

|   column_name   | column_type |
|-----------------|-------------|
| person_id       | VARCHAR     |
| first_name      | VARCHAR     |
| last_name       | VARCHAR     |
| age             | BIGINT      |
| gender          | VARCHAR     |
| bmi             | DOUBLE      |
| smoking_status  | VARCHAR     |
| diabetes        | BOOLEAN     |
| hypertension    | BOOLEAN     |
| heart_disease   | BOOLEAN     |
| cancer_history  | VARCHAR     |
| asthma          | BOOLEAN     |
| copd            | BOOLEAN     |
| kidney_disease  | BOOLEAN     |
| hemoglobin_a1c  | DOUBLE      |
| ldl_cholesterol | BIGINT      |
| systolic_bp     | BIGINT      |
| diastolic_bp    | BIGINT      |
| egfr            | BIGINT      |
| medications     | VARCHAR     |
