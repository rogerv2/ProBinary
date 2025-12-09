import pytest

from probinary.session import (
    ParameterValidationError,
    StopError,
    StopReason,
    TradingParameters,
    TradingSession,
)


def test_parameter_validation_ranges():
    params = TradingParameters(risk_percent=1, trailing_percent=5, target_percent=5, max_trades=2)
    params.validate()

    with pytest.raises(ParameterValidationError):
        TradingParameters(risk_percent=0.1, trailing_percent=5, target_percent=5, max_trades=2).validate()

    with pytest.raises(ParameterValidationError):
        TradingParameters(risk_percent=1, trailing_percent=20, target_percent=5, max_trades=2).validate()

    with pytest.raises(ParameterValidationError):
        TradingParameters(risk_percent=1, trailing_percent=5, target_percent=20, max_trades=2).validate()

    with pytest.raises(ParameterValidationError):
        TradingParameters(risk_percent=1, trailing_percent=5, target_percent=5, max_trades=0).validate()


def test_block_actions_when_stopped():
    params = TradingParameters(risk_percent=1, trailing_percent=5, target_percent=5, max_trades=1)
    session = TradingSession(balance=1000, dynamic_stop_floor=900, parameters=params)
    session.stop(StopReason.TARGET)

    with pytest.raises(StopError) as excinfo:
        session.place_trade(100)

    assert "Meta diaria alcanzada" in str(excinfo.value)


def test_max_investment_respects_dynamic_stop():
    params = TradingParameters(risk_percent=2, trailing_percent=5, target_percent=5, max_trades=5)
    session = TradingSession(balance=1000, dynamic_stop_floor=900, parameters=params)

    allowed = session.max_investment_without_breaking_stop(params.risk_percent)
    # Available drawdown = 100, with 2% risk gives max 5000 but capped by balance (1000)
    assert allowed == pytest.approx(1000)

    with pytest.raises(ParameterValidationError):
        session.place_trade(1500)

    accepted = session.place_trade(1000)
    assert accepted == 1000


def test_consecutive_loss_limit_triggers_stop():
    params = TradingParameters(risk_percent=1, trailing_percent=5, target_percent=5, max_trades=5)
    session = TradingSession(
        balance=1000,
        dynamic_stop_floor=900,
        parameters=params,
        consecutive_loss_limit=2,
    )

    session.record_loss(amount=10)
    assert session.state == "RUNNING"

    session.record_loss(amount=10)
    assert session.state == "STOPPED"
    assert session.stop_reason == StopReason.CONSECUTIVE_LOSSES

    with pytest.raises(StopError):
        session.place_trade(100)
