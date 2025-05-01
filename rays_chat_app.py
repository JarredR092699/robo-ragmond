"""
Streamlit Chat Interface for Rays RAG System
This module provides a web interface for interacting with the Rays RAG chatbot.
"""

import streamlit as st
from rays_rag import RaysRAG
import time

# Page configuration
st.set_page_config(
    page_title="Robo Raymond",
    page_icon="🤖",
    layout="centered"
)

# Custom CSS for better appearance
st.markdown("""
    <style>
    .stApp {
        max-width: 800px;
        margin: 0 auto;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: flex-start;
    }
    .chat-message.user {
        background-color: #2b313e;
    }
    .chat-message.assistant {
        background-color: #475063;
    }
    .chat-message .avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        margin-right: 1rem;
    }
    .chat-message .message {
        flex-grow: 1;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

if "rag" not in st.session_state:
    st.session_state.rag = RaysRAG()

# Header
st.title("⚾ Robo Raymond")
st.markdown("""
Hi I'm Robo Raymond! I can help you with:
- Ticket information and specials
- Stadium facilities and services
- Game day experiences
- And more!

Ask me anything about the Rays!
""")

# Chat interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User input
if prompt := st.chat_input("Ask about the Rays..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get bot response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        # Add a typing indicator
        with st.spinner("Thinking..."):
            response = st.session_state.rag.ask(prompt)
        
        # Stream the response
        full_response = ""
        for chunk in response.split():
            full_response += chunk + " "
            time.sleep(0.05)  # Add a small delay for typing effect
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response})

# Sidebar with helpful information
with st.sidebar:
    st.header("About")
    st.markdown("""
    This assistant uses RAG (Retrieval Augmented Generation) technology to provide accurate, 
    up-to-date information about the Tampa Bay Rays. All information is sourced directly 
    from official Rays websites.
    
    **Sample Questions:**
    - What are the current ticket specials?
    - Tell me about parking at the stadium
    - What food options are available?
    - Are there student discounts?
    - How can I get season tickets?
    """)
    
    # Add a clear chat button
    if st.button("Clear Chat"):
        st.session_state.messages = []
        st.rerun() 