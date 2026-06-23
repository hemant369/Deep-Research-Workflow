import asyncio
import time
from datetime import datetime

from langgraph_layer.state import ResearchState

from agents.planner import PlannerAgent
from agents.synthesizer_agent import SynthesizerAgent
from agents.writer_agent import WriterAgent
from agents.academic_agent import AcademicAgent
from agents.coding_agent import CodingAgent
from agents.general_agent import GeneralAgent
from services.merge_dedup import MergeDedup
from services.evidence_validator import EvidenceValidator
from services.citation_generator import CitationGenerator
from memory.memory_store import memory  # single instance

planner          = PlannerAgent()
general_agent    = GeneralAgent()
academic_agent   = AcademicAgent()
coding_agent     = CodingAgent()
merge_dedup      = MergeDedup()
validator        = EvidenceValidator()
citation_generator = CitationGenerator()
synthesizer      = SynthesizerAgent()
writer           = WriterAgent()


async def memory_load_node(state: ResearchState) -> dict:
    print("NODE -> Memory Load")
    query = state.get("query", "")
    if not query:
        return {"memory_hit": False, "past_report": "", "past_sources": []}

    past = memory.find(query=query)
    if past:
        return {
            "memory_hit":   True,
            "past_report":  past.get("report", ""),
            "past_sources": past.get("sources", [])
        }
    return {"memory_hit": False, "past_report": "", "past_sources": []}


async def memory_save_node(state: ResearchState) -> dict:
    print("NODE -> Memory Save")
    query  = state.get("query", "")
    report = state.get("report", "")
    if not query or not report:
        print("Missing query or report — skipping memory save.")
        return {}

    sources = [
        item.get("url", "")
        for item in state.get("results", [])
        if item.get("url", "")
    ]
    memory.save(query=query, report=report, sources=sources)
    return {}


async def planner_node(state: ResearchState) -> dict:
    print("NODE -> Planner Node")
    sub_questions = planner.generate_sub_question(state["query"])
    return {"sub_questions": sub_questions}


async def general_node(state: ResearchState) -> dict:
    questions = state["general_questions"]
    if not questions:
        return {"general_results": []}

    start = time.time()
    print(f"{datetime.now()} -> NODE -> General Node START")
    tasks   = [general_agent.search(q) for q in questions]
    results = await asyncio.gather(*tasks)
    general_results = [item for result in results for item in result]
    print(f"{datetime.now()} -> NODE -> General Node END {time.time()-start:.2f}s")
    return {"general_results": general_results}


async def academic_node(state: ResearchState) -> dict:
    questions = state["academic_questions"]
    if not questions:
        return {"academic_results": []}

    start = time.time()
    print(f"{datetime.now()} -> NODE -> Academic Node START")
    tasks   = [academic_agent.search(q) for q in questions]
    results = await asyncio.gather(*tasks)
    academic_results = [item for result in results for item in result]
    print(f"{datetime.now()} -> NODE -> Academic Node END {time.time()-start:.2f}s")
    return {"academic_results": academic_results}


async def coding_node(state: ResearchState) -> dict:
    questions = state["coding_questions"]
    if not questions:
        return {"coding_results": []}

    start = time.time()
    print(f"{datetime.now()} -> NODE -> Coding Node START")
    tasks   = [coding_agent.search(q) for q in questions]
    results = await asyncio.gather(*tasks)
    coding_results = [item for result in results for item in result]
    print(f"{datetime.now()} -> NODE -> Coding Node END {time.time()-start:.2f}s")
    return {"coding_results": coding_results}


async def merge_node(state: ResearchState) -> dict:
    print("NODE -> Merge Node")
    all_results = (
        state.get("academic_results", []) +
        state.get("general_results",  []) +
        state.get("coding_results",   [])
    )
    results = merge_dedup.execute(all_results)
    return {"results": results}


async def validator_node(state: ResearchState) -> dict:
    print("NODE -> Validator Node")
    results = validator.execute(state["results"])
    return {"results": results}


async def citation_node(state: ResearchState) -> dict:
    print("NODE -> Citation Node")
    results = citation_generator.execute(state["results"])
    return {"results": results}


async def synthesizer_node(state: ResearchState) -> dict:
    print("NODE -> Synthesizer Node")
    synthesized_text = synthesizer.synthesize(state["query"], state["results"])
    return {"synthesized_text": synthesized_text}


async def writer_node(state: ResearchState) -> dict:
    print("NODE -> Writer Node")
    report = writer.generate_report(state["query"], state["synthesized_text"])
    return {"report": report}