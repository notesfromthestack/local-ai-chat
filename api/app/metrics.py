from collections import defaultdict


# Metric names
CHAT_REQUESTS_TOTAL = "chat_requests_total"
CHAT_DURATION_SECONDS = "chat_duration_seconds"
CHAT_TOKENS_TOTAL = "chat_tokens_total"

RAG_REQUESTS_TOTAL = "rag_requests_total"
RAG_DURATION_SECONDS = "rag_duration_seconds"
RAG_DOCUMENTS_RETRIEVED_TOTAL = "rag_documents_retrieved_total"

RAG_INDEX_REQUESTS_TOTAL = "rag_index_requests_total"
RAG_INDEX_DURATION_SECONDS = "rag_index_duration_seconds"
RAG_DOCUMENTS_INDEXED_TOTAL = "rag_documents_indexed_total"


class Metrics:
    def __init__(self):
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)

    def inc_counter(self, name: str, value: int = 1):
        """Increment a counter."""
        self.counters[name] += value

    def observe_histogram(self, name: str, value: float):
        """Record a histogram observation."""
        self.histograms[name].append(value)

    def get_prometheus_format(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []

        # Counters
        for name, value in self.counters.items():
            lines.append(f"# TYPE {name} counter")
            lines.append(f"{name} {value}")

        # Histograms (simple avg for now)
        for name, values in self.histograms.items():
            if values:
                avg = sum(values) / len(values)
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {avg:.4f}")

        return "\n".join(lines) + "\n"


# Global metrics instance
metrics = Metrics()
