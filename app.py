import streamlit as st
import json
from openai import OpenAI
from exa_py import Exa
import os

# Page configuration
st.set_page_config(page_title="Exa + OpenAI Search Chatbot", page_icon="🔍", layout="wide")

# Sidebar for API Keys
with st.sidebar:
    st.title("Settings")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    exa_api_key = st.text_input("Exa API Key", type="password")
    st.markdown("---")
    st.info("Get your API keys:\n- [OpenAI](https://platform.openai.com/api-keys)\n- [Exa](https://dashboard.exa.ai)")

st.title("🔍 Exa + OpenAI AI Search Chatbot")
st.markdown("""
Welcome! This chatbot uses **Exa API** for real-time web searches and **OpenAI** to generate smart responses.
To get started, please enter your API keys in the **Settings** sidebar.
""")

# Initialize clients if keys are provided
if not (openai_api_key and exa_api_key):
    st.warning("⚠️ Waiting for API keys... Please provide both OpenAI and Exa API keys in the sidebar.")
    st.stop()

openai_client = OpenAI(api_key=openai_api_key)
exa_client = Exa(api_key=exa_api_key)


# Helper function for Exa search
def exa_search(query: str):
    """Search the web for current information using Exa."""
    try:
        results = exa_client.search(
            query=query, 
            type="auto", 
            num_results=5, 
            contents={"text": {"max_characters": 5000}}
        )
        formatted_results = []
        raw_results = []
        for r in results.results:
            formatted_results.append(f"Title: {r.title}\nURL: {r.url}\nContent: {r.text[:1000]}...")
            raw_results.append({"title": r.title, "url": r.url})
        return "\n\n---\n\n".join(formatted_results), raw_results
    except Exception as e:
        return f"Error during search: {str(e)}", []

# Define tools for OpenAI
tools = [{
    "type": "function",
    "function": {
        "name": "exa_search",
        "description": "Search the web for real-time information, news, or context when the user's query requires it.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query to use."}
            },
            "required": ["query"]
        }
    }
}]

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to know?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Prepare context for OpenAI
        messages_for_api = [
            {"role": "system", "content": """You are a helpful assistant with real-time web search capabilities via Exa.
            
            CRITICAL RULES:
            1. Always cite your sources when using information from the web.
            2. Provide direct clickable links to the sources at the end of your response or inlined.
            3. If you use the exa_search tool, make sure to summarize the information and attribute it to the specific titles/URLs provided."""}
        ] + st.session_state.messages

        try:
            # First LLM call to see if tool is needed
            response = openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_api,
                tools=tools,
                tool_choice="auto"
            )
            
            assistant_message = response.choices[0].message
            
            if assistant_message.tool_calls:
                messages_for_api.append(assistant_message)
                
                # Execute tool calls
                all_search_results = []
                for tool_call in assistant_message.tool_calls:
                    if tool_call.function.name == "exa_search":
                        query = json.loads(tool_call.function.arguments)["query"]
                        with st.status(f"Searching for: {query}...", expanded=False):
                            search_text, raw_results = exa_search(query)
                            all_search_results.extend(raw_results)
                            st.write("Search completed.")
                        
                        messages_for_api.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": search_text
                        })
                
                if all_search_results:
                    with st.expander("📚 Sources & Citations", expanded=False):
                        for i, res in enumerate(all_search_results):
                            st.markdown(f"{i+1}. [{res['title']}]({res['url']})")
                
                # Final LLM call with tool results
                final_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages_for_api,
                    stream=True
                )
                
                for chunk in final_response:
                    content = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
                    full_response += content
                    message_placeholder.markdown(full_response + "▌")
            else:
                # No tool call needed, just stream the response
                stream_response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages_for_api,
                    stream=True
                )
                for chunk in stream_response:
                    content = chunk.choices[0].delta.content if chunk.choices[0].delta.content else ""
                    full_response += content
                    message_placeholder.markdown(full_response + "▌")
            
            message_placeholder.markdown(full_response)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")
