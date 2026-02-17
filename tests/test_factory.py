from unittest.mock import patch

from caprag.strategies.factory import get_strategy
from caprag.strategies.multi_hop import MultiHopStrategy
from caprag.strategies.multi_question import MultiQuestionStrategy


@patch("caprag.strategies.factory.settings")
def test_get_strategy_multi_hop(mock_settings):
    mock_settings.retrieval_strategy = "multi-hop"
    result = get_strategy()
    assert isinstance(result, MultiHopStrategy)


@patch("caprag.strategies.factory.settings")
def test_get_strategy_multi_question(mock_settings):
    mock_settings.retrieval_strategy = "multi-question"
    result = get_strategy()
    assert isinstance(result, MultiQuestionStrategy)
