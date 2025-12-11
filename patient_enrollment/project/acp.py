import json
import os
from typing import Any, AsyncGenerator, Callable

from agentex.lib import adk
from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.acp import SendMessageParams
from agentex.lib.utils.logging import make_logger
from agentex.types.task_message_content import TaskMessageContent
from agentex.types.task_message_update import TaskMessageUpdate
from agentex.types.text_content import TextContent
from dotenv import find_dotenv, load_dotenv
from pydantic import BaseModel
from scale_gp import AsyncSGPClient
from agentex.lib.types.tracing import SGPTracingProcessorConfig
from agentex.lib.core.tracing.tracing_processor_manager import add_tracing_processor_config

from .tools import (
    FIND_CANDIDATES_FOR_PROGRAM_TOOL_DEF,
    FIND_PERSON_BY_NAME_TOOL_DEF,
    FIND_PROGRAM_BY_NAME_TOOL_DEF,
    FIND_PROGRAMS_FOR_CANDIDATE_TOOL_DEF,
    LIST_ALL_PROGRAMS_TOOL_DEF,
    find_candidates_for_program,
    find_person_by_name,
    find_program_by_name,
    find_programs_for_candidate,
    list_all_programs,
)

if not (SGP_API_KEY := os.getenv("SGP_API_KEY")):
    raise EnvironmentError("Missing SGP_API_KEY")

if not (SGP_ACCOUNT_ID := os.getenv("SGP_ACCOUNT_ID")):
    raise EnvironmentError("Missing SGP_ACCOUNT_ID")

if not (SGP_BASE_URL := os.getenv("SGP_BASE_URL")):
    raise EnvironmentError("Missing SGP_BASE_URL")

MODEL = "vertex_ai/gemini-2.5-flash"

add_tracing_processor_config(
    SGPTracingProcessorConfig(
        sgp_api_key=SGP_API_KEY,
        sgp_account_id=SGP_ACCOUNT_ID,
        sgp_base_url=SGP_BASE_URL,
    )
)

AGENT_NAME = "Clinical Trial Enrollment Agent"

AGENT_INSTRUCTIONS = """
You are an AI-Augmented Clinical Research Coordinator specializing in clinical trial enrollment.
You help users find clinical programs and match eligible candidates to trials.

You have access to the following tools:
- list_all_programs: List all available clinical research programs
- find_program_by_name: Find a specific program by searching for its name
- find_person_by_name: Find a person/candidate by searching for their name
- find_candidates_for_program: Find all eligible candidates for a specific program (requires program_id like CP001)
- find_programs_for_candidate: Find all eligible programs for a specific candidate (requires person_id like P001)

Always be professional and helpful. When presenting candidates or programs, show their key information.
If a user asks about a person by name, use find_person_by_name first to get their person_id, then you can use find_programs_for_candidate.
If a user asks about eligibility criteria, you can use the find_program_by_name tool to get program details first.
"""

logger = make_logger(__name__)

AGENT_TOOLS = [
    (list_all_programs, LIST_ALL_PROGRAMS_TOOL_DEF),
    (find_program_by_name, FIND_PROGRAM_BY_NAME_TOOL_DEF),
    (find_person_by_name, FIND_PERSON_BY_NAME_TOOL_DEF),
    (find_candidates_for_program, FIND_CANDIDATES_FOR_PROGRAM_TOOL_DEF),
    (find_programs_for_candidate, FIND_PROGRAMS_FOR_CANDIDATE_TOOL_DEF),
]

MODEL = "gemini/gemini-2.5-flash"

# Load environment variables from .env file local or parent directories
load_dotenv(find_dotenv())

if (
    not os.getenv("SGP_BASE_URL")
    or not os.getenv("SGP_ACCOUNT_ID")
    or not os.getenv("SGP_API_KEY")
):
    raise EnvironmentError(
        "SGP_BASE_URL, SGP_ACCOUNT_ID, and SGP_API_KEY must be set in environmental variables."
    )

