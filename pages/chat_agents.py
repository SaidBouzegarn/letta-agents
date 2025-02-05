import streamlit as st
from agents import list_agents
import dotenv
from letta_client import CreateBlock, Letta, MessageCreate

# Load environment variables
dotenv.load_dotenv()

# Set page configuration to use maximum width
st.set_page_config(layout="wide")

# Initialize Letta client
client = Letta(base_url="http://localhost:8283")

# Page configuration
st.title("Chat with Agents")

# Initialize chat history in session state if not exists
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize selected agent in session state if not exists
if "selected_agent_id" not in st.session_state:
    st.session_state.selected_agent_id = None

# Create two columns - adjust width ratio and add gap
col1, gap, col2 = st.columns([3, 0.2, 7])  # Adjusted for better space utilization

# Left column - Agent selection
with col1:
    st.header("Select Agent")
    agents = list_agents()
    
    if agents:
        agent_names = [agent.name for agent in agents]
        selected_name = st.selectbox("Choose an agent:", options=agent_names)
        selected_agent = next(agent for agent in agents if agent.name == selected_name)
        
        # Update selected agent ID if changed
        if st.session_state.selected_agent_id != selected_agent.id:
            st.session_state.selected_agent_id = selected_agent.id
            st.session_state.messages = []  # Clear chat history when switching agents
            
        # Display agent info
        st.subheader("Agent Info")
        st.write(f"ID: {selected_agent.id}")
        
        # Retrieve and display agent details
        try:
            agent_config = client.agents.retrieve(selected_agent.id)
            if not agent_config.llm_config or not agent_config.llm_config.model:
                st.error("Agent is not properly configured with an LLM backend")
                
            st.write(f"Model: {agent_config.llm_config.model}")
            
            # Display memory blocks if available
            if hasattr(agent_config, 'memory') and hasattr(agent_config.memory, 'blocks'):
                for block in agent_config.memory.blocks:
                    if block.label == "persona":
                        st.write("Persona:", block.value)
        except Exception as e:
            st.error(f"Error fetching agent details: {str(e)}")
    else:
        st.info("No agents available")
        st.stop()

# Add empty gap column for spacing
with gap:
    st.empty()

# Right column - Chat interface
with col2:
    st.header("Chat")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        if st.session_state.selected_agent_id:
            # Add user message to chat history
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Display user message
            with st.chat_message("user"):
                st.write(prompt)

            # Get agent response with streaming
            try:
                stream = client.agents.messages.create_stream(
                    agent_id=st.session_state.selected_agent_id,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                
                # Create empty containers for the response
                with st.chat_message("assistant"):
                    message_placeholder = st.empty()
                    reasoning_placeholder = st.empty()
                    final_content = ""
                    
                    # Process each chunk from the stream
                    for chunk in stream:
                        if hasattr(chunk, 'message_type'):
                            if chunk.message_type == "reasoning_message":
                                with st.expander("Agent's thoughts"):
                                    reasoning_placeholder.write(chunk.reasoning)
                            elif chunk.message_type == "assistant_message":
                                final_content += chunk.content
                                message_placeholder.write(final_content)
                            # Skip usage_statistics messages entirely
                        else:
                            st.warning(f"Unexpected chunk format: {type(chunk)}")
                
                # Add final assistant response to chat history
                st.session_state.messages.append({"role": "assistant", "content": final_content})
                
            except Exception as e:
                st.error(f"Error getting response from agent: {str(e)}")
        else:
            st.warning("Please select an agent first")
