"""Sensor for checking the battery level of Roomba."""
from homeassistant.components.camera import Camera
from roombapy import Roomba
from roombapy.const import ROOMBA_STATES

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
        if self.vacuum.map_name:
            return f"{self.vacuum.map_name} ({self._name})"
    
        return f"{self._name}"

    @property
    def state(self):
        return self._get_state_text()

    @property
    def unique_id(self):
        """Return the ID of this sensor."""
        return f"map_{self._blid}"     
   
    def camera_image(self, width: int = None, height: int = None) -> bytes:
        return self.vacuum.get_map(width,height)

    def _get_state_text(self):
        state_text = ""
        
        vacuum_state = "Idle"
        if self.vacuum and self.vacuum.current_state:
            vacuum_state = self.vacuum.current_state
        
        if vacuum_state == "Idle":
            state_text = "Idle"
        elif vacuum_state == ROOMBA_STATES["charge"]:
            state_text = f"Charging ({self.vacuum.batPct}%)"
        elif vacuum_state == ROOMBA_STATES["recharge"]:
            state_text = f"Recharging ({self.vacuum.batPct}%)"
        elif vacuum_state == ROOMBA_STATES["pause"]:
            state_text = "Paused"
        elif vacuum_state == ROOMBA_STATES["hmPostMsn"]:
            state_text = "Returning Home"
        elif vacuum_state == ROOMBA_STATES["evac"]:
            state_text = "Emptying Bin"
        elif vacuum_state == ROOMBA_STATES["completed"]:
            state_text = "Completed"          
        elif vacuum_state == ROOMBA_STATES["run"]:
            state_text = "Running"
        elif vacuum_state == ROOMBA_STATES["stop"]:
            state_text = "Stopped"
        elif vacuum_state == ROOMBA_STATES["new"]:
            state_text = "Starting"
        elif vacuum_state == ROOMBA_STATES["stuck"]:
            expire = self.vacuum.expireM
            state_text = f'Stuck (Cancel: {expire}m)' if expire else 'Job Cancelled'
        elif vacuum_state == ROOMBA_STATES["cancelled"]:
            state_text = "Cancelled"
        elif vacuum_state == ROOMBA_STATES["hmMidMsn"]:
            if self.vacuum._flags.get("bin_full"):
                state_text = "Docking (Bin Full)"
            elif self.vacuum._flags.get("tank_low"):
                state_text = "Docking (Tank Low)"
            elif self.vacuum._flags.get("battery_low"):
                state_text = "Docking (Batt Low)"
            else:
                state_text = "Docking"
        elif vacuum_state == ROOMBA_STATES["hmUsrDock"]:
            state_text = "User Docking"
        else:
            state_text = vacuum_state
    
        return state_text