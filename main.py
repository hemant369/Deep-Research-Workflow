import asyncio
from langgraph_layer.graph_builder import build_graph


async def main():
    graph = build_graph()
    query = input("Enter your research query: ")
    result = await graph.ainvoke({"query": query})
    print(result["report"])


if __name__ == "__main__":
    asyncio.run(main())