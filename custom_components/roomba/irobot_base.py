"""Base class for iRobot devices."""
from __future__ import annotations

import asyncio
from datetime import datetime
import json
import logging

from homeassistant.components.vacuum import (
    ATTR_STATUS,
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    SUPPORT_BATTERY,
    SUPPORT_LOCATE,
    SUPPORT_PAUSE,
    SUPPORT_RETURN_HOME,
    SUPPORT_SEND_COMMAND,
    SUPPORT_START,
    SUPPORT_STATE,
    SUPPORT_STATUS,
    SUPPORT_STOP,
    StateVacuumEntity,
)
import homeassistant.helpers.device_registry as dr
from homeassistant.helpers.entity import Entity
import homeassistant.util.dt as dt_util

from . import roomba_reported_state
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

ATTR_CLEANING_TIME = "cleaning_time"
ATTR_CLEANED_AREA = "cleaned_area"
ATTR_INITIATOR = "initiator"
ATTR_TOTAL_CLEANING_TIME = "total_cleaning_time"
ATTR_TOTAL_CLEANED_AREA = "total_cleaned_area"
ATTR_TOTAL_JOBS = "total_jobs"
ATTR_TOTAL_DIRT_EVENTS = "total_dirt_events"
ATTR_TOTAL_EVACS = "total_evacs"
ATTR_LAST_COMMAND = "last_command"
ATTR_NOT_READY = "not_ready"
ATTR_NOT_READY_CODE = "not_ready_code"
ATTR_ERROR = "error"
ATTR_ERROR_CODE = "error_code"
ATTR_POSITION = "position"
ATTR_SOFTWARE_VERSION = "software_version"
ATTR_PMAP = "pmap_"

# Commonly supported features
SUPPORT_IROBOT = (
    SUPPORT_BATTERY
    | SUPPORT_PAUSE
    | SUPPORT_RETURN_HOME
    | SUPPORT_SEND_COMMAND
    | SUPPORT_START
    | SUPPORT_STATE
    | SUPPORT_STATUS
    | SUPPORT_STOP
    | SUPPORT_LOCATE
)

STATE_MAP = {
    "": STATE_IDLE,
    "charge": STATE_DOCKED,
    "evac": STATE_RETURNING,  # Emptying at cleanbase
    "hmMidMsn": STATE_CLEANING,  # Recharging at the middle of a cycle
    "hmPostMsn": STATE_RETURNING,  # Cycle finished
    "hmUsrDock": STATE_RETURNING,
    "pause": STATE_PAUSED,
    "run": STATE_CLEANING,
    "stop": STATE_IDLE,
    "stuck": STATE_ERROR,
}

NOT_READY_MAP = {
    0: 'N/A',
    2: 'Uneven Ground',
    15: 'Low Battery',
    39: 'Pending',
    48: 'Path Blocked'   
}

