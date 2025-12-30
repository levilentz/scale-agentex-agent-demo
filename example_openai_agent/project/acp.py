import os
from typing import AsyncGenerator, List, Union

from agentex.lib import adk
from agentex.lib.sdk.fastacp.fastacp import FastACP
from agentex.lib.types.acp import SendMessageParams
from agentex.lib.utils.logging import make_logger
from agentex.lib.utils.model_utils import BaseModel
from agentex.types.task_message_content import TaskMessageContent
from agentex.types.task_message_update import TaskMessageUpdate
from agentex.types.text_content import TextContent
from agentex.lib.core.tracing.tracing_processor_manager import (
    add_tracing_processor_config,
)
from agentex.lib.types.tracing import SGPTracingProcessorConfig

from .tools import ADD_NUMBERS_TOOL
from .prompts import AGENT_PROMPT

from agents import RunResultStreaming, set_default_openai_client, set_default_openai_api
from agentex.lib.core.temporal.activities.adk.providers.openai_activities import ModelSettings as SerializableModelSettings
from openai.types.shared import Reasoning

from project.openai_client import openai_client

set_default_openai_client(openai_client)
set_default_openai_api("chat_completions")

logger = make_logger(__name__)

# Only enable tracing if not in local development mode
LOCAL_DEVELOPMENT = os.environ.get("LOCAL_DEVELOPMENT", "false").lower() == "true"

if not LOCAL_DEVELOPMENT:
    add_tracing_processor_config(
        SGPTracingProcessorConfig(
            sgp_api_key=os.environ.get("SGP_API_KEY", ""),
            sgp_account_id=os.environ.get("SGP_ACCOUNT_ID", ""),
            sgp_base_url=os.environ.get("SGP_BASE_URL", "https://sgp.ai.t-mobile.com/api/v5/"),
        )
    )
    logger.info("Tracing enabled")
else:
    logger.info("Tracing disabled (LOCAL_DEVELOPMENT mode)")

# Create an ACP server
acp = FastACP.create(
    acp_type="sync",
)


class StateModel(BaseModel):
    """State model to track conversation state across turns"""
    input_list: List[dict]
    turn_number: int
    # Add any additional state fields you need here
    # Example: cart: List[dict] = []
    # Example: user_id: str | None = None


@acp.on_message_send
async def handle_message_send(
    params: SendMessageParams
) -> Union[TaskMessageContent, AsyncGenerator[TaskMessageUpdate, None], None]:
    """Message handler with state management and tracing support"""
    
    # Validate incoming message
    if not params.content:
        return None

    if params.content.type != "text":
        raise ValueError(f"Expected text message, got {params.content.type}")

    if params.content.author != "user":
        raise ValueError(f"Expected user message, got {params.content.author}")

    # Retrieve the task state. Each event is handled as a new turn, so we need to get the state for the current turn.
    task_state = await adk.state.get_by_task_and_agent(task_id=params.task.id, agent_id=params.agent.id)
    if not task_state:
        # If the state doesn't exist, create it.
        state = StateModel(input_list=[], turn_number=0)
        task_state = await adk.state.create(task_id=params.task.id, agent_id=params.agent.id, state=state)
    else:
        state = StateModel.model_validate(task_state.state)

    # Increment turn number
    state.turn_number += 1

    # Decode and add the new user message to the message history
    user_prompt = params.content.content
    logger.info(f"The user prompt: {user_prompt}")
    state.input_list.append({"role": "user", "content": user_prompt})
    
    async with adk.tracing.span(
        trace_id=params.task.id,
        name=f"Turn {state.turn_number}",
        input=state
    ) as span:
        trace_id = params.task.id
        input_list = state.input_list

        # Configure agent settings
        agent_name = "Assistant Agent"
        agent_instructions = AGENT_PROMPT
        
        # Model configuration
        model = "openai/openai/gpt-5-mini"
        model_settings = SerializableModelSettings(
            parallel_tool_calls=True,
            reasoning=Reasoning(
                effort="low",
                summary="auto",
            ),
        )
        tool_use_behavior = "run_llm_again"
        
        # Setup agent with tools (add your tools here)
        tools = [
            # Add your tools here
            ADD_NUMBERS_TOOL
        ]

        # Run the agent with streaming
        result: RunResultStreaming = await adk.providers.openai.run_agent_streamed_auto_send(
            task_id=params.task.id,
            trace_id=trace_id,
            parent_span_id=span.id if span else None,
            input_list=input_list,
            agent_name=agent_name,
            agent_instructions=agent_instructions,
            model=model,
            tool_use_behavior=tool_use_behavior,
            model_settings=model_settings,
            tools=tools,
            mcp_server_params=[],
        )
        
        logger.info(f"Agent: {result}")
        logger.info(f"Agent streaming started for task {params.task.id}")
        
        # Update state with conversation history from result
        state.input_list = result.to_input_list()
        
        # Set the span output to the state for the next turn
        span.output = state

        # Store the messages in the task state for the next turn
        await adk.state.update(
            state_id=task_state.id,
            task_id=params.task.id,
            parent_span_id=span.id if span else None,
            agent_id=params.agent.id,
            state=state,
            trace_id=params.task.id,
        )
    
    return None
    