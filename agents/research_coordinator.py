from agents.general_agent import GeneralAgent
from agents.academic_agent import AcademicAgent
from agents.coding_agent import CodingAgent


class ResearchCoordinator():
    
    def __init__(self):
        self.general_agent = GeneralAgent()
        self.academic_agent = AcademicAgent()
        self.coding_agent = CodingAgent()

    def route_question(self, question:str):

        question = question.lower()

        academic_keywords = [ "paper", "research", "journal", "survey", "study"]
        coding_keywords = ["code", "github", "repository", "implementation", "python"]

        if any(

            keyword in question

            for keyword in academic_keywords

        ):

            return self.academic_agent


        if any(

            keyword in question

            for keyword in coding_keywords

        ):

            return self.coding_agent


        return self.general_agent

    async def execute(self, sub_questions):

        all_results = []

        for query in sub_questions:

            agent = self.route_question(query)
            results = await agent.search(query)
            all_results.extend(results)
        
        return all_results
