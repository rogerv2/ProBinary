# Mi Proyecto en Codex ProBinary Manager

Herramientas básicas para validar parámetros de riesgo, controlar estados de detención y calcular montos máximos de inversión respetando un stop dinámico.

## Uso rápido

```python
from probinary import TradingParameters, TradingSession, StopReason

params = TradingParameters(risk_percent=1.5, trailing_percent=5, target_percent=5, max_trades=3)
session = TradingSession(balance=1000, dynamic_stop_floor=900, parameters=params)

# Valida rangos y calcula el monto máximo permitido
max_amount = session.max_investment_without_breaking_stop(params.risk_percent)

# Ejecuta una operación sin exceder el stop dinámico
session.place_trade(max_amount)

# Forzar stop por meta alcanzada y bloquear nuevas acciones
session.stop(StopReason.TARGET)
```

## Pruebas

Ejecuta la suite con:

```bash
python -m pytest
```