class IRobotEntity(Entity):
    """Base class for iRobot Entities."""

    def __init__(self, roomba, blid):
        """Initialize the iRobot handler."""
        self.vacuum = roomba
        self._blid = blid
        self.vacuum_state = roomba_reported_state(roomba)
        self._name = self.vacuum_state.get("name")
        self._version = self.vacuum_state.get("softwareVer")
        self._sku = self.vacuum_state.get("sku")

    @property
    def should_poll(self):
        """Disable polling."""
        return False

    @property
    def robot_unique_id(self):
        """Return the uniqueid of the vacuum cleaner."""
        return f"roomba_{self._blid}"

    @property
    def unique_id(self):
        """Return the uniqueid of the vacuum cleaner."""
        return self.robot_unique_id

    @property
    def device_info(self):
        """Return the device info of the vacuum cleaner."""
        info = {
            "identifiers": {(DOMAIN, self.robot_unique_id)},
            "manufacturer": "iRobot",
            "name": str(self._name),
            "sw_version": self._version,
            "model": self._sku,
        }
        if mac_address := self.vacuum_state.get("hwPartsRev", {}).get(
            "wlan0HwAddr", self.vacuum_state.get("mac")
        ):
            info["connections"] = {(dr.CONNECTION_NETWORK_MAC, mac_address)}
        return info

    @property
    def _battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        return self.vacuum_state.get("batPct")

    @property
    def _robot_state(self):
        """Return the state of the vacuum cleaner."""
        clean_mission_status = self.vacuum_state.get("cleanMissionStatus", {})
        cycle = clean_mission_status.get("cycle")
        phase = clean_mission_status.get("phase")
        try:
            state = STATE_MAP[phase]
        except KeyError:
            return STATE_ERROR
        if cycle != "none" and state in (STATE_IDLE, STATE_DOCKED):
            state = STATE_PAUSED
        return state

    async def async_added_to_hass(self):
        """Register callback function."""
        self.vacuum.register_on_message_callback(self.on_message)

    def new_state_filter(self, new_state):  # pylint: disable=no-self-use
        """Filter out wifi state messages."""
        return len(new_state) > 1 or "signal" not in new_state

    def on_message(self, json_data):
        """Update state on message change."""
        state = json_data.get("state", {}).get("reported", {})
        if self.new_state_filter(state):
            self.schedule_update_ha_state()


