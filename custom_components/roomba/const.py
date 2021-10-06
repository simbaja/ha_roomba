"""The roomba constants."""
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
CONF_MAP_MIN_X = "map_min_x"
CONF_MAP_MAX_X = "map_max_x"
CONF_MAP_MIN_Y = "map_min_y"
CONF_MAP_MAX_Y = "map_max_y"
CONF_MAP_ROTATE_ANGLE = "map_rotate_angle"
CONF_IMAGE_WIDTH = "image_width"
CONF_IMAGE_HEIGHT = "image_height"