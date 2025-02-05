import dotenv
from letta_client import Letta
import time

# Load environment variables
dotenv.load_dotenv()

# Initialize Letta client
client = Letta(base_url="http://localhost:8283")

def create_and_test_agent():
    try:
        # Create a new agent
        print("Creating agent...")
        agent = client.agents.create(
            name="Test Agent",
            memory_blocks=[
                {
                    "label": "job_directives",
                    "value": "You are a helpful assistant",
                    "limit": 2000
                },
                {
                    "label": "persona",
                    "value": "I am a friendly AI",
                    "limit": 3000
                }
            ],
            model="openai/gpt-4o-mini",
            llm_config={
                "model": "gpt-4o-mini",
                "model_endpoint_type": "openai",
                "model_endpoint": "https://api.openai.com/v1/",
                "context_window": 8192,
                "temperature": 0.7,
                "put_inner_thoughts_in_kwargs": True
            },
            embedding_config={
                "embedding_model": "text-embedding-3-small",
                "embedding_endpoint_type": "openai",
                "embedding_endpoint": "https://api.openai.com/v1/",
                "embedding_dim": 1536
            },
            tags=["level_1", "test_supervisor_sub"]
        )
        
        print(f"Agent created with ID: {agent.id}")
        
        # Send a message to the agent
        print("Sending message to agent...")
        response = client.agents.messages.create(
            agent_id=agent.id,
            messages=[
                {
                    "role": "user",
                    "content": "Hello, how are you?"
                }
            ],
        )
        
        print("Agent response:")
        print(response)
        
        # Wait a moment before deletion
        time.sleep(2)
        
        #print("Retrieving agent info...")
        #retrieving agent info
        #agent_info = client.agents.retrieve(
        #    agent_id=agent.id
        #)
        #print(agent_info)
        
        # Delete the agent
        print("Deleting agent...")
        client.agents.delete(agent.id)
        print("Agent deleted successfully")
        
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    create_and_test_agent()
