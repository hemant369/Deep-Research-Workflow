import requests
from schemas.tool_result import ToolResult


def search_github(query: str):

    url = "https://api.github.com/search/repositories"

    params = {
        "q": query,
        "sort": "stars",
        "per_page": 5
    }

    response = requests.get(url, params=params)
    response.raise_for_status() 

    data = response.json()

    results = []

    for repo in data.get("items", []):  
        results.append(
            ToolResult(
                source="github",
                title=repo.get("name", ""),
                content=repo.get("description", "") or "", 
                url=repo.get("html_url", ""),
                metadata={
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),       
                    "language": repo.get("language", "") or "" 
                }
            )
        )

    return results