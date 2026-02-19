from rpg_rules_ai.config import settings
from rpg_rules_ai.strategies.base import RetrievalStrategy


def get_strategy() -> RetrievalStrategy:
    from rpg_rules_ai.strategies.multi_hop import MultiHopStrategy
    from rpg_rules_ai.strategies.multi_question import MultiQuestionStrategy

    strategies = {
        "multi-hop": MultiHopStrategy,
        "multi-question": MultiQuestionStrategy,
    }
    return strategies[settings.retrieval_strategy]()
