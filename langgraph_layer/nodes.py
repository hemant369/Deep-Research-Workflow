from agents.planner import PlannerAgent
from agents.research_coordinator import ResearchCoordinator
from agents.synthesizer import SynthesizerAgent
from agents.writer import WriterAgent
from services.merge_dedup import MergeDedup
from services.evidence_validator import EvidenceValidator
from services.citation_generator import CitationGenerator

planner = PlannerAgent()
coordinator = ResearchCoordinator()
merge_dedup = MergeDedup()
validator = EvidenceValidator()
citation_generator = CitationGenerator()
synthesizer = SynthesizerAgent()
writer = WriterAgent()

async def planner_node(state):

    query = state["query"]

    sub_questions = planner.generate_sub_question(query)

    return {
        "sub_questions": sub_questions
    }


async def research_node(state):

    sub_questions = state["sub_questions"]

    results = await coordinator.execute(sub_questions)

    return {
        "results": results
    }


async def merge_node(state):

    results = merge_dedup.execute(state["results"])

    return {
        "results": results
    }


async def validator_node(state):

    results = validator.execute(state["results"])

    return {
        "results": results
    }



async def citation_node(state):

    results = citation_generator.execute(state["results"])

    return {
        "results": results
    }


async def synthesizer_node(state):

    synthesized_text = synthesizer.synthesize(
        state["query"],
        state["results"]
    )

    return {
        "synthesized_text": synthesized_text
    }


async def writer_node(state):

    report = writer.generate_report(
        state["query"],
        state["synthesized_text"]
    )
    return {
        "report": report
    }