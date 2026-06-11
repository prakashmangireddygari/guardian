from dataclasses import dataclass
from enum import Enum


class Condition(str, Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    FOG = "fog"
    SNOW = "snow"


_MULTIPLIERS = {
    Condition.CLEAR: 1.0,
    Condition.CLOUDY: 1.1,
    Condition.RAIN: 1.3,
    Condition.HEAVY_RAIN: 1.6,
    Condition.FOG: 1.5,
    Condition.SNOW: 1.8,
}

_MESSAGES = {
    Condition.CLEAR: "Clear conditions — standard following distances apply.",
    Condition.CLOUDY: "Overcast — minor distance increase applied.",
    Condition.RAIN: "Rain detected — safe following distance +30%.",
    Condition.HEAVY_RAIN: "Heavy rain — safe following distance +60%.",
    Condition.FOG: "Dense fog — safe following distance +50%.",
    Condition.SNOW: "Snow conditions — safe following distance +80%.",
}


@dataclass
class WeatherState:
    condition: Condition
    visibility_km: float
    is_night: bool
    temperature_c: float


SCENARIOS: list[WeatherState] = [
    WeatherState(Condition.CLEAR, 10.0, False, 22.0),
    WeatherState(Condition.RAIN, 3.0, False, 15.0),
    WeatherState(Condition.FOG, 0.5, True, 8.0),
    WeatherState(Condition.HEAVY_RAIN, 1.0, True, 12.0),
    WeatherState(Condition.SNOW, 0.3, False, -2.0),
    WeatherState(Condition.CLOUDY, 8.0, False, 18.0),
]


class WeatherContext:
    """Mock weather context — swap _fetch() for a real API call in production."""

    NIGHT_MULT = 1.2

    def __init__(self, scenario: int = 0):
        self._state = SCENARIOS[scenario % len(SCENARIOS)]

    def set_scenario(self, index: int):
        self._state = SCENARIOS[index % len(SCENARIOS)]

    def threshold_multiplier(self) -> float:
        m = _MULTIPLIERS[self._state.condition]
        if self._state.is_night:
            m *= self.NIGHT_MULT
        return round(m, 2)

    def status(self) -> dict:
        return {
            'condition': self._state.condition.value,
            'visibility_km': self._state.visibility_km,
            'is_night': self._state.is_night,
            'temperature_c': self._state.temperature_c,
            'threshold_multiplier': self.threshold_multiplier(),
            'alert_message': self._alert_msg(),
        }

    def _alert_msg(self) -> str:
        msg = _MESSAGES.get(self._state.condition, '')
        if self._state.is_night:
            msg += ' Low light — visibility alert active.'
        return msg
