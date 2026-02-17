from caprag.config import settings
from caprag.strategies.base import RetrievalStrategy


def get_strategy() -> RetrievalStrategy:
    from caprag.strategies.multi_hop import MultiHopStrategy
    from caprag.strategies.multi_question import MultiQuestionStrategy

    strategies = {
        "multi-hop": MultiHopStrategy,
        "multi-question": MultiQuestionStrategy,
    }
    return strategies[settings.retrieval_strategy]()
