"""The roomba constants."""
from homeassistant.const import CONF_PATH

DOMAIN = "roomba"
CONFIG = "config"
PLATFORMS = ["sensor", "binary_sensor", "vacuum", "camera"]
CONF_CERT = "certificate"
CONF_CONTINUOUS = "continuous"
CONF_BLID = "blid"
DEFAULT_CERT = "/etc/ssl/certs/ca-certificates.crt"
DEFAULT_CONTINUOUS = True
DEFAULT_DELAY = 1
ROOMBA_SESSION = "roomba_session"
BLID = "blid_key"
CANCEL_STOP = "cancel_stop"

SERVICE_CLEAN_ROOMS = "clean_rooms"

#yaml-based config
CONF_MAPS = "maps"
CONF_PMAP_ID = "pmap_id"
CONF_MAP_MIN_X = "min_x"
CONF_MAP_MAX_X = "max_x"
CONF_MAP_MIN_Y = "min_y"
CONF_MAP_MAX_Y = "max_y"
CONF_MAP_ANGLE = "angle"
CONF_MAP_ICON_SET = "icon_set"
CONF_MAP_FLOORPLAN_IMAGE = "floorplan_image"
CONF_MAP_WALLS_IMAGE = "walls_image"
CONF_MAP_BG_COLOR = "bg_color"
CONF_MAP_PATH_COLOR = "path_color"
CONF_MAP_PATH_WIDTH = "path_width"
CONF_NO_MAP_IMAGE = "no_map_image"

CONF_ICONS = "icons"
CONF_ICON_BASE_PATH = "base_path"
CONF_ICON_ERROR = "error"
CONF_ICON_ROOMBA = "roomba"
CONF_ICON_CANCELLED = "cancelled"
CONF_ICON_BATTERY_LOW = "battery_low"
CONF_ICON_CHARGING = "charging"
CONF_ICON_BIN_FULL = "bin_full"
CONF_ICON_TANK_LOW = "tank_low"
CONF_ICON_HOME = "home"
CONF_ICON_WIDTH = "width"
CONF_ICON_HEIGHT = "height"

CONF_DEVICES = "devices"