class IRobotVacuum(IRobotEntity, StateVacuumEntity):
    """Base class for iRobot robots."""

    def __init__(self, roomba, blid):
        """Initialize the iRobot handler."""
        super().__init__(roomba, blid)
        self._cap_position = self.vacuum_state.get("cap", {}).get("pose") == 1

    @property
    def supported_features(self):
        """Flag vacuum cleaner robot features that are supported."""
        return SUPPORT_IROBOT

    @property
    def battery_level(self):
        """Return the battery level of the vacuum cleaner."""
        return self._battery_level

    @property
    def state(self):
        """Return the state of the vacuum cleaner."""
        return self._robot_state

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True  # Always available, otherwise setup will fail

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def not_ready_code(self):
        state = self.vacuum_state
        if not (mission_state := state.get("cleanMissionStatus")):
            return 0
        return mission_state.get("notReady", 0)
    
    @property
    def not_ready(self):
        try:
            return NOT_READY_MAP[self.not_ready_code]
        except KeyError as e:
            return f"Unknown message type {self.not_ready_code}"
  
    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        state = self.vacuum_state

        # Roomba software version
        software_version = state.get("softwareVer")

        # Set properties that are to appear in the GUI
        state_attrs = {ATTR_SOFTWARE_VERSION: software_version}

        # Set legacy status to avoid break changes
        state_attrs[ATTR_STATUS] = self.vacuum.current_state

        # get the last command (to help with identifying rooms/zones)
        state_attrs[ATTR_LAST_COMMAND] = json.dumps(state.get("lastCommand",""))

        map_id = 0
        if pmaps := state.get("pmaps",[]):
            for map in pmaps:
                for k, v in map.items():
                    state_attrs[f"{ATTR_PMAP}{map_id}"] = k
                    pass
                map_id += 1

        # Get total statistics
        (
            state_attrs[ATTR_TOTAL_CLEANING_TIME],
            state_attrs[ATTR_TOTAL_CLEANED_AREA],
            state_attrs[ATTR_TOTAL_JOBS],
            state_attrs[ATTR_TOTAL_DIRT_EVENTS],
            state_attrs[ATTR_TOTAL_EVACS]
        ) = self.get_total_statistics(state)        

        # Only add cleaning time and cleaned area attrs when the vacuum is
        # currently on
        if self.state == STATE_CLEANING:
            # Get clean mission status
            (
                state_attrs[ATTR_CLEANING_TIME],
                state_attrs[ATTR_CLEANED_AREA],
                state_attrs[ATTR_INITIATOR]
            ) = self.get_cleaning_status(state)

        # Error
        if self.vacuum.error_code != 0:
            state_attrs[ATTR_ERROR] = self.vacuum.error_message
            state_attrs[ATTR_ERROR_CODE] = self.vacuum.error_code

        if self.not_ready_code != 0:
            state_attrs[ATTR_NOT_READY] = self.not_ready
            state_attrs[ATTR_NOT_READY_CODE] = self.not_ready_code

        # Not all Roombas expose position data
        # https://github.com/koalazak/dorita980/issues/48
        if self._cap_position:
            pos_state = state.get("pose", {})
            position = "(0,0,0)"
            pos_x = pos_state.get("point", {}).get("x")
            pos_y = pos_state.get("point", {}).get("y")
            theta = pos_state.get("theta")
            if all(item is not None for item in (pos_x, pos_y, theta)):
                position = f"({pos_x}, {pos_y}, {theta})"
            state_attrs[ATTR_POSITION] = position

        return state_attrs

    def get_total_statistics(self, state) -> tuple[int, int, int, int, int]:
        """Return the cleaning time and cleaned area from the device."""
        if not (total := state.get("bbrun")):
            return (0, 0)
        
        cleaning_time = 0
        if clean_hrs := total.get("hr", 0):
            clean_min = total.get("min", 0)
            cleaning_time = clean_hrs * 60 + clean_min

        if cleaned_area := total.get("sqft", 0):  # Imperial
            # Convert to m2 if the unit_system is set to metric
            if self.hass.config.units.is_metric:
                cleaned_area = round(cleaned_area * 0.0929)

        missions = total.get("nMssn", 0)
        scrubs = total.get("nScrubs", 0)
        evacs = total.get("nEvacs", 0)

        return (cleaning_time, cleaned_area, missions, scrubs, evacs)        

    def get_cleaning_status(self, state) -> tuple[int, int, str]:
        """Return the cleaning time and cleaned area from the device."""
        if not (mission_state := state.get("cleanMissionStatus")):
            return (0, 0, "")

        if cleaning_time := mission_state.get("mssnM", 0):
            pass
        elif start_time := mission_state.get("mssnStrtTm"):
            now = dt_util.as_timestamp(dt_util.utcnow())
            if now > start_time:
                cleaning_time = (now - start_time) // 60

        if cleaned_area := mission_state.get("sqft", 0):  # Imperial
            # Convert to m2 if the unit_system is set to metric
            if self.hass.config.units.is_metric:
                cleaned_area = round(cleaned_area * 0.0929)

        initiator = mission_state.get("initiator", "")

        return (cleaning_time, cleaned_area, initiator)

    def on_message(self, json_data):
        """Update state on message change."""
        state = json_data.get("state", {}).get("reported", {})
        if self.new_state_filter(state):
            _LOGGER.debug("Got new state from the vacuum: %s", json_data)
            self.schedule_update_ha_state()

    async def async_start(self):
        """Start or resume the cleaning task."""
        if self.state == STATE_PAUSED:
            await self.hass.async_add_executor_job(self.vacuum.send_command, "resume")
        else:
            await self.hass.async_add_executor_job(self.vacuum.send_command, "start")

    async def async_stop(self, **kwargs):
        """Stop the vacuum cleaner."""
        await self.hass.async_add_executor_job(self.vacuum.send_command, "stop")

    async def async_pause(self):
        """Pause the cleaning cycle."""
        await self.hass.async_add_executor_job(self.vacuum.send_command, "pause")

    async def async_return_to_base(self, **kwargs):
        """Set the vacuum cleaner to return to the dock."""
        if self.state == STATE_CLEANING:
            await self.async_pause()
            for _ in range(0, 10):
                if self.state == STATE_PAUSED:
                    break
                await asyncio.sleep(1)
        await self.hass.async_add_executor_job(self.vacuum.send_command, "dock")

    async def async_locate(self, **kwargs):
        """Located vacuum."""
        await self.hass.async_add_executor_job(self.vacuum.send_command, "find")

    async def async_send_command(self, command, params=None, **kwargs):
        """Send raw command."""
        _LOGGER.debug("async_send_command %s (%s), %s", command, params, kwargs)
        await self.hass.async_add_executor_job(
            self.vacuum.send_command, command, params
        )
