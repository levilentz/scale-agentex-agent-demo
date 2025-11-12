from typing import AsyncGenerator

from pydantic import BaseModel

from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.acp import SendMessageParams
from agentex.types.task_message_update import TaskMessageUpdate
from agentex.types.task_message_content import TaskMessageContent
from agentex.types.text_content import TextContent
from agentex.lib.utils.logging import make_logger
from agentex.lib import adk
from agents import set_default_openai_client

from .tools import list_all_programs, find_program_by_name, find_candidates_for_program

from openai import AsyncOpenAI
from dotenv import load_dotenv

AGENT_NAME = "Clinical Trial Enrollment Agent"

AGENT_INSTRUCTIONS = """
You are an AI-Augmented Clinical Research Coordinator specializing in clinical trial enrollment.
You help users find clinical programs and match eligible candidates to trials.

You have access to the following tools:
- list_all_programs: List all available clinical research programs
- find_program_by_name: Find a specific program by searching for its name
- find_candidates_for_program: Find all eligible candidates for a specific program (requires program_id like CP001)

Always be professional and helpful. When presenting candidates, show their key demographic information.
If a user asks about eligibility criteria, you can use the find_program_by_name tool to get program details first.
"""

AGENT_TOOLS = [
    list_all_programs,
    find_program_by_name,
    find_candidates_for_program,
]

AGENT_MODEL = "openai/gpt-4o-mini"

# TODO: How does Auth with SGP work?
# import os
# import httpx
# SGP_API_KEY = os.getenv("SGP_API_KEY")
# SGP_BASE_URL = os.getenv("SGP_BASE_URL")
# SGP_ACCOUNT_ID = os.getenv("SGP_ACCOUNT_ID")
# http_client = httpx.AsyncClient(verify=False)
# openai_client = AsyncOpenAI(
#     base_url=SGP_BASE_URL,
#     api_key="",
#     default_headers={
#         "x-api-key": SGP_API_KEY,
#         "x-selected-account-id": SGP_ACCOUNT_ID
#     },
#     http_client=http_client,
# )

# Load .env file
load_dotenv()

# Use my OpenAI creds b/c I can't figure out auth
openai_client = AsyncOpenAI()
set_default_openai_client(openai_client)

logger = make_logger(__name__)

# Create an ACP server
acp = FastACP.create(acp_type="sync")


class StateModel(BaseModel):
    input_list: list[dict]
    turn_number: int


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
        if not isinstance(item, dict) or "role" not in item or "content" not in item:
            continue
        if item["role"] == "user" and item["content"]:
            text_messages.append(TextContent(author="user", content=item["content"]))
        elif (
            item["role"] == "assistant"
            and item["content"]
            and isinstance(item["content"], list)
        ):
            for content_item in item["content"]:
                if not isinstance(content_item, dict) or "text" not in content_item:
                    continue
                text_messages.append(
                    TextContent(author="agent", content=content_item["text"])
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
    """Handle incoming messages for clinical trial enrollment with AI agent."""

    # Extract message text
    if (
        not params.content
        or params.content.type != "text"
        or not params.content.content
    ):
        return TextContent(author="agent", content="Please provide a message.")
    message_text = params.content.content
    logger.info(f"📨 Received message: {message_text}")

    # Get or create task state
    task = await adk.tasks.get(task_id=params.task.id)
    task_state = await adk.state.get_by_task_and_agent(
        task_id=params.task.id, agent_id=params.agent.id
    )

    if not task_state:
        state = StateModel(input_list=[], turn_number=0)
        task_state = await adk.state.create(
            task_id=params.task.id, agent_id=params.agent.id, state=state
        )
    else:
        state = StateModel.model_validate(task_state.state)

    # Increment turn number
    state.turn_number += 1
    state_len = len(state.input_list)

    # Add user message to history
    state.input_list.append({"role": "user", "content": message_text})

    try:
        result = await adk.providers.openai.run_agent_auto_send(
            task_id=task.id,
            trace_id=task.id,
            input_list=state.input_list,
            agent_name=AGENT_NAME,
            agent_instructions=AGENT_INSTRUCTIONS,
            model=AGENT_MODEL,
            tools=AGENT_TOOLS,
        )
    except Exception as e:
        logger.exception(f"❌ Error handling message: {str(e)}")
        return TextContent(
            author="agent", content=f"Sorry, I encountered an error: {str(e)}"
        )
    logger.info("✅ Response generated successfully")

    new_messages = result.to_input_list()[state_len + 1 :]
    state.input_list.extend(new_messages)
    await adk.state.update(
        state_id=task_state.id,
        task_id=params.task.id,
        agent_id=params.agent.id,
        state=state,
    )

    return parse_messages_to_text_content(new_messages)
