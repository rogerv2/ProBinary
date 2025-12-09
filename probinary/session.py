"""Trading session rules and validation logic."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class ParameterValidationError(ValueError):
    """Raised when provided trading parameters are invalid."""


class StopError(RuntimeError):
    """Raised when an action is attempted while the session is stopped."""


class StopReason(str, Enum):
    FATIGUE = "fatiga"
    TRAILING = "trailing"
    TARGET = "meta"
    CONSECUTIVE_LOSSES = "perdidas_consecutivas"

    def human_reason(self) -> str:
        mapping = {
            StopReason.FATIGUE: "Fatiga operativa detectada",
            StopReason.TRAILING: "Stop dinámico alcanzado por trailing",
            StopReason.TARGET: "Meta diaria alcanzada",
            StopReason.CONSECUTIVE_LOSSES: "Límite de pérdidas consecutivas alcanzado",
        }
        return mapping[self]


@dataclass
class TradingParameters:
    """Configuration used to place trades.

    Attributes:
        risk_percent: Percentage of account balance to risk per trade (0.5-5%).
        trailing_percent: Trailing stop percentage (3-15%).
        target_percent: Profit target percentage (3-15%).
        max_trades: Maximum number of trades allowed in the session.
    """

    risk_percent: float
    trailing_percent: float
    target_percent: float
    max_trades: int

    def validate(self) -> None:
        """Validate parameter ranges.

        Raises:
            ParameterValidationError: if any parameter is outside its allowed range.
        """

        if not 0.5 <= self.risk_percent <= 5:
            raise ParameterValidationError(
                f"El riesgo debe estar entre 0.5% y 5% (valor recibido: {self.risk_percent})."
            )

        if not 3 <= self.trailing_percent <= 15:
            raise ParameterValidationError(
                f"El trailing debe estar entre 3% y 15% (valor recibido: {self.trailing_percent})."
            )

        if not 3 <= self.target_percent <= 15:
            raise ParameterValidationError(
                f"La meta debe estar entre 3% y 15% (valor recibido: {self.target_percent})."
            )

        if self.max_trades <= 0:
            raise ParameterValidationError("El límite de operaciones debe ser mayor que cero.")


class TradingSession:
    """Represents the current trading session status and risk controls."""

    def __init__(
        self,
        *,
        balance: float,
        dynamic_stop_floor: float,
        parameters: TradingParameters,
        consecutive_loss_limit: int = 3,
    ) -> None:
        self.balance = balance
        self.dynamic_stop_floor = dynamic_stop_floor
        self.parameters = parameters
        self.parameters.validate()
        self.state = "RUNNING"
        self.stop_reason: Optional[StopReason] = None
        self.consecutive_losses = 0
        self.consecutive_loss_limit = consecutive_loss_limit
        self.trades_placed = 0

    def stop(self, reason: StopReason) -> None:
        """Stop the session and record the reason."""

        self.state = "STOPPED"
        self.stop_reason = reason

    def resume(self) -> None:
        """Resume trading clearing the stop reason."""

        self.state = "RUNNING"
        self.stop_reason = None

    def assert_running(self) -> None:
        """Ensure the session is not stopped before performing an action."""

        if self.state == "STOPPED":
            reason = self.stop_reason.human_reason() if self.stop_reason else "Estado detenido"
            raise StopError(f"Acción bloqueada: {reason}.")

    def record_loss(self, *, amount: float) -> None:
        """Record a loss and stop if consecutive losses reached the limit."""

        self.balance -= amount
        self.consecutive_losses += 1
        if self.consecutive_losses >= self.consecutive_loss_limit:
            self.stop(StopReason.CONSECUTIVE_LOSSES)

    def record_profit(self, *, amount: float) -> None:
        """Record a profit and reset consecutive losses."""

        self.balance += amount
        self.consecutive_losses = 0

    def max_investment_without_breaking_stop(self, risk_percent: float) -> float:
        """Calculate maximum stake without violating the dynamic stop.

        The calculation caps the amount so that the potential loss at the
        provided risk percentage does not push the balance below the
        ``dynamic_stop_floor``. The available amount is also limited by the
        current balance.
        """

        available_drawdown = max(self.balance - self.dynamic_stop_floor, 0)
        if risk_percent <= 0:
            raise ParameterValidationError("El riesgo debe ser mayor que cero para calcular el monto permitido.")

        # Potential loss = stake * (risk_percent / 100)
        allowed_by_stop = available_drawdown / (risk_percent / 100)
        return min(self.balance, allowed_by_stop)

    def place_trade(self, amount: float) -> float:
        """Validate and place a trade.

        Returns the amount accepted for the trade.
        """

        self.assert_running()
        self.parameters.validate()

        if self.trades_placed >= self.parameters.max_trades:
            self.stop(StopReason.FATIGUE)
            self.assert_running()

        max_allowed = self.max_investment_without_breaking_stop(self.parameters.risk_percent)
        if amount > max_allowed:
            raise ParameterValidationError(
                "El monto propuesto supera el permitido por el stop dinámico. "
                f"Máximo permitido: {max_allowed:.2f}."
            )

        self.trades_placed += 1
        return amount
