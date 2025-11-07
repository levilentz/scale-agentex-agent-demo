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
from agents import Tool, set_default_openai_client, set_default_openai_api

from .openai_client import openai_client

# Load environment variables from .env file
load_dotenv()

logger = make_logger(__name__)

# Create an ACP server
acp = FastACP.create(
    acp_type="sync",
)

set_default_openai_client(openai_client)
# set_default_openai_api("chat_completions")

class StateModel(BaseModel):
    input_list: List[dict]
    turn_number: int


class WebSearchTool(BaseModel):
    user_location: Optional[dict[str, Any]] = None  # UserLocation object
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
            model="openai/openai/gpt-5-mini",
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
