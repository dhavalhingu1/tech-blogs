import os
import logging
import chainlit as cl
from dotenv import load_dotenv

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# --------------------------------------------------
# Load environment variables
# --------------------------------------------------
load_dotenv()

# Reduce Azure SDK log noise
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

AIPROJECT_CONNECTION_STRING = os.getenv("AIPROJECT_CONNECTION_STRING")
AGENT_ID = os.getenv("AGENT_ID")

if not AIPROJECT_CONNECTION_STRING:
    raise RuntimeError("Missing AIPROJECT_CONNECTION_STRING")

if not AGENT_ID:
    raise RuntimeError("Missing AGENT_ID")

# --------------------------------------------------
# Create AI Project client
# --------------------------------------------------
project_client = AIProjectClient.from_connection_string(
    conn_str=AIPROJECT_CONNECTION_STRING,
    credential=DefaultAzureCredential(),
)

# --------------------------------------------------
# Chainlit handlers
# --------------------------------------------------

@cl.on_chat_start
async def on_chat_start():
    # Create one thread per user session
    thread = project_client.agents.create_thread()
    cl.user_session.set("thread_id", thread.id)
    print(f"New Thread ID: {thread.id}")


@cl.on_message
async def on_message(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")

    try:
        # Show temporary thinking message
        msg = await cl.Message(
            content="thinking...",
            author="assistant"
        ).send()

        # Add user message to agent thread
        project_client.agents.create_message(
            thread_id=thread_id,
            role="user",
            content=message.content,
        )

        # Run the agent
        run = project_client.agents.create_and_process_run(
            thread_id=thread_id,
            agent_id=AGENT_ID,
        )

        if run.status == "failed":
            raise Exception(run.last_error)

        # ----------------------------------
        # Get all messages from the thread
        # ----------------------------------
        messages = project_client.agents.list_messages(thread_id)

        # Get the last assistant message
        last_msg = messages.get_last_text_message_by_role("assistant")
        if not last_msg:
            raise Exception("No response from the model.")

        msg.content = last_msg.text.value
        await msg.update()

    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()


if __name__ == "__main__":
    # Chainlit runs the app automatically
    pass
