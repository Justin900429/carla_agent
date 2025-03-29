import logging
import math
import re
from typing import Optional

import carla
import numpy as np

LOG_LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


class SectionColorFormatter(logging.Formatter):
    RESET = "\033[0m"

    COLOR_CODES = {
        "asctime": "\033[38;5;245m",  # Soft gray
        "name": "\033[0;34m",  # Teal/cyan
        "levelname": {
            "DEBUG": "\033[1;34m",  # Cool blue
            "INFO": "\033[1;92m",  # Light purple
            "WARNING": "\033[38;5;214m",  # Amber
            "ERROR": "\033[38;5;196m",  # Red
            "CRITICAL": "\033[38;5;199m",  # Hot pink
        },
        "funcName": "\033[0;34m",  # Teal/cyan
        "message": "\033[37m",  # White
    }

    FIELD_WIDTHS = {
        "name": 20,
        "levelname": 8,
        "funcName": 20,
    }

    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt=fmt, datefmt=datefmt)
        self.used_fields = re.findall(r"%\((.*?)\)", fmt or "")

    def format(self, record):
        # Add level color if applicable
        colorized = self._colorize_fields(record)
        return colorized

    def _colorize_fields(self, record):
        # Call the base formatter to fill in fields
        base = super().format(record)

        for field in self.used_fields:
            raw_val = str(getattr(record, field, ""))
            if field == "levelname":
                color = self.COLOR_CODES["levelname"].get(record.levelname, "")
            else:
                color = self.COLOR_CODES.get(field, "")
            pad_width = self.FIELD_WIDTHS.get(field)
            if pad_width:
                if len(raw_val) > pad_width:
                    raw_val = raw_val[: pad_width - 3] + "..."
                else:
                    total_pad = pad_width - len(raw_val)
                    left = total_pad // 2
                    right = total_pad - left
                    raw_val = " " * left + raw_val + " " * right
            colored_val = f"{color}{raw_val}{self.RESET}"
            base = base.replace(str(getattr(record, field, "")), colored_val, 1)
        return base


def setup_logger(
    logger_name: str,
    format: str = "[%(asctime)s] %(levelname)s - %(name)s - %(funcName)s - %(message)s",
    datefmt: str = "%Y-%m-%d %H:%M:%S",
    level: str = "debug",
):
    logger = logging.getLogger(logger_name)
    logger.setLevel(LOG_LEVEL_MAP[level])
    logger.propagate = False
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = SectionColorFormatter(format, datefmt=datefmt)
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


def get_incoming_waypoint_and_routes(routes: list[carla.Waypoint], steps: int) -> Optional[carla.Waypoint]:
    if len(routes) > steps:
        return routes[steps]
    else:
        try:
            return routes[-1]
        except IndexError:
            return None


def compute_distance(location_1, location_2):
    x = location_2.x - location_1.x
    y = location_2.y - location_1.y
    z = location_2.z - location_1.z
    norm = np.linalg.norm([x, y, z]) + np.finfo(float).eps
    return norm


def extract_location_to_string(location: carla.Location) -> str:
    return f"x: {location.x:.2f}, y: {location.y:.2f}"


def get_trafficlight_trigger_location(traffic_light):
    def rotate_point(point, radians):
        rotated_x = math.cos(radians) * point.x - math.sin(radians) * point.y
        rotated_y = math.sin(radians) * point.x - math.cos(radians) * point.y

        return carla.Vector3D(rotated_x, rotated_y, point.z)

    base_transform = traffic_light.get_transform()
    base_rot = base_transform.rotation.yaw
    area_loc = base_transform.transform(traffic_light.trigger_volume.location)
    area_ext = traffic_light.trigger_volume.extent

    point = rotate_point(carla.Vector3D(0, 0, area_ext.z), math.radians(base_rot))
    point_location = area_loc + carla.Location(x=point.x, y=point.y)

    return carla.Location(point_location.x, point_location.y, point_location.z)


def is_within_distance(target_transform, reference_transform, max_distance, angle_interval=None):
    target_vector = np.array(
        [
            target_transform.location.x - reference_transform.location.x,
            target_transform.location.y - reference_transform.location.y,
        ]
    )
    norm_target = np.linalg.norm(target_vector)

    if norm_target < 0.001:
        return True

    if norm_target > max_distance:
        return False

    if angle_interval is None:
        return True

    min_angle = angle_interval[0]
    max_angle = angle_interval[1]

    fwd = reference_transform.get_forward_vector()
    forward_vector = np.array([fwd.x, fwd.y])
    angle = math.degrees(math.acos(np.clip(np.dot(forward_vector, target_vector) / norm_target, -1.0, 1.0)))

    return min_angle < angle < max_angle