# Initialize SGP client
async_sgp_client = AsyncSGPClient(
    base_url=os.getenv("SGP_BASE_URL"),
    account_id=os.getenv("SGP_ACCOUNT_ID"),
    api_key=os.getenv("SGP_API_KEY"),
)

# Create an ACP server
acp = FastACP.create(acp_type="sync")


class StateModel(BaseModel):
    input_list: list[dict]
    turn_number: int


async def run_gemini_with_tools(
    messages: list[dict],
    agent_instructions: str = AGENT_INSTRUCTIONS,
    model: str = MODEL,
    tools: list[tuple[Callable, dict[str, Any]]] | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1000,
) -> str:
    """
    Run Gemini with clinical trial tools via SGP client.

    Args:
        messages: List of message dicts with role and content
        agent_name: Name of the agent
        agent_instructions: System instructions for the agent
        model: Model name to use
        tools: List of (function, tool_dict) tuples, defaults to AGENT_TOOLS
        temperature: Model temperature
        max_tokens: Maximum tokens in response

    Returns:
        The assistant's response text
    """
    if tools is None:
        tools = AGENT_TOOLS

    # Create tool map for executing functions
    tool_map = {func.__name__: func for func, _ in tools}

    # Extract just the tool dicts for the API
    tool_defs = [tool_dict for _, tool_dict in tools]

    # Prepend system message with instructions
    conversation = [{"role": "system", "content": agent_instructions}] + messages

    logger.info(f"Sending request to {model} with {len(tool_defs)} tools")

    # First request - model decides if it needs to use tools
    response = await async_sgp_client.beta.chat.completions.create(
        model=model,
        messages=conversation,
        tools=tool_defs,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    message = response.choices[0].message

    # Loop until we get a response without tool calls
    while hasattr(message, "tool_calls") and message.tool_calls:
        logger.info(f"Model requested {len(message.tool_calls)} tool call(s)")

        # Append assistant message with tool calls to conversation
        conversation.append(
            {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in message.tool_calls
                ],
            }
        )

        # Execute each tool call
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)

            logger.info(f"Executing tool: {tool_name} with args: {args}")

            # Execute the actual function
            result = tool_map[tool_name](**args)

            logger.info(f"Tool result: {result}")

            # Append tool result to conversation
            conversation.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                }
            )

        logger.info("Requesting next response with tool results...")

        # Get next response with tool results
        response = await async_sgp_client.beta.chat.completions.create(
            model=model,
            messages=conversation,
            tools=tool_defs,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        logger.info(f"Response: {response}")
        message = response.choices[0].message

    logger.info("Model returned final answer without tool calls")
    return message.content


@acp.on_message_send
async def handle_message_send(
    params: SendMessageParams,
) -> (
    TaskMessageContent
    | list[TaskMessageContent]
    | AsyncGenerator[TaskMessageUpdate, None] 
    | None
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
    logger.info(f"Received message: {message_text}")

    # Get or create task state
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

    async with adk.tracing.span(
        trace_id=params.task.id,
        name=f"clinical_trial_turn_{state.turn_number}_task_{params.task.id}",
        input=state,
    ) as span:
        state.turn_number += 1

        # Add user message to history
        state.input_list.append({"role": "user", "content": message_text})

        try:
            response_text = await run_gemini_with_tools(
                messages=state.input_list,
            )
        except Exception as e:
            logger.exception(f"Error handling message: {str(e)}")
            return TextContent(
                author="agent", content=f"Sorry, I encountered an error: {str(e)}"
            )
        logger.info("Response generated successfully")

        # Add assistant response to history
        state.input_list.append({"role": "assistant", "content": response_text})

        span.output = state

        await adk.state.update(
           state_id=task_state.id,
           task_id=params.task.id,
           parent_span_id=span.id if span else None,
           agent_id=params.agent.id,
           state=state,
           trace_id=params.task.id,
        )

        await adk.messages.create(
            task_id=params.task.id,
            content=TextContent(
                author="agent",
                content=response_text,
            ),
            parent_span_id=span.id if span else None,
        )
    return None