import math
from typing import Optional

import carla
import numpy as np


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
