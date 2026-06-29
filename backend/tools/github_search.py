import requests
from backend.schemas.tool_result import ToolResult, make_tool_result


def search_github(query: str) -> list[ToolResult]:

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
            make_tool_result(
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
