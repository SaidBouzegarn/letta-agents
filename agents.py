import streamlit as st
from letta_client import Letta
import dotenv

# Load environment variables
dotenv.load_dotenv()

st.set_page_config(layout="wide")

# Initialize Letta client
client = Letta(base_url="http://localhost:8283")


def save_agent(action, persona_value, job_directives, level, supervisor_name, agent_name, temperature, 
              model_endpoint_type, model, context_window, agent_id=None):
    """Create or update a Letta agent based on specified action"""
    try:
        # Common memory blocks structure
        memory_blocks = [
            {
                "label": "job_directives",
                "value": job_directives,
                "limit": 2000
            },
            {
                "label": "persona",
                "value": persona_value,
                "limit": 3000
            }
        ]
        
        # Set model endpoint based on provider
        model_endpoints = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "groq": "https://api.groq.com/v1",
            "mistral": "https://api.mistral.ai/v1",
            "cohere": "https://api.cohere.ai/v1"
        }
        
        model_endpoint = model_endpoints.get(model_endpoint_type)
        
        # Common LLM config
        llm_config = {
            "model": model,
            "model_endpoint_type": model_endpoint_type,
            "model_endpoint": model_endpoint,
            "context_window": context_window,
            "temperature": temperature,
        }
        
        # Update embedding config to support multiple providers
        embedding_providers = {
            "openai": {
                "model": "text-embedding-3-small",
                "endpoint_type": "openai",
                "endpoint": "https://api.openai.com/v1",
                "dim": 1536
            },
            "cohere": {
                "model": "embed-english-v3.0",
                "endpoint_type": "cohere",
                "endpoint": "https://api.cohere.ai/v1",
                "dim": 1024
            }
        }
        
        # Default to OpenAI embeddings, but use Cohere if selected
        embedding_config = {
            "embedding_model": embedding_providers[model_endpoint_type]["model"] if model_endpoint_type in embedding_providers else embedding_providers["openai"]["model"],
            "embedding_endpoint_type": embedding_providers[model_endpoint_type]["endpoint_type"] if model_endpoint_type in embedding_providers else embedding_providers["openai"]["endpoint_type"],
            "embedding_endpoint": embedding_providers[model_endpoint_type]["endpoint"] if model_endpoint_type in embedding_providers else embedding_providers["openai"]["endpoint"],
            "embedding_dim": embedding_providers[model_endpoint_type]["dim"] if model_endpoint_type in embedding_providers else embedding_providers["openai"]["dim"]
        }
        
        tags = [f"level_{level}", f"{supervisor_name}_sub"]
        tools = []
        if level > 1:
            tools.append("send_message_to_agents_matching_all_tags")

        if action == "create":
            # Validation for create action
            if level not in [1, 2, 3]:
                st.error("Level must be 1, 2, or 3")
                return None
                
            return client.agents.create(
                name=agent_name,
                memory_blocks=memory_blocks,
                llm_config=llm_config,
                embedding_config=embedding_config,
                tags=tags,
                tools=tools
            )
            
        elif action == "modify" and agent_id:
            updated_agent = client.agents.modify(
                agent_id,
                name=agent_name,
                llm_config=llm_config,
                embedding_config=embedding_config,
                tags=tags,
            )
            client.agents.core_memory.modify_block(
                agent_id=agent_id,
                block_label="job_directives",
                value=job_directives
            )
            client.agents.core_memory.modify_block(
                agent_id=agent_id,
                block_label="persona",
                value=persona_value
            )
            #attaching send message to agents matching all tags tool if level > 1
            if level > 1:
                client.agents.tools.attach(
                    agent_id=agent_id,
                    tool_id="tool-87868ef9-46d1-43a7-aa95-7698a3968317"
                )            
        else:
            st.error("Invalid action or missing agent ID for modification")
            return None
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def delete_agent(agent_id):
    """Delete a Letta agent by ID"""
    try:
        client.agents.delete(agent_id)
        return True
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return False

def list_agents():
    """List all available Letta agents"""
    try:
        def fetch_agents():
            return client.agents.list()
            
        agents = fetch_agents()
        return agents
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return []

# Streamlit UI
st.title("Agent Factory")

# Initialize session state for agents if not exists
if 'agents' not in st.session_state:
    st.session_state.agents = list_agents()

# Create two columns for the layout
col1, col2 = st.columns([1, 2])

# Left column - List of agents
with col1:
    st.header("Agent List")
    agents = list_agents()
    # Create a simple selectbox with just agent names
    if agents:
        agent_names = [agent.name for agent in st.session_state.agents]
        selected_name = st.selectbox("Select an agent:", options=agent_names)
        selected_agent = next(agent for agent in st.session_state.agents if agent.name == selected_name)
    else:
        st.info("No agents found")
        selected_agent = None
    st.session_state.agents = agents

# Right column - Agent details and actions
with col2:
    if selected_agent:
        st.header("Agent Details")
        
        try:
            agent_config = client.agents.retrieve(selected_agent.id)
            current_memory = agent_config.memory
            
            # Extract current tags
            current_level = next((int(tag.split('_')[1]) for tag in agent_config.tags if tag.startswith('level_')), 1)
            current_supervisor = next((tag.replace('_sub', '') for tag in agent_config.tags if tag.endswith('_sub')), "")
            
            # Extract memory blocks
            current_persona = ""
            current_job_directives = ""
            
            if current_memory and hasattr(current_memory, 'blocks'):
                for block in current_memory.blocks:
                    if block.label == "persona":
                        current_persona = block.value
                    elif block.label == "job_directives":
                        current_job_directives = block.value
            
            # Extract model config
            llm_config = agent_config.llm_config
            current_model = llm_config.model
            current_provider = llm_config.model_endpoint_type
            current_context_window = llm_config.context_window
            current_temperature = llm_config.temperature
            current_name = agent_config.name

        except Exception as e:
            st.error(f"Error fetching agent configuration: {str(e)}")
            current_name = current_persona = current_job_directives = ""
            current_level = 1
            current_supervisor = ""
            current_model = "gpt-4o-mini"
            current_provider = "openai"
            current_context_window = 16000
            current_temperature = 0.7

        # Editable fields
        new_name = st.text_input("Agent Name:", value=current_name, key=f"name_{selected_agent.id}")
        new_persona = st.text_area("Persona:", value=current_persona, key=f"persona_{selected_agent.id}")
        new_job_directives = st.text_area("Job Directives:", value=current_job_directives, 
                                        key=f"directives_{selected_agent.id}")
        
        col_model1, col_model2 = st.columns(2)
        with col_model1:
            new_provider = st.selectbox("Model Provider:", 
                options=["openai", "anthropic", "groq", "mistral", "cohere"],
                index=["openai", "anthropic", "groq", "mistral", "cohere"].index(current_provider),
                key=f"provider_{selected_agent.id}")
        with col_model2:
            model_options = {
                "openai": ["gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
                "anthropic": ["claude-3-haiku", "claude-3-sonnet", "claude-3-opus"],
                "groq": ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
                "mistral": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
                "cohere": ["command-r-plus", "command-r", "command"]
            }
            new_model = st.selectbox("Model:", 
                options=model_options[new_provider],
                index=model_options[new_provider].index(current_model) if current_model in model_options[new_provider] else 0,
                key=f"model_{selected_agent.id}")
        
        new_context_window = st.selectbox("Context Window:", 
            options=[4096, 8192, 16000, 32768, 128000, 200000],
            index=[4096, 8192, 16000, 32768, 128000, 200000].index(current_context_window),
            key=f"context_{selected_agent.id}")
        
        col_supervisor, col_level = st.columns(2)
        with col_supervisor:
            new_supervisor = st.text_input("Supervisor Name:", value=current_supervisor, key=f"super_{selected_agent.id}")
        with col_level:
            new_level = st.selectbox("Level:", [1, 2, 3], index=current_level-1, key=f"level_{selected_agent.id}")
            
        new_temperature = st.slider("Temperature:", min_value=0.0, max_value=1.0, 
                                  value=current_temperature, step=0.1,
                                  key=f"temp_{selected_agent.id}")
        
        col_update, col_delete = st.columns(2)
        
        with col_update:
            if st.button("Update Agent", key=f"update_{selected_agent.id}"):
                updated_agent = save_agent(
                    action="modify",
                    agent_id=selected_agent.id,
                    persona_value=new_persona,
                    job_directives=new_job_directives,
                    level=new_level,
                    supervisor_name=new_supervisor,
                    agent_name=new_name,
                    temperature=new_temperature,
                    model_endpoint_type=new_provider,
                    model=new_model,
                    context_window=new_context_window
                )
                if updated_agent:
                    st.success(f"Updated agent {selected_agent.id}")
                    st.session_state.agents = list_agents()
                    st.rerun()
                
        with col_delete:
            if st.button("Delete Agent", type="primary", key=f"delete_{selected_agent.id}"):
                if delete_agent(selected_agent.id):
                    st.success(f"Deleted agent {selected_agent.id}")
                    st.session_state.agents = list_agents()
                    st.rerun()
    
    # Create new agent section
    st.header("Create New Agent")
    with st.expander("Create New Agent"):
        agent_name_input = st.text_input("Enter agent name:", "New Letta Agent")
        persona_input = st.text_area("Enter agent persona:", 
            "I am a helpful AI assistant focused on providing clear and concise information.")
        job_directives_input = st.text_area("Enter job directives:", 
            "Your primary responsibility is to assist users with accurate information.")
        level_input = st.selectbox("Select Level:", [1, 2, 3])
        supervisor_input = st.text_input("Enter Supervisor Name:")
        temperature_input = st.slider("Temperature:", min_value=0.0, max_value=1.0, 
                                    value=0.7, step=0.1)
        
        # Model configuration
        model_endpoint_type = st.selectbox("Model Provider:", 
            options=["openai", "anthropic", "groq", "mistral", "cohere"])
        
        # Model selection based on provider
        model_options = {
            "openai": ["gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
            "anthropic": ["claude-3-haiku", "claude-3-sonnet", "claude-3-opus"],
            "groq": ["llama3-70b-8192", "llama3-8b-8192", "mixtral-8x7b-32768"],
            "mistral": ["mistral-large-latest", "mistral-medium-latest", "mistral-small-latest"],
            "cohere": ["command-r-plus", "command-r", "command"]
        }
        model = st.selectbox("Model:", 
            options=model_options[model_endpoint_type])
        
        # Context window selection
        context_window = st.selectbox("Context Window:", 
            options=[4096, 8192, 16000, 32768, 128000, 200000],
            index=2)  # Default to 16k

        if st.button("Create Agent"):
            if not supervisor_input:
                st.error("Please enter a supervisor name")
            else:
                agent = save_agent(
                    action="create",
                    persona_value=persona_input,
                    job_directives=job_directives_input,
                    level=level_input,
                    supervisor_name=supervisor_input,
                    agent_name=agent_name_input,
                    temperature=temperature_input,
                    model_endpoint_type=model_endpoint_type,
                    model=model,
                    context_window=context_window
                )
                if agent:
                    st.success(f"Created agent with ID: {agent.id}")
                    st.session_state.agents = list_agents()
                    st.rerun()
