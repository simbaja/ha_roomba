"""Support for Wi-Fi enabled iRobot Roombas."""
from . import roomba_reported_state
from .braava import BraavaJet
from .const import BLID, DOMAIN, ROOMBA_SESSION, SERVICE_CLEAN_ROOMS
from .roomba import RoombaVacuum, RoombaVacuumCarpetBoost
from homeassistant.helpers import entity_platform

import voluptuous as vol
import homeassistant.helpers.config_validation as cv

ATTR_PMAP = "pmap"
ATTR_REGIONS = "regions"

async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the iRobot Roomba vacuum cleaner."""
    domain_data = hass.data[DOMAIN][config_entry.entry_id]
    roomba = domain_data[ROOMBA_SESSION]
    blid = domain_data[BLID]

    # Get the platform
    platform = entity_platform.async_get_current_platform()

    # Get the capabilities of our unit
    state = roomba_reported_state(roomba)
    capabilities = state.get("cap", {})
    cap_carpet_boost = capabilities.get("carpetBoost")
    detected_pad = state.get("detectedPad")
    if detected_pad is not None:
        constructor = BraavaJet
    elif cap_carpet_boost == 1:
        constructor = RoombaVacuumCarpetBoost
    else:
        constructor = RoombaVacuum

    roomba_vac = constructor(roomba, blid)
    async_add_entities([roomba_vac], True)

    platform.async_register_entity_service(
    SERVICE_CLEAN_ROOMS,
    {
        vol.Optional(ATTR_PMAP): vol.All(cv.string),
        vol.Required(ATTR_REGIONS): vol.All(cv.ensure_list)
    },
    clean_rooms)


async def clean_rooms(entity, service_call):
    await entity.async_clean_rooms(
        service_call.data.get(ATTR_PMAP,None), 
        service_call.data[ATTR_REGIONS])    
