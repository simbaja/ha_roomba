"""The roomba component."""
import asyncio
import logging

import json

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
import voluptuous as vol
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.config_validation import ensure_list, positive_int, string
from voluptuous.error import Invalid
from voluptuous.validators import All, Range

from .const import (
    BLID,
    CANCEL_STOP,
    CONF_BLID,
    CONF_CONTINUOUS,
    DOMAIN,
    PLATFORMS,
    ROOMBA_SESSION,
    CONF_MAPS,
    CONF_PMAP_ID,
    CONF_MAP_MIN_X,
    CONF_MAP_MAX_X,
    CONF_MAP_MIN_Y,
    CONF_MAP_MAX_Y,
    CONF_MAP_ROTATE_ANGLE,
    CONF_IMAGE_WIDTH,
    CONF_IMAGE_HEIGHT
)

_LOGGER = logging.getLogger(__name__) 

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_MAPS): vol.All(
                    ensure_list,
                    [
                        {
                            vol.Required(CONF_PMAP_ID): str,
                            vol.Optional(CONF_MAP_MIN_X, default=-2000): int,
                            vol.Optional(CONF_MAP_MAX_X, default=2000): int,
                            vol.Optional(CONF_MAP_MIN_Y, default=-2000): int,
                            vol.Optional(CONF_MAP_MAX_Y, default=2000): int,
                            vol.Optional(CONF_MAP_ROTATE_ANGLE, default=0.0): vol.All(
                                float, Range(min=-360.0, max=360.0)
                            ),                                                        
                            vol.Optional(CONF_IMAGE_WIDTH, default=1024): positive_int,
                            vol.Optional(CONF_IMAGE_HEIGHT, default=1024): positive_int
                        }
                    ],
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA
)

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Withings component."""
    conf = config.get(DOMAIN, {})
    if not conf:
        return True

    # Make the config available to the oauth2 config flow.
    hass.data[DOMAIN] = {const.CONFIG: conf}

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


def roomba_reported_state(roomba):
    """Roomba report."""
    return roomba.master_state.get("state", {}).get("reported", {})


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""
