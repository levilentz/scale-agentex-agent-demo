# Makefile for Web Search Agent
# Usage:
#   make run-agent    - Run the agent locally

.PHONY: run-agent help

# Default target
help:
	@echo "Product Agent Makefile Commands:"
	@echo "  make run-agent    - Run the agent locally on port 8000"
	@echo ""
	@echo "Ensure you have the following environment variables set in .env:"
	@echo "  - SGP_API_KEY"
	@echo "  - SGP_BASE_URL"
	@echo "  - SGP_ACCOUNT_ID"

# Run the agent
run-agent:
	@echo "======================================"
	@echo "Starting Web Search Agent..."
	@echo "======================================"
	@echo ""
	@echo "Starting agent on port 8000..."
	@echo "Press Ctrl+C to stop the agent"
	@echo ""
	ENVIRONMENT=development uv run agentex agents run --manifest manifest.yaml

# Alternative target names for convenience
run: run-agent