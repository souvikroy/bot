import streamlit as st
from exa_py import Exa
import os

# Page configuration
st.set_page_config(page_title="Exa News Explorer", page_icon="📡", layout="wide")

# Sidebar for API Keys
with st.sidebar:
    st.title("Settings")
    exa_api_key = st.text_input("Exa API Key", type="password")
    st.markdown("---")
    st.info("Get your API key at [Exa Dashboard](https://dashboard.exa.ai)")

st.title("📡 Exa Recent News Explorer")
st.markdown("""
Enter a topic below to find the most recent news using **Exa's Neural Search**.
""")

# Initialize client if key is provided
if not exa_api_key:
    st.warning("⚠️ Please provide your Exa API key in the sidebar to start.")
    st.stop()

exa_client = Exa(api_key=exa_api_key)

# Helper function for Exa search
def search_news(query: str):
    """Search for recent news using Exa."""
    try:
        # Using category="news" for targeted search
        results = exa_client.search(
            query=query, 
            type="auto", 
            category="news",
            num_results=10, 
            contents={"text": {"max_characters": 1000}} # Just enough for a snippet
        )
        return results.results
    except Exception as e:
        st.error(f"Error during search: {str(e)}")
        return []

# User input
if prompt := st.chat_input("What news are you looking for?"):
    st.chat_message("user").write(prompt)
    
    with st.status(f"Searching for news on '{prompt}'...", expanded=True) as status:
        news_results = search_news(prompt)
        if news_results:
            status.update(label="Search completed!", state="complete", expanded=False)
            
            st.subheader(f"Latest News for: {prompt}")
            
            for i, res in enumerate(news_results):
                with st.container(border=True):
                    # Display clickable title
                    st.markdown(f"### {i+1}. [{res.title}]({res.url})")
                    
                    # Display snippet if available
                    if hasattr(res, 'text') and res.text:
                        snippet = res.text[:500] + "..." if len(res.text) > 500 else res.text
                        st.write(snippet)
                    
                    # Display Citation/Source Info
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.caption(f"Source: {res.url.split('/')[2]}")
                    with col2:
                        st.link_button("Read Full Article", res.url)
        else:
            status.update(label="No results found.", state="error", expanded=True)
            st.info("Try a different or more specific search query.")
