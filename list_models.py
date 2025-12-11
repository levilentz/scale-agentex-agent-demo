#!/usr/bin/env python3
"""Script to list available models and run a chat completion."""

import asyncio
import os

from dotenv import find_dotenv, load_dotenv
from scale_gp import AsyncSGPClient

# Load environment variables
load_dotenv(find_dotenv())


async def list_models_and_chat():
    """List models and run a chat completion with an chat completion model."""
    # Check for required environment variables
    if not os.getenv("SGP_API_KEY"):
        raise EnvironmentError(
            "SGP_API_KEY must be set in environment variables."
        )

    client = AsyncSGPClient(
        base_url=os.getenv("SGP_BASE_URL"),
        account_id=os.getenv("SGP_ACCOUNT_ID"),
        api_key=os.getenv("SGP_API_KEY"),
    )

    print(f"SGP_API_KEY: {os.getenv('SGP_API_KEY')[:10]}...")
    print("\nFetching available models...\n")
    print("=" * 80)

    # List all models and find an chat completion model
    models_response = client.models.list()
    chat_model = None

    async for model in models_response:
        print(f"Model Name: {model.name}")
        print(f"Display Name: {model.display_name}")
        print(f"Model Type: {model.model_type}")
        print(f"Model Vendor: {model.model_vendor}")
        print("-" * 80)

        # Select the first chat completion model we find
        if (
            chat_model is None
            and model.model_type == "COMPLETION"
        ):
            chat_model = model.name
            model_vendor = model.model_vendor.lower()

    print("\n" + "=" * 80)

    if chat_model:
        print(f"\n✅ Selected Chat Model: {chat_model}")
        print("\nRunning chat completion with prompt: 'who are you?'\n")
        print("-" * 80)

        # Run a chat completion
        response = await client.beta.chat.completions.create(
            model=f"{model_vendor}/{chat_model}",
            messages=[
                {"role": "user", "content": "who are you?"}
            ],
            temperature=0.7,
            max_tokens=500,
        )

        # Print the response
        print("\n📝 Response:\n")
        print(response.choices[0].message.content)
        print("\n" + "-" * 80)
    else:
        print("\n❌ No chat completion model found.")
        print("Available model types may be different. Check the list above.")


if __name__ == "__main__":
    asyncio.run(list_models_and_chat())
