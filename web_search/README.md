# Web Search Agent

An AI agent that can search the web using DuckDuckGo to answer questions with current, up-to-date information.

## Overview

This agent demonstrates how to give an LLM access to real-time web search capabilities. It uses DuckDuckGo's free search API (no API key required) as a tool that Gemini can call when it needs current information to answer questions.

## Quick Start

See the [root README](../README.md) for setup instructions. Once running, browse to [http://localhost:3000](http://localhost:3000) to interact with the agent.

## Example Queries

- "What's the weather in San Francisco today?"
- "Who won the Super Bowl this year?"
- "What are the latest developments in AI?"
- "Find me recent news about SpaceX"

## Architecture

- **[`acp.py`](project/acp.py)** - Agent handler using Scale AgentEx SDK and Gemini via SGP
- **DuckDuckGo Search** - Free web search (via `ddgs` Python package)
- **Gemini** - LLM that decides when to use web search and synthesizes results

## How It Works

1. User sends a question to the agent
2. Gemini receives the question and available tools (including `web_search`)
3. If Gemini determines it needs current info, it calls the `web_search` tool
4. The agent executes a DuckDuckGo search and returns results to Gemini
5. Gemini synthesizes the search results into a natural language answer
6. The answer is returned to the user

## Key Components

**Web Search Tool** ([acp.py:39-77](project/acp.py#L39-L77))
```python
async def search_web_duckduckgo(query: str, max_results: int = 5)
```
- Uses DuckDuckGo free search API
- Returns title, link, and snippet for each result
- No API key required

**Tool Definition** ([acp.py:99-115](project/acp.py#L99-L115))
- Describes the `web_search` function to Gemini
- LLM decides when to call it based on the description

**Agent Loop** ([acp.py:79-209](project/acp.py#L79-L209))
- Sends messages to Gemini with tool definitions
- Detects when Gemini wants to use tools
- Executes searches and returns results
- Gets final answer with search context

## Dependencies

- **`agentex-sdk`** - Scale AgentEx framework
- **`scale-gp`** - SGP client for Gemini access
- **`ddgs`** - DuckDuckGo search library (free, no API key)
- **`python-dotenv`** - Environment variable management

Install with:
```bash
uv sync
```

## Configuration

Requires SGP credentials in `.env` file (see [root README](../README.md)):
```bash
SGP_API_KEY=your_key
SGP_BASE_URL=your_url
SGP_ACCOUNT_ID=your_account_id
```

The agent uses `gemini/gemini-2.5-flash` by default (configured in [acp.py:27](project/acp.py#L27)).
