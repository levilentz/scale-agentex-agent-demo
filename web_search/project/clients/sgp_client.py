from scale_gp import SGPClient, AsyncSGPClient
import os
import httpx

# Environment variables for SGP configuration
SGP_API_KEY = os.getenv("SGP_API_KEY")
SGP_BASE_URL = os.getenv("SGP_BASE_URL")
SGP_ACCOUNT_ID = os.getenv("SGP_ACCOUNT_ID")

# Additional configuration
max_retries = int(os.getenv("SGP_MAX_RETRIES", 3))
timeout = float(os.getenv("SGP_TIMEOUT", 60.0))

# Create HTTP clients with SSL verification disabled
# (matching openai_client pattern)
http_client = httpx.Client(verify=False)
async_http_client = httpx.AsyncClient(verify=False)

# Create the synchronous SGP client instance
# The SGPClient will automatically use SGP_API_KEY and
# SGP_ACCOUNT_ID from environment if they are set, but we can
# also pass them explicitly
sgp_client = SGPClient(
    api_key=SGP_API_KEY,
    account_id=SGP_ACCOUNT_ID,
    base_url=SGP_BASE_URL,
    max_retries=max_retries,
    timeout=timeout,
    http_client=http_client,
)

# Create the async SGP client instance for use in async contexts
async_sgp_client = AsyncSGPClient(
    api_key=SGP_API_KEY,
    account_id=SGP_ACCOUNT_ID,
    base_url=SGP_BASE_URL,
    max_retries=max_retries,
    timeout=timeout,
    http_client=async_http_client,
)
