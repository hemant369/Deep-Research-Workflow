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
    THRESHOLD = 0.70

    def _domain_score(self, url: str) -> float:
        for domain, score in self.DOMAIN_SCORES.items():
            if domain in url:
                return score
        return self.DEFAULT_SCORE

    def _content_bonus(self, text: str) -> float:
        length = len(text)
        if length > 1000:
            return 0.10
        if length > 500:
            return 0.05
        return 0.0

    def _title_bonus(self, title: str) -> float:
        return 0.03 if title else 0.0

    def execute(self, results: list) -> list:
        validated = []
        for item in results:
            url = item.get("url", "")
            title = item.get("title", "")
            body = item.get("body", "") or item.get("content", "")

            score = self._domain_score(url)
            score += self._content_bonus(body)
            score += self._title_bonus(title)
            score = min(score, 1.0)

            item["confidence"] = round(score, 2)
            if score >= self.THRESHOLD:
                validated.append(item)

        print(f"VALIDATOR: {len(results)} -> {len(validated)}")
        return validated
