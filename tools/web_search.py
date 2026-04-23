from langchain_core.tools import tool
from tavily import TavilyClient
from config import TAVILY_API_KEY

client = TavilyClient(api_key=TAVILY_API_KEY)

@tool
def web_search(query: str) -> str:
    """Search the web for current information about any topic.
    Use this when you need up to date information or facts you don't know."""
    
    response = client.search(query=query, max_results=3)
    
    # extract and format the results cleanly
    results = []
    for r in response['results']:
        results.append(f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['content']}\n")
    
    return "\n".join(results)