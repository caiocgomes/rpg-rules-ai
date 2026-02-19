from unittest.mock import patch

from rpg_rules_ai.strategies.factory import get_strategy
from rpg_rules_ai.strategies.multi_hop import MultiHopStrategy
from rpg_rules_ai.strategies.multi_question import MultiQuestionStrategy


@patch("rpg_rules_ai.strategies.factory.settings")
def test_get_strategy_multi_hop(mock_settings):
    mock_settings.retrieval_strategy = "multi-hop"
    result = get_strategy()
    assert isinstance(result, MultiHopStrategy)


@patch("rpg_rules_ai.strategies.factory.settings")
def test_get_strategy_multi_question(mock_settings):
    mock_settings.retrieval_strategy = "multi-question"
    result = get_strategy()
    assert isinstance(result, MultiQuestionStrategy)
