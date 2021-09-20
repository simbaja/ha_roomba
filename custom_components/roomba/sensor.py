"""Sensor for checking the battery level of Roomba."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.components.vacuum import STATE_DOCKED
from homeassistant.const import DEVICE_CLASS_BATTERY, PERCENTAGE
from homeassistant.helpers.icon import icon_for_battery_level

from . import roomba_reported_state
from .const import BLID, DOMAIN, ROOMBA_SESSION
from .irobot_base import IRobotEntity

CLEAN_BASE_STATE_MAP = {
    300: "Ready",
    301: "Ready",
    302: "Empty",
    303: "Empty",
    350: "Bag Missing",
    351: "Clogged",
    352: "Sealing Problem",
    353: "Bag Full",
    360: "Comms Problem"
}

ATTR_CB_PART_NUMBER = "part_number"
ATTR_CB_FW_VER = "fwVer"

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the iRobot Roomba vacuum cleaner."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    roomba = domain_data[ROOMBA_SESSION]
    blid = domain_data[BLID]

    entities = []

    # add the battery
    entities.append(RoombaBattery(roomba, blid))

    #if we have a clean base, add it too
    state = roomba_reported_state(roomba)
    if clean_base := state.get("dock", {}):
        entities.append(CleanBase(roomba, blid))

    async_add_entities(entities, True)

class RoombaBattery(IRobotEntity, SensorEntity):
    """Class to hold Roomba battery info."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Battery Level"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"battery_{self._blid}"

    @property
    def device_class(self):
        """Return the device class of the sensor."""
        return DEVICE_CLASS_BATTERY

    @property
    def native_unit_of_measurement(self):
        """Return the unit_of_measurement of the device."""
        return PERCENTAGE

    @property
    def icon(self):
        """Return the icon for the battery."""
        charging = bool(self._robot_state == STATE_DOCKED)

        return icon_for_battery_level(
            battery_level=self._battery_level, charging=charging
        )

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._battery_level

class CleanBase(IRobotEntity, SensorEntity):
    """Class to hold Roomba Sensor basic info."""

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Clean Base"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"clean_base_{self._blid}"

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if clean_base := self.vacuum_state.get("dock", {}):
            try:
                return CLEAN_BASE_STATE_MAP[int(clean_base["state"])]
            except:
                return "Unknown"

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        state_attrs = super().extra_state_attributes
        if not state_attrs:
            state_attrs = {}

        clean_base = self.vacuum_state.get("dock", {})
        base_state = {}
        if clean_base.get("pn") is not None:
            base_state[ATTR_CB_PART_NUMBER] = clean_base.get("pn")
        if clean_base.get("fwVer") is not None:
            base_state[ATTR_CB_FW_VER] = clean_base.get("fvVer")

        state_attrs.update(base_state)

        return state_attrs

    def new_state_filter(self, new_state):
        """Filter the new state."""
        return "dock" in new_state        