"""CLI wrapper for Tavily search — usable from Claude Code via Bash."""

import asyncio
import json
import sys
import os
from pathlib import Path

# Load .env
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

from langchain_tavily import TavilySearch


async def search(query: str, max_results: int = 5):
    api_key = os.getenv("TAVILY_API_KEY", "")
    tool = TavilySearch(
        tavily_api_key=api_key,
        max_results=max_results,
        search_depth="basic",
    )
    result = tool.invoke({"query": query})
    return result


if __name__ == "__main__":
    query = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else sys.stdin.read().strip()
    if not query:
        print("Usage: python search.py <query>")
        sys.exit(1)

    result = asyncio.run(search(query))

    if isinstance(result, str):
        print(result)
    elif isinstance(result, list):
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif isinstance(result, dict):
        print(json.dumps(result, ensure_ascii=False, indent=2))
