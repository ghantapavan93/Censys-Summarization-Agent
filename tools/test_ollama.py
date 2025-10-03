from backend.services.llm_router import LLMRouter

if __name__ == "__main__":
    demo = (
        "Rewrite into one concise executive sentence, keep facts: "
        "Analyzed 11 services across 2 countries (3 unique IPs). "
        "Top ports 22 (2), 11558 (1). Risks: 1 high, 2 medium, 1 low."
    )
    llm = LLMRouter()
    print(llm.complete(demo))
