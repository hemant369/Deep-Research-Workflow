class CitationGenerator:

    def execute(self, results):

        citations = []

        for index, item in enumerate(results, start=1):

            item["citation"] = f"[{index}]"

            citations.append(item)

        return citations