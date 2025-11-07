# Building Your First AgentEx Agent: Web Search Agent

## What You'll Build

**Agent Goal:** Build an agent that can search the web to answer questions using real-time information from the internet.

**What you'll learn:**

- How to initialize an AgentEx project
- How to configure agent dependencies
- How to set up environment variables
- How to customize the `acp.py` file to define agent behavior

---

The below steps are useful for reference or for creating you own custom agent.

## Prerequisites

Before starting this tutorial, make sure you have:

- [ ] **AgentEx installed** and running on your local machine
- [ ] **Python 3.12+** installed
- [ ] **The agentex-sdk** installed [see here](https://github.com/scaleapi/scale-agentex)
**New to AgentEx?** Check the [AgentEx documentation](https://docs.agentex.com) for installation instructions.

---

## Part 1: Set Up Environment Variables

### Step 1: Create the .env File

Your agent needs API keys to function. These should be stored in a `.env` file (which is automatically ignored by git for security).

**Create the file:**

```bash
# Create .env file in the project root
touch .env
```

### Step 2: Add Your API Keys

**Open `.env` in your text editor and add:**

```bash
SGP_API_KEY=SGP_API_KEY
SGP_BASE_URL=SGP_BASE_URL
SGP_ACCOUNT_ID=SGP_ACCOUNT_ID
```

### Step 3: Load Environment Variables (Optional)

If you want to test that your environment variables are loaded:

```bash
source .env
echo SGP_API_KEY  # Should print your API key
```

**Note:** The `load_dotenv()` function in `acp.py` automatically loads these variables, so this step is optional.

---

## Part 3: Configure Dependencies

The `pyproject.toml` file defines your project's dependencies. The `agentex init` command creates this file, but you may need to verify or update it.

### Step 1: Open pyproject.toml

**Location:** `web-search/pyproject.toml`

### Step 2: Verify Dependencies

Your `pyproject.toml` should look like this:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "web_search"
version = "0.1.0"
description = "An AgentEx agent"
requires-python = ">=3.12"
readme = "README.md"
dependencies = [
    "agentex-sdk",
    "scale-gp",
    "openai>=1.0.0",
    "mcp>=1.0.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "black",
    "isort",
    "flake8",
]

[tool.hatch.build.targets.wheel]
packages = ["project"]

[tool.black]
line-length = 88
target-version = ['py312']

[tool.isort]
profile = "black"
line_length = 88
```

### Step 3: Understanding the Dependencies

**Core dependencies (required):**

- **`agentex-sdk`**: The AgentEx framework for building agents
- **`scale-gp`**: Scale AI's platform utilities
- **`openai>=1.0.0`**: OpenAI Python SDK for AI models
- **`mcp>=1.0.0`**: Model Context Protocol for tool integration
- **`python-dotenv>=1.0.0`**: Load environment variables from .env

**Development dependencies (optional, for code quality):**

- **`pytest`**: Testing framework
- **`black`**: Code formatter
- **`isort`**: Import statement organizer
- **`flake8`**: Code linter

### Step 4: Install Dependencies

**If using `uv` (recommended):**

```bash
uv sync
```

**If using `pip`:**

```bash
pip install -e .
```

**What this does:**

- Installs all dependencies listed in `pyproject.toml`
- Creates a virtual environment (if using `uv`)
- Makes your agent package importable

---

## Part 4: Fill Out the acp.py File

The `acp.py` file is the main entry point for your agent. It comes with pre-defined function structures (marked with `@acp` decorators). You'll be copying and pasting specific code blocks to make your web search agent work.

**Location:** `project/acp.py`

---

## Step 1: Import Required Libraries (Lines 1-16)

Some of these imports are **already provided** when you run `agentex init`.

**Verify your file has these imports:**

```python
import os
from typing import AsyncGenerator, List, Optional, Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel

from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.acp import SendMessageParams
from agentex.types.task_message_update import TaskMessageUpdate
from agentex.types.task_message_content import TaskMessageContent
from agentex.types.text_content import TextContent
from agentex.lib.utils.logging import make_logger
from agentex.lib import adk
from agents.tool import WebSearchTool as OAIWebSearchTool
from agents import Tool
```

✅ **If these imports are already in your file, move to Step 2.**

---

## Step 2: Set Up Environment Variables and Logging (Lines 17-20)

These lines are **already provided** by the framework.

**Verify your file has:**

```python
# Load environment variables from .env file
load_dotenv()

logger = make_logger(__name__)
```

✅ **If these lines are already in your file, move to Step 3.**

**Note:** Make sure your `.env` file exists with your required keys (completed in Part 2).

---

## Step 4: Define Your Agent's Memory (StateModel) (Lines 28-31)

**Copy and paste this code** into your `acp.py` file around line 28:

```python
class StateModel(BaseModel):
    input_list: List[dict]
    turn_number: int
```

**What this does:** Defines how your agent remembers information between messages.

- `input_list`: Stores the conversation history
- `turn_number`: Tracks conversation turns

✅ **Once copied, move to Step 5.**

---

## Step 5: Configure Your Tools (Lines 33-50)

**Copy and paste this code** into your `acp.py` file around line 33:

```python
class WebSearchTool(BaseModel):
    user_location: Optional[dict[str, Any]] = None
    search_context_size: Optional[Literal["low", "medium", "high"]] = "medium"

    def to_oai_function_tool(self) -> OAIWebSearchTool:
        kwargs = {}
        if self.user_location is not None:
            kwargs["user_location"] = self.user_location
        if self.search_context_size is not None:
            kwargs["search_context_size"] = self.search_context_size
        return OAIWebSearchTool(**kwargs)


WEB_SEARCH_TOOL = WebSearchTool(
    user_location={"type": "approximate", "city": "Seattle", "country": "US"},
    search_context_size="medium",
)
```

**What this does:** Configures the web search tool that your agent will use to search the internet.

✅ **Once copied, move to Step 6.**

---

## Step 6: Helper Functions (Lines 52-98)

**Copy and paste this function** into your `acp.py` file around line 52:

```python
def parse_messages_to_text_content(input_list: list[dict]) -> list[TextContent]:
    """
    Parse the input list into TextContent objects.

    Handles:
    - User messages: {'role': 'user', 'content': 'text'}
    - Assistant messages: {'role': 'assistant', 'content': [{'text': '...'}]}
    - Skips reasoning objects and other non-message types
    """
    text_messages = []

    for item in input_list:
        if not isinstance(item, dict):
            continue

        role = item.get("role")

        # Skip items without a role (reasoning objects, etc.)
        if not role:
            continue

        if role == "user":
            # User message: content is a string
            content = item.get("content", "")
            if content:
                text_messages.append(TextContent(author="user", content=content))

        elif role == "assistant":
            # Assistant message: content is a list with text objects
            content_list = item.get("content", [])
            if isinstance(content_list, list):
                for content_item in content_list:
                    if isinstance(content_item, dict):
                        text = content_item.get("text", "")
                        if text:
                            text_messages.append(
                                TextContent(author="agent", content=text)
                            )

    return text_messages
```

**What this does:** Converts message data into a format the framework can display.

✅ **Once copied, move to Step 7.**

---

## Step 7: The Main Message Handler (Lines 100-193)

**This is the heart of your agent!**

\*\*Copy and overwrite the existing handle_message_send in your `acp.py` file starting around line 100:

```python
@acp.on_message_send
async def handle_message_send(
    params: SendMessageParams,
) -> (
    TaskMessageContent
    | list[TaskMessageContent]
    | AsyncGenerator[TaskMessageUpdate, None]
):
    """
    Handle incoming messages with web search via OpenAI MCP server.

    This uses the openai-websearch-mcp server to perform web searches.
    """

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        return TextContent(
            author="agent",
            content="❌ OpenAI API key is missing. Please set OPENAI_API_KEY in your .env file.",
        )

    # Extract message text
    message_text = ""
    if hasattr(params.content, "content"):
        content_val = getattr(params.content, "content", "")
        if isinstance(content_val, str):
            message_text = content_val

    if not message_text:
        return TextContent(
            author="agent",
            content="Please provide a message.",
        )

    logger.info(f"📨 Received message: {message_text}")

    task = await adk.tasks.get(task_id=params.task.id)
    task_state = await adk.state.get_by_task_and_agent(
        task_id=params.task.id, agent_id=params.agent.id
    )
    if not task_state:
        # If the state doesn't exist, create it.
        state = StateModel(input_list=[], turn_number=0)
        task_state = await adk.state.create(
            task_id=params.task.id, agent_id=params.agent.id, state=state
        )
    else:
        state = StateModel.model_validate(task_state.state)

    # Increment turn number
    state.turn_number += 1

    # Decode and add the new user message to the message history
    user_prompt = message_text
    state.input_list.append({"role": "user", "content": user_prompt})

    try:
        agent_name = "Web Search Agent"
        agent_instructions = """
            You are a helpful agent that answers questions about a range of topics. Your strength is that you can search the web.
            You have access to the following tools:
           - web_search: Search the internet for answers to the questions

            When using web search, always cite your sources with links. Use web search to:
            - Find up-to-date information on topics

            Always be professional, empathetic, and ensure that your answers are accurate and well-cited.
        """
        # Setup agent with tools
        tools: List[Tool] = [WEB_SEARCH_TOOL]

        result = await adk.providers.openai.run_agent_auto_send(
            task_id=task.id,
            trace_id=task.id,
            input_list=state.input_list,
            agent_name=agent_name,
            agent_instructions=agent_instructions,
            model="gpt-4o-mini",
            tools=tools,
        )

        logger.info("✅ Response generated successfully")
        inputs = result.to_input_list()

        # Parse and return all messages as TextContent objects
        return parse_messages_to_text_content(inputs)

    except Exception as e:
        logger.error(f"❌ Error handling message: {str(e)}")
        return TextContent(
            author="agent",
            content=f"Sorry, I encountered an error: {str(e)}\n\nPlease make sure:\n1. Your OPENAI_API_KEY is set in .env\n2. The openai-websearch-mcp package is available (it will be installed automatically via uvx)",
        )
```

**What this does:** Handles incoming messages, manages conversation state, and calls the AI model with web search capabilities.

✅ **Once copied, your agent is complete!**

---

## Quick Recap

Here's what you should have in your `acp.py` file after following Steps 1-7:

- [ ] **Step 1**: Imports (lines 1-16) - ✅ Already provided
- [ ] **Step 2**: Environment setup (lines 17-20) - ✅ Already provided
- [ ] **Step 3**: ACP server creation (lines 22-25) - ✅ Already provided
- [ ] **Step 4**: StateModel class (lines 28-31) - Copied from Step 4
- [ ] **Step 5**: WebSearchTool configuration (lines 33-50) - Copied from Step 5
- [ ] **Step 6**: Helper function (lines 52-98) - Copied from Step 6
- [ ] **Step 7**: Main handler function (lines 100-193) - Copied from Step 7

**Your agent is now ready to run!**

---

## Testing Your Agent

Now that you've copied all the code blocks, let's test your agent!

### 1. Verify your `.env` file exists:

```bash
# Should show your OPENAI_API_KEY
cat .env
```

If not, create it:

```bash
echo "OPENAI_API_KEY=your-api-key-here" > .env
```

### 2. Install dependencies:

```bash
uv sync
```

### 3. Run the agent:

```bash
agentex agents run --manifest manifest.yaml
```

You should see output like:

```
🚀 Starting agent...
✓ Agent is running on http://localhost:8000
```

### 4. Test with the Jupyter Notebook:

Use the included `dev.ipynb` notebook to test your agent:

```bash
# Install Jupyter if you don't have it
pip install jupyter

# Start Jupyter notebook
jupyter notebook dev.ipynb
```

Your browser will open with the notebook. Now run each cell:

**Cell 1: Connect to your agent**

```python
from agentex import Agentex

client = Agentex(base_url="http://localhost:5003")
```

**Cell 2: Set your agent name**

```python
AGENT_NAME = "web-search"
```

**Cell 3: Create a task (Optional)**

```python
# Creates a new task to maintain conversation context
import uuid

TASK_ID = str(uuid.uuid4())[:8]

rpc_response = client.agents.rpc_by_name(
    agent_name=AGENT_NAME,
    method="task/create",
    params={"name": f"{TASK_ID}-task", "params": {}}
)

task = rpc_response.result
print(task)
```

**Cell 4: Send a non-streaming message**

```python
# Test basic message sending
rpc_response = client.agents.send_message(
    agent_name=AGENT_NAME,
    params={
        "content": {"type": "text", "author": "user", "content": "What's the weather like in San Francisco today?"},
        "stream": False
    }
)

for task_message in rpc_response.result:
    content = task_message.content
    if isinstance(content, TextContent):
        print(content.content)
```

### 5. Verify it works:

After running the cells, you should see:

- **Cell 3 output**: A Task object with an ID and status
- **Cell 4 output**: A response about San Francisco weather with sources

## For Reference: Create A New Agent Project 

### Step 1: Navigate to Your Working Directory

Choose where you want to create your agent and navigate there:

```bash
cd ~/your-projects-folder
```

### Step 2: Initialize the Agent Project

Run the AgentEx initialization command:

```bash
agentex init
```

You'll be prompted with several questions. Here's how to answer them:

```
? What type of template would you like to create? Sync ACP
? Where would you like to create your project? .
? What's your agent name? (letters, numbers, and hyphens only) web-search
? What do you want to name the project folder for your agent? web-search
? Provide a brief description of your agent: An AgentEx agent
? Would you like to use uv for package management? Yes (Recommended)

✓ Created project structure at: /Users/roxanne.farhad/Desktop/scale/tmo-demos/web_search

✨ Project created successfully!
```

**Your project structure will look like this:**

```
web-search/
├── project/
│   └── acp.py          # Main agent logic (this is what you'll customize!)
├── manifest.yaml       # Deployment configuration
├── pyproject.toml      # Python dependencies
├── dev.ipynb          # Jupyter notebook for testing your agent
├── README.md          # This tutorial
└── .env               # Environment variables (you'll create this)
```

### Step 3: Navigate into Your Project

```bash
cd web-search
```

---
