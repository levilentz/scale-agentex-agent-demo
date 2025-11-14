# Patient Enrollment Agent

An AI agent that answers natural language queries about clinical trial eligibility using structured data from CSV files.

## Overview

This agent acts as a clinical research coordinator, helping match patients to clinical trials based on eligibility criteria like demographics, medical conditions, lab values, and medications. It demonstrates how to build an agent that queries structured data (CSVs loaded into DuckDB) to answer complex natural language questions.

## Quick Start

See the [root README](../README.md) for setup instructions. Once running, browse to [http://localhost:3000](http://localhost:3000) to interact with the agent.

## Example Queries

- "List all available clinical programs"
- "Find the diabetes program"
- "Who is eligible for CP001?"
- "What trials is John Smith eligible for?"
- "Show me candidates for the asthma program"

## Data

The agent works with two synthetic CSV datasets in `./data`:

- **`clinical_programs.csv`** - 15 clinical trial programs with eligibility criteria (age, gender, BMI, medical conditions, medications, lab values)
- **`persons.csv`** - 100 synthetic patient records with demographics and medical profiles

## Available Tools

The agent has 5 tools defined in [`tools.py`](project/tools.py):

1. **`list_all_programs()`** - List all clinical programs
2. **`find_program_by_name(program_name)`** - Find programs by name (fuzzy matching)
3. **`find_person_by_name(name)`** - Find patients by name (fuzzy matching)
4. **`find_candidates_for_program(program_id)`** - Find eligible patients for a program
5. **`find_programs_for_candidate(person_id)`** - Find eligible programs for a patient

## Architecture

- **[`acp.py`](project/acp.py)** - Agent handler using Scale AgentEx SDK and Gemini via SGP
- **[`tools.py`](project/tools.py)** - Tool definitions and SQL-based eligibility matching logic
- **DuckDB** - In-memory database for fast SQL queries on CSV data
- **RapidFuzz** - Fuzzy string matching for name searches

## Adding New Tools

1. Define your function in [`tools.py`](project/tools.py):
   ```python
   def my_tool(param: str) -> dict:
       """Description for the LLM."""
       return {"result": "data"}
   ```

2. Create the tool definition dict:
   ```python
   MY_TOOL_DEF = {
       "name": "my_tool",
       "description": "What this tool does",
       "parameters": {
           "type": "object",
           "properties": {
               "param": {"type": "string", "description": "Parameter description"}
           },
           "required": ["param"]
       }
   }
   ```

3. Add to `AGENT_TOOLS` in [`acp.py`](project/acp.py):
   ```python
   AGENT_TOOLS = [
       (my_tool, MY_TOOL_DEF),
       # ... existing tools
   ]
   ```

4. Update `AGENT_INSTRUCTIONS` to document the tool for the LLM
