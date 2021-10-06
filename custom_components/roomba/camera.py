"""Sensor for checking the battery level of Roomba."""
from homeassistant.components.camera import Camera
from roombapy import Roomba

from . import roomba_reported_state
from .const import BLID, DOMAIN, ROOMBA_SESSION
from .irobot_base import IRobotEntity

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the iRobot Roomba vacuum cleaner."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    roomba = domain_data[ROOMBA_SESSION]
    blid = domain_data[BLID]

    entities = []

    state = roomba_reported_state(roomba)
    capabilities = state.get("cap", {})
    cap_position = capabilities.get("pose", 0) == 1
    if cap_position:
      entities.append(RoombaCamera(roomba, blid))

    async_add_entities(entities, True)

class RoombaCamera(IRobotEntity, Camera):
    """Class to hold Roomba Camera (i.e. map)"""
    def __init__(self, roomba: Roomba, blid):
        IRobotEntity.__init__(self, roomba, blid)
        Camera.__init__(self)
        self.content_type = "image/png"

    @property
    def name(self):
        """Return the name of the sensor."""
        return f"{self._name} Map"

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"map_{self._blid}"     
   
    def camera_image(self, width: int = None, height: int = None) -> bytes:
        return self.vacuum.get_map(width,height)
