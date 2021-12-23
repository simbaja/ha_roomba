"""The roomba component."""
import asyncio
import logging

from typing import Any

import async_timeout
from roombapy import RoombaConnectionError, RoombaFactory

from homeassistant import exceptions
from homeassistant.const import (
    CONF_DELAY,
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    EVENT_HOMEASSISTANT_STOP,
)
from roombapy.mapping.roomba_map_device import RoombaMapDevice
from roombapy.roomba import Roomba
from roombapy.mapping import RoombaMap, DEFAULT_ICON_SIZE
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.config_validation import ensure_list, positive_int, string
from voluptuous.error import Invalid
from voluptuous.validators import All, Range

from .const import *

_LOGGER = logging.getLogger(__name__) 

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_NO_MAP_IMAGE): str,

                vol.Optional(CONF_DEVICES): vol.All(
                    ensure_list,
                    [
                        {
                            vol.Required(CONF_BLID): str,
                            vol.Optional(CONF_MAP_ICON_SET): str,
                            vol.Optional(CONF_MAP_PATH_COLOR): str,
                            vol.Optional(CONF_MAP_PATH_WIDTH): int,
                            vol.Optional(CONF_MAP_BG_COLOR): str,
                        }
                    ],
                ),
                vol.Optional(CONF_MAPS): vol.All(
                    ensure_list,
                    [
                        {
                            vol.Required(CONF_PMAP_ID): str,
                            vol.Required(CONF_NAME): str,
                            vol.Optional(CONF_MAP_MIN_X, default=-1000): int,
                            vol.Optional(CONF_MAP_MAX_X, default=1000): int,
                            vol.Optional(CONF_MAP_MIN_Y, default=-1000): int,
                            vol.Optional(CONF_MAP_MAX_Y, default=1000): int,
                            vol.Optional(CONF_MAP_ANGLE, default=0.0): vol.All(
                                float, Range(min=-360.0, max=360.0)
                            ),
                            vol.Optional(CONF_MAP_FLOORPLAN_IMAGE): str,
                            vol.Optional(CONF_MAP_WALLS_IMAGE): str,
                            vol.Optional(CONF_MAP_ICON_SET): str,
                            vol.Optional(CONF_MAP_BG_COLOR): str,
                            vol.Optional(CONF_MAP_PATH_COLOR): str,
                            vol.Optional(CONF_MAP_PATH_WIDTH): str,
                        }
                    ],
                ),
                vol.Optional(CONF_ICONS): vol.All(
                    ensure_list,
                    [
                        {
                            vol.Required(CONF_NAME): str,
                            vol.Required(CONF_ICON_BASE_PATH): str,
                            vol.Optional(CONF_ICON_WIDTH): int,
                            vol.Optional(CONF_ICON_HEIGHT): int,
                            vol.Optional(CONF_ICON_ROOMBA): str,
                            vol.Optional(CONF_ICON_ERROR): str,
                            vol.Optional(CONF_ICON_HOME): str,
                            vol.Optional(CONF_ICON_CANCELLED): str,
                            vol.Optional(CONF_ICON_CHARGING): str,
                            vol.Optional(CONF_ICON_BATTERY_LOW): str,
                            vol.Optional(CONF_ICON_BIN_FULL): str,
                            vol.Optional(CONF_ICON_TANK_LOW): str,
                        }
                    ],
                ),                
            }
        )
    },
    extra=vol.ALLOW_EXTRA
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Roomba component."""
    conf = config.get(DOMAIN, {})

    # Make the config available for all other objects
    hass.data[DOMAIN] = {CONFIG: conf}

    return True    

async def async_setup_entry(hass, config_entry):
    """Set the config entry up."""
    # Set up roomba platforms with config entry

    if not config_entry.options:
        hass.config_entries.async_update_entry(
            config_entry,
            options={
                CONF_CONTINUOUS: config_entry.data[CONF_CONTINUOUS],
                CONF_DELAY: config_entry.data[CONF_DELAY],
            },
        )

    roomba = RoombaFactory.create_roomba(
        address=config_entry.data[CONF_HOST],
        blid=config_entry.data[CONF_BLID],
        password=config_entry.data[CONF_PASSWORD],
        continuous=config_entry.options[CONF_CONTINUOUS],
        delay=config_entry.options[CONF_DELAY],
    )

    initialize_mapping_config(roomba, hass.data[DOMAIN][CONFIG])

    try:
        if not await async_connect_or_timeout(hass, roomba):
            return False
    except CannotConnect as err:
        raise exceptions.ConfigEntryNotReady from err

    async def _async_disconnect_roomba(event):
        await async_disconnect_or_timeout(hass, roomba)

    cancel_stop = hass.bus.async_listen_once(
        EVENT_HOMEASSISTANT_STOP, _async_disconnect_roomba
    )

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][config_entry.entry_id] = {
        ROOMBA_SESSION: roomba,
        BLID: config_entry.data[CONF_BLID],
        CANCEL_STOP: cancel_stop,
    }



    hass.config_entries.async_setup_platforms(config_entry, PLATFORMS)

    if not config_entry.update_listeners:
        config_entry.add_update_listener(async_update_options)

    return True


async def async_connect_or_timeout(hass, roomba):
    """Connect to vacuum."""
    try:
        name = None
        with async_timeout.timeout(10):
            _LOGGER.debug("Initialize connection to vacuum")
            await hass.async_add_executor_job(roomba.connect)
            while not roomba.roomba_connected or name is None:
                # Waiting for connection and check datas ready
                name = roomba_reported_state(roomba).get("name", None)
                if name:
                    break
                await asyncio.sleep(1)
    except RoombaConnectionError as err:
        _LOGGER.debug("Error to connect to vacuum: %s", err)
        raise CannotConnect from err
    except asyncio.TimeoutError as err:
        # api looping if user or password incorrect and roomba exist
        await async_disconnect_or_timeout(hass, roomba)
        _LOGGER.debug("Timeout expired: %s", err)
        raise CannotConnect from err

    return {ROOMBA_SESSION: roomba, CONF_NAME: name}


async def async_disconnect_or_timeout(hass, roomba):
    """Disconnect to vacuum."""
    _LOGGER.debug("Disconnect vacuum")
    with async_timeout.timeout(3):
        await hass.async_add_executor_job(roomba.disconnect)
    return True


async def async_update_options(hass, config_entry):
    """Update options."""
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass, config_entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    if unload_ok:
        domain_data = hass.data[DOMAIN][config_entry.entry_id]
        domain_data[CANCEL_STOP]()
        await async_disconnect_or_timeout(hass, roomba=domain_data[ROOMBA_SESSION])
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok

def initialize_mapping_config(roomba: Roomba, conf: dict[str,Any]):           
    if CONF_ICONS in conf:
        for conf_icon in conf[CONF_ICONS]:
            s = DEFAULT_ICON_SIZE
            if CONF_ICON_WIDTH in conf_icon and CONF_ICON_HEIGHT in conf_icon:
                s = (conf_icon[CONF_ICON_WIDTH], conf_icon[CONF_ICON_HEIGHT])

            roomba.add_map_icon_set(
                conf_icon[CONF_NAME], 
                conf_icon[CONF_ICON_BASE_PATH],
                conf_icon.get(CONF_ICON_HOME,None),
                conf_icon.get(CONF_ICON_ROOMBA,None),
                conf_icon.get(CONF_ICON_ERROR,None),
                conf_icon.get(CONF_ICON_CANCELLED,None),
                conf_icon.get(CONF_ICON_BATTERY_LOW,None),
                conf_icon.get(CONF_ICON_CHARGING,None),
                conf_icon.get(CONF_ICON_BIN_FULL,None),
                conf_icon.get(CONF_ICON_TANK_LOW,None),
                s)

    if CONF_DEVICES in conf:
        for conf_dev in conf[CONF_DEVICES]:
            device = RoombaMapDevice(
                conf_dev[CONF_BLID],
                conf_dev.get(CONF_MAP_ICON_SET,None),
                conf_dev.get(CONF_MAP_PATH_COLOR,None),
                conf_dev.get(CONF_MAP_PATH_WIDTH,None),
                conf_dev.get(CONF_MAP_BG_COLOR,None)
            )                

            roomba.add_map_device(device) 

    if CONF_MAPS in conf:
        for conf_map in conf[CONF_MAPS]:
            map = RoombaMap(conf_map[CONF_PMAP_ID], conf_map[CONF_NAME])
            
            if CONF_MAP_MIN_X in conf_map and CONF_MAP_MIN_Y in conf_map:
                map.coords_start = (conf_map[CONF_MAP_MIN_X], conf_map[CONF_MAP_MIN_Y])
            if CONF_MAP_MAX_X in conf_map and CONF_MAP_MAX_Y in conf_map:    
                map.coords_end = (conf_map[CONF_MAP_MAX_X], conf_map[CONF_MAP_MAX_Y])

            map.angle = conf_map.get(CONF_MAP_ANGLE,None)
            map.floorplan = conf_map.get(CONF_MAP_FLOORPLAN_IMAGE,None)
            map.walls = conf_map.get(CONF_MAP_WALLS_IMAGE,None)
            map.icon_set = conf_map.get(CONF_MAP_ICON_SET,None)
            map.bg_color = conf_map.get(CONF_MAP_BG_COLOR,None)
            map.path_color = conf_map.get(CONF_MAP_PATH_COLOR,None)
            map.path_width = conf_map.get(CONF_MAP_PATH_WIDTH,None)

            roomba.add_map_definition(map)

def roomba_reported_state(roomba):
    """Roomba report."""
    return roomba.master_state.get("state", {}).get("reported", {})


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
