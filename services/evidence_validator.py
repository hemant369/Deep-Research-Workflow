from model.llm import llm


class EvidenceValidator:
    DOMAIN_SCORES = {
        "arxiv.org": 0.95,
        "pubmed.ncbi.nlm.nih.gov": 0.95,
        "scholar.google.com": 0.95,
        "github.com": 0.85,
        "docs.python.org": 0.90,
        "aws.amazon.com/documentation": 0.90,
        "cloud.google.com/docs": 0.90,
        "pytorch.org": 0.90,
        "huggingface.co": 0.88,
        "ibm.com": 0.88,
        "coursera.org": 0.85,
        "geeksforgeeks.org": 0.82,
        "wikipedia.org": 0.80,
        "stackoverflow.com": 0.75,
        "towardsdatascience.com": 0.70,
        "medium.com": 0.65,
        "linkedin.com": 0.50,
    }

    DEFAULT_SCORE = 0.55
    THRESHOLD = 0.75

    def _domain_score(self, url: str) -> float:
        for domain, score in self.DOMAIN_SCORES.items():
            if domain in url.lower():
                return score
        return self.DEFAULT_SCORE

    def _content_bonus(self, text: str) -> float:
        length = len(text)

        if length > 3000:
            return 0.10
        elif length > 1500:
            return 0.08
        elif length > 800:
            return 0.05
        elif length > 300:
            return 0.02

        return 0.0

    def _title_bonus(self, title: str) -> float:
        return 0.03 if title.strip() else 0.0

    def _relevance_bonus(self, query: str, item: dict) -> float:
        title = item.get("title", "")
        body = item.get("body", "") or item.get("content", "")

        # Prevent sending huge documents
        body = body[:1500]

        prompt = f"""
        You are evaluating whether a piece of evidence is useful for answering a user's research question.

        User Query:
        {query}

        Evidence Title:
        {title}

        Evidence:
        {body}

        Classify the evidence into ONLY one of:

        Relevant
        Partially Relevant
        Irrelevant

        Return ONLY one word.
        """

        try:
            response = llm.invoke(prompt)
            answer = str(response.content).strip().lower()

            if "relevant" == answer:
                return 0.10

            if "partially" in answer:
                return 0.05

            return 0.0

        except Exception:
            return 0.0

    def execute(self, query: str, results: list) -> list:
        validated = []

        for item in results:
            url = item.get("url", "")
            title = item.get("title", "")
            body = item.get("body", "") or item.get("content", "")

            score = self._domain_score(url)
            score += self._content_bonus(body)
            score += self._title_bonus(title)
            score += self._relevance_bonus(query, item)

            score = min(score, 1.0)

            item["confidence"] = round(score, 2)

            if score >= self.THRESHOLD:
                validated.append(item)

        print(
            f"VALIDATOR: {len(results)} -> {len(validated)} "
            f"(threshold={self.THRESHOLD})"
        )

        return validated