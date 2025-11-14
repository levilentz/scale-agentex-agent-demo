import os
import json
from typing import AsyncGenerator, List, Optional, Any, Literal

from dotenv import load_dotenv, find_dotenv
from pydantic import BaseModel

from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.acp import SendMessageParams
from agentex.types.task_message_update import TaskMessageUpdate
from agentex.types.task_message_content import TaskMessageContent
from agentex.types.text_content import TextContent
from agentex.lib.utils.logging import make_logger
from agentex.lib import adk

from .clients.sgp_client import async_sgp_client

# Load environment variables from .env file local or parent directories
load_dotenv(find_dotenv())

logger = make_logger(__name__)

# Create an ACP server
acp = FastACP.create(
    acp_type="sync",
)

MODEL = "gemini/gemini-2.5-flash"


class StateModel(BaseModel):
    input_list: List[dict]
    turn_number: int


# ============================================================================
# Web Search Implementation with DuckDuckGo
# ============================================================================

async def search_web_duckduckgo(query: str, max_results: int = 5):
    """
    Perform web search using DuckDuckGo (free, no API key needed)

    Args:
        query: Search query
        max_results: Maximum number of results to return

    Returns:
        List of search results with title, link, and snippet
    """
    try:
        from ddgs import DDGS

        results = []
        ddgs = DDGS()

        # Use the text search method
        search_results = ddgs.text(query, max_results=max_results)

        for r in search_results:
            results.append({
                "title": r.get("title", ""),
                "link": r.get("href", r.get("link", "")),
                "snippet": r.get("body", r.get("snippet", ""))
            })

        return results if results else [{"info": "No results found"}]

    except ImportError:
        logger.error("ddgs package not installed")
        return [{
            "error": "ddgs not installed. Install with: uv pip install ddgs"
        }]
    except Exception as e:
        logger.error(f"Web search error: {str(e)}")
        import traceback
        return [{"error": str(e), "traceback": traceback.format_exc()}]


async def run_gemini_with_web_search(
    messages: List[dict],
    max_search_results: int = 5,
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """
    Run Gemini with web search tool via SGP client.

    Args:
        messages: List of message dicts with role and content
        max_search_results: Maximum number of search results per query
        temperature: Model temperature
        max_tokens: Maximum tokens in response

    Returns:
        The assistant's response text
    """

    # Define custom web search tool
    tool_def = {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current, up-to-date information on any topic",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to look up"
                    }
                },
                "required": ["query"]
            }
        }
    }

    tools = [tool_def]

    logger.info(f"📤 Sending request to Gemini with web search tool")

    # First request - model decides if it needs to search
    response = await async_sgp_client.beta.chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    logger.info(f"🤖 Response: {response}")

    message = response.choices[0].message

    # Check if model wants to use the tool
    if hasattr(message, 'tool_calls') and message.tool_calls:
        logger.info(f"🔧 Model requested {len(message.tool_calls)} tool call(s)")

        # Build conversation with tool responses
        conversation = messages.copy()
        conversation.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        })

        # Execute tool calls
        for tool_call in message.tool_calls:
            args = json.loads(tool_call.function.arguments)
            search_query = args.get('query', '')

            logger.info(f"🔍 Searching: '{search_query}'")

            # Execute the actual web search!
            search_results = await search_web_duckduckgo(search_query, max_results=max_search_results)

            logger.info(f"✅ Found {len(search_results)} results")

            # Format results for the model
            tool_result = {
                "query": search_query,
                "results": search_results
            }
            logger.info(f"🔍 Tool result: {tool_result}")

            conversation.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(tool_result)
            })

        logger.info(f"🤖 Conversation: {conversation}")
        # Get final response with tool results
        logger.info(f"🤖 Generating final answer with search results...")

        final_response = await async_sgp_client.beta.chat.completions.create(
            model=MODEL,
            messages=conversation,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.info(f"🤖 Final response: {final_response}")

        response_text = final_response.choices[0].message.content
    else:
        logger.info("💭 Model didn't request tool use")
        response_text = message.content

    
    return response_text


def parse_messages_to_text_content(input_list: list[dict]) -> list[TextContent]:
    """
    Parse the input list into TextContent objects.

    Handles:
    - User messages: {'role': 'user', 'content': 'text'}
    - Assistant messages: {'role': 'assistant', 'content': [{'text': '...'}]}
    - Skips reasoning objects and other non-message types

    Args:
        input_list: List of message dictionaries from agent response

    Returns:
        List of TextContent objects
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
            # Assistant message: content could be a string or list
            content = item.get("content", "")
            if isinstance(content, str):
                if content:
                    text_messages.append(TextContent(author="agent", content=content))
            elif isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict):
                        text = content_item.get("text", "")
                        if text:
                            text_messages.append(
                                TextContent(author="agent", content=text)
                            )

    return text_messages


@acp.on_message_send
async def handle_message_send(
    params: SendMessageParams,
) -> (
    TaskMessageContent
    | list[TaskMessageContent]
    | AsyncGenerator[TaskMessageUpdate, None]
):
    """
    Handle incoming messages with web search via custom Gemini implementation.

    This uses the SGP client directly with custom web search tool.
    """

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

    # Add the new user message to the message history
    state.input_list.append({"role": "user", "content": message_text})

    try:
        # Run Gemini with web search capability
        response_text = await run_gemini_with_web_search(
            messages=state.input_list,
            max_search_results=5,  # Control number of search results here!
            temperature=0.7,
            max_tokens=1000,
        )

        if response_text is None: 
            response_text = "Sorry, I encountered when searching the web. Please try again."

        # Add assistant response to state
        state.input_list.append({"role": "assistant", "content": response_text})

        logger.info("✅ Response generated successfully")
        # Return the response as TextContent
        return TextContent(
            author="agent",
            content=response_text,
        )

    except Exception as e:
        logger.error(f"❌ Error handling message: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

        return TextContent(
            author="agent",
            content=f"Sorry, I encountered an error: {str(e)}\n\nPlease make sure:\n1. The SGP credentials are properly configured\n2. The ddgs package is installed (uv pip install ddgs)",
        )
