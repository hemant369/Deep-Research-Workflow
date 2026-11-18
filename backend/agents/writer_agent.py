from model.llm import llm


PROMPT = """You are a professional technical report writer.

You will receive structured research data with these sections:
- FACTS: deduplicated findings with citation indices like [1.1][2.3]
- CONFLICTS: disagreements between sources
- GAPS: unanswered parts of the query

Your job is to transform this into a polished markdown report.

Topic:
{query}

Research Synthesis:
{synthesized_text}

Verified reference map:
{references}

Instructions:
1. Do NOT invent any information not present in the synthesis.
2. Preserve all citation indices exactly as [1], [1.1], [2.3] etc.
3. Under # Conflicts & Caveats, surface any CONFLICTS from the synthesis.
4. Under # Research Gaps, list any GAPS from the synthesis honestly.
5. Do not create a References section. It is appended deterministically after writing.
6. Write a complete, useful report. Be factual, but do not make it artificially short.
7. Return ONLY markdown, no preamble.
8. Aim for 900-1500 words when the synthesis contains enough evidence.
9. Use enough detail that a reader can understand the main ideas, tradeoffs, evidence,
   caveats, and practical implications without opening every source.

Write this exact structure:

# Executive Summary
<3-5 sentence overview of the topic and what the research found>

# Key Findings
<grouped subsections where useful, with detailed bullet points from FACTS and citations>

# Conflicts & Caveats
<bullet points from CONFLICTS - where sources disagree or evidence is limited>

# Research Gaps
<bullet points from GAPS - what the research did not cover>

# Conclusion
<2-4 paragraphs synthesizing the overall picture and practical implications>
"""


class WriterAgent:
    async def generate_report(
        self,
        query: str,
        synthesized_text: str,
        references: str,
    ) -> str:
        prompt = PROMPT.format(
            query=query,
            synthesized_text=synthesized_text,
            references=references,
        )

        try:
            response = await llm.ainvoke(prompt)
            return str(response.content).strip()
        except Exception as e:
            raise RuntimeError(f"Report generation failed: {e}") from e
