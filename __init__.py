"""The PID controller integration."""

from __future__ import annotations

import logging
import math
from datetime import timedelta
from typing import TYPE_CHECKING, Any, Never

from dvg_pid_controller import Constants as PIDConst
from dvg_pid_controller import PID_Controller as PID
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_time_interval

from .const import (
    ATTR_CYCLE_TIME,
    ATTR_LAST_CYCLE_START,
    ATTR_PID_ENABLE,
    ATTR_PID_ERROR,
    ATTR_PID_INPUT,
    ATTR_PID_KD,
    ATTR_PID_KI,
    ATTR_PID_KP,
    ATTR_PID_OUTPUT,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

PLATFORMS = [Platform.NUMBER]
_LOGGER = logging.getLogger(__name__)


class PidBaseClass(Entity):
    """Base class for PID entities."""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        k_p: float = 1,
        k_i: float = 0.01,
        k_d: float = 0,
        direction: PIDConst = PIDConst.DIRECT,
        cycle_time: str | timedelta = "00:00:10",
    ) -> None:
        """Initialize PID base class."""
        self._pid = PID(k_p, k_i, k_d, direction)
        if isinstance(cycle_time, timedelta):
            self._attr_cycle_time = cycle_time
        else:
            self._attr_cycle_time = timedelta(**cycle_time)
        self._attr_last_cycle_start: str = None

    @property
    def pid_state_attributes(self) -> dict[str, Any]:
        """Return capability attributes."""
        attr = {}
        attr[ATTR_CYCLE_TIME] = self.cycle_time
        attr[ATTR_PID_KP] = self.k_p
        attr[ATTR_PID_KI] = self.k_i
        attr[ATTR_PID_KD] = self.k_d
        attr[ATTR_PID_INPUT] = self.pid_input
        attr[ATTR_PID_OUTPUT] = self.pid_output
        attr[ATTR_PID_ERROR] = self.pid_error
        attr[ATTR_LAST_CYCLE_START] = self._attr_last_cycle_start
        attr[ATTR_PID_ENABLE] = self.enable_pid
        return attr

    async def _async_start_pid_cycle(self) -> None:
        """
        Start periodical cycle of PID controller.

        Call this when added to hass, and hass is fully started.
        """
        self.async_on_remove(
            async_track_time_interval(
                self.hass,
                self._async_pid_cycle,
                self._attr_cycle_time,
                cancel_on_shutdown=True,
            )
        )

    @property
    def cycle_time(self) -> str:
        """Return cycle time for PID controller."""
        return str(self._attr_cycle_time)

    @property
    def last_cycle_start(self) -> str:
        """Return last time the PID controller cycle started."""
        return str(self._attr_last_cycle_start)

    @property
    def k_p(self) -> float:
        """Get Kp of the PID regulator."""
        return self._pid.kp

    @property
    def k_i(self) -> float:
        """Ki of the PID regulator."""
        return self._pid.ki

    @property
    def k_d(self) -> float:
        """Kd of the PID regulator."""
        return self._pid.kd

    @property
    def enable_pid(self) -> bool:
        """PID controller enabled."""
        return self._pid.in_auto

    async def async_enable(self, *, value: bool) -> Never:
        """Enable or disable PID regulator."""
        # Raise Not Yet implemented error; has to be implemented per controller
        # Use self._pid.set_mode (mode,
        #                input_state , output_state, optional:input2_state )
        raise NotImplementedError

    def filter_nan(self, value: float) -> float | None:
        """Filter floats for NAN."""
        if math.isnan(value):
            return None
        return value

    @property
    def pid_input(self) -> float:
        """Calculate input value, differential or not."""
        return self.filter_nan(self._pid.last_input)

    @property
    def pid_output(self) -> float:
        """Return PID output value."""
        return self.filter_nan(self._pid.output)

    @property
    def pid_error(self) -> float:
        """Calculate the current error."""
        return self.filter_nan(self._pid.last_error)

    @callback
    async def _async_pid_cycle(self, *_: Any) -> Never:
        """
        Cycle PID regulator.

        Will raise NotImplemented error; should be implemented per controller.
        Use self._pid.compute(input,optional:input2 ) and self._pid.output to
        calculate.
        Read the data from this controllers input and send the result to this
        controllers output.
        Don't forget to update last_cycle_start as below:
        self._attr_last_cycle_start = dt_util.utcnow().replace(microsecond=0)
        """
        raise NotImplementedError


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up slow PID Controller from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(config_entry_update_listener))
    return True


async def config_entry_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """
    Update listener.

    Called when the config entry options are changed.
    """
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
