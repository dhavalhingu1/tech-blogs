import os
import chainlit as cl
import logging
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# ------------------------------
# Load environment variables
# ------------------------------
load_dotenv()

AIPROJECT_CONNECTION_STRING = os.getenv("AIPROJECT_CONNECTION_STRING")
AGENT_ID = os.getenv("AGENT_ID")

# ------------------------------
# Disable verbose Azure logs
# ------------------------------
logger = logging.getLogger("azure.core.pipeline.policies.http_logging_policy")
logger.setLevel(logging.WARNING)

# ------------------------------
# Initialize AIProjectClient
# ------------------------------
project_client = AIProjectClient.from_connection_string(
    conn_str=AIPROJECT_CONNECTION_STRING,
    credential=DefaultAzureCredential()
)

# ------------------------------
# Chainlit Chat Start
# ------------------------------
@cl.on_chat_start
async def on_chat_start():
    # Create a thread if it doesn't exist
    if not cl.user_session.get("thread_id"):
        thread = project_client.agents.create_thread()
        cl.user_session.set("thread_id", thread.id)
        print(f"New Thread ID: {thread.id}")

# ------------------------------
# Handle User Messages
# ------------------------------
@cl.on_message
async def on_message(message: cl.Message):
    thread_id = cl.user_session.get("thread_id")
    
    try:
        # Show "thinking..." to the user
        msg = await cl.Message("thinking...", author="agent").send()

        # Send user message to Azure AI Project thread
        project_client.agents.create_message(
            thread_id=thread_id,
            role="user",
            content=message.content
        )
        
        # Process the message with the agent
        run = project_client.agents.create_and_process_run(
            thread_id=thread_id,
            agent_id=AGENT_ID
        )
        print(f"Run finished with status: {run.status}")

        if run.status == "failed":
            raise Exception(run.last_error)

        # Get all messages in the thread
        messages = project_client.agents.list_messages(thread_id)

        # Get the last message from the assistant
        last_msg = messages.get_last_text_message_by_role("assistant")
        if not last_msg:
            raise Exception("No response from the model.")

        # Update Chainlit message with agent's response
        msg.content = last_msg.text.value
        await msg.update()

    except Exception as e:
        await cl.Message(content=f"Error: {str(e)}").send()

# ------------------------------
# Main entry point
# ------------------------------
if __name__ == "__main__":
    pass
