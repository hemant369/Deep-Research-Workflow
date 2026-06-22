class EvidenceValidator:

    DOMAIN_SCORES = {
        "arxiv.org": 0.95,
        "pubmed.ncbi.nlm.nih.gov": 0.95,
        "scholar.google.com": 0.95,
        "github.com": 0.85,
        "docs.python.org": 0.90,
        "aws.amazon.com/documentation": 0.90,
        "cloud.google.com/docs": 0.90,
        "pytorch.org/docs": 0.90,
        "huggingface.co": 0.88,
        "wikipedia.org": 0.80,
        "stackoverflow.com": 0.75,
        "ibm.com": 0.88,
        "geeksforgeeks.org": 0.82,
        "coursera.org": 0.85,
        "medium.com": 0.65,
        "towardsdatascience.com": 0.70,
        "linkedin.com": 0.50,
    }

    DEFAULT_SCORE = 0.55
    THRESHOLD = 0.70

    def _score(self, url: str) -> float:
        for domain, score in self.DOMAIN_SCORES.items():
            if domain in url:
                return score
        return self.DEFAULT_SCORE

    def execute(self, results: list) -> list:
        validated = []
        for item in results:
            url = item.get("url", "")
            score = self._score(url)
            item["confidence"] = score
            if score >= self.THRESHOLD:
                validated.append(item)
        return validated