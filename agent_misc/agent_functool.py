import math
from dataclasses import dataclass, field

import carla
import numpy as np
from agents import RunContextWrapper, function_tool
from shapely.geometry import Polygon

from agent_misc.utils import (
    compute_distance,
    extract_location_to_string,
    get_incoming_waypoint_and_routes,
    get_trafficlight_trigger_location,
    is_within_distance,
)
from manager.carla_manager import CarlaManager

MAX_HISTORY_LENGTH = 5


@dataclass
class VehicleInfo:
    vehicle: carla.Vehicle
    carla_manager: CarlaManager
    destination_point: carla.Waypoint
    frame_idx: int = 0
    total_routes: list[carla.Waypoint] = field(default_factory=list)
    previous_control: list[str] = field(default_factory=list)
    previous_location: list[str] = field(default_factory=list)

    # Traffic Light Detection
    ignore_traffic_lights: bool = False
    traffic_light_max_distance: float = 5.0

    # Vehicle Detection
    ignore_vehicles: bool = False
    vehicle_max_distance: float = 5.0
    lane_offset: float = 0.0
    offset: float = 0.0
    low_angle_th: float = 0.0
    up_angle_th: float = 0.0
    use_bbs_detection: bool = False

    # Self properties
    lights_list: list[carla.TrafficLight] = field(default_factory=list)
    lights_map: dict[int, carla.Waypoint] = field(default_factory=dict)

    def __post_init__(self):
        self.lights_list = self.carla_manager.world_manager.get_actors().filter("*traffic_light*")
        self.lights_map = {}
        for traffic_light in self.lights_list:
            trigger_location = get_trafficlight_trigger_location(traffic_light)
            trigger_wp = self.carla_manager.world_manager.get_waypoint_from_location(trigger_location)
            self.lights_map[traffic_light.id] = trigger_wp


@function_tool
async def fetch_vehicle_destination_point(wrapper: RunContextWrapper[VehicleInfo]) -> str:
    """Return the destination point of the vehicle with x, y only

    Args:
        wrapper (RunContextWrapper[VehicleInfo]): Context of the vehicle
    """
    location = wrapper.context.destination_point.transform.location
    return extract_location_to_string(location)


@function_tool
async def fetch_vehicle_location(wrapper: RunContextWrapper[VehicleInfo]) -> str:
    """Return the location of the vehicle

    Args:
        wrapper (RunContextWrapper[VehicleInfo]): Context of the vehicle

    Returns:
        list[str]: return the location of x, y, z of the vehicle
    """
    location = wrapper.context.vehicle.get_location()
    return f"x: {location.x:.2f}, y: {location.y:.2f}, z: {location.z:.2f}"


@function_tool
async def control_vehicle(
    wrapper: RunContextWrapper[VehicleInfo],
    throttle: float,
    steer: float,
    brake: float,
    reverse: bool,
):
    """Control the vehicle. This function will not update the world but only update the vehicle's control.

    Args:
        wrapper (RunContextWrapper[VehicleInfo]): Context of the vehicle
        throttle (float): Throttle of the vehicle in [0, 1]
        steer (float): Steer of the vehicle in [-1, 1]. smaller than 0 turns the vehicle to the left. Otherwise, turns to the right.
        brake (float): Brake of the vehicle in [0, 1]
        reverse (bool): Reverse of the vehicle
    """
    print(f"throttle: {throttle}, steer: {steer}, brake: {brake}, reverse: {reverse}")
    wrapper.context.previous_control.insert(
        0, f"throttle: {throttle}, steer: {steer}, brake: {brake}, reverse: {reverse}"
    )
    wrapper.context.previous_location.insert(
        0, extract_location_to_string(wrapper.context.vehicle.get_location())
    )

    if len(wrapper.context.previous_control) > MAX_HISTORY_LENGTH:
        wrapper.context.previous_control.pop()
    if len(wrapper.context.previous_location) > MAX_HISTORY_LENGTH:
        wrapper.context.previous_location.pop()

    wrapper.context.vehicle.apply_control(
        carla.VehicleControl(throttle=throttle, steer=steer, brake=brake, reverse=reverse)
    )


@function_tool
async def fetch_rotation_difference(wrapper: RunContextWrapper[VehicleInfo]) -> str:
    """Return the rotation difference in [-1, 1].
    smaller than 0 means the destination is on the counter-clockwise side of the vehicle.
    larger than 0 means the destination is on the clockwise side of the vehicle.

    Args:
        wrapper (RunContextWrapper[VehicleInfo]): Context of the vehicle
    """
    current_loc = wrapper.context.vehicle.get_location()
    target_loc = wrapper.context.destination_point.transform.location
    current_vec = wrapper.context.vehicle.get_transform().get_forward_vector()
    target_vec = target_loc - current_loc

    current_vec = np.array([current_vec.x, current_vec.y, 0.0])
    target_vec = np.array([target_vec.x, target_vec.y, 0.0])

    wv_linalg = np.linalg.norm(target_vec) * np.linalg.norm(current_vec)
    if wv_linalg == 0:
        _dot = 1
    else:
        _dot = math.acos(np.clip(np.dot(current_vec, target_vec) / (wv_linalg), -1.0, 1.0))
    _cross = np.cross(current_vec, target_vec)
    if _cross[2] < 0:
        _dot *= -1.0
    _dot = np.clip(_dot, -1.0, 1.0)

    print(f"heading difference: {_dot:.2f}")

    return f"heading difference: {_dot:.2f}"


@function_tool
def check_affected_by_traffic_light(wrapper: RunContextWrapper[VehicleInfo]):
    """Check if there is a red light affecting the vehicle.

    Args:
        wrapper (RunContextWrapper[VehicleInfo]): Context of the vehicle

    Returns:
        bool: True if there is a red light affecting the vehicle, False otherwise.
    """
    if wrapper.context.ignore_traffic_lights:
        return False

    ego_vehicle_location = wrapper.context.vehicle.get_location()
    ego_vehicle_waypoint = wrapper.context.carla_manager.world_manager.get_waypoint_from_location(
        ego_vehicle_location
    )

    for traffic_light in wrapper.context.lights_list:
        trigger_wp = wrapper.context.lights_map[traffic_light.id]

        if trigger_wp.road_id != ego_vehicle_waypoint.road_id:
            continue

        if (
            trigger_wp.transform.location.distance(ego_vehicle_location)
            > wrapper.context.traffic_light_max_distance
        ):
            continue

        ve_dir = ego_vehicle_waypoint.transform.get_forward_vector()
        wp_dir = trigger_wp.transform.get_forward_vector()
        dot_ve_wp = ve_dir.x * wp_dir.x + ve_dir.y * wp_dir.y + ve_dir.z * wp_dir.z

        if dot_ve_wp < 0:
            continue

        if traffic_light.state != carla.TrafficLightState.Red:
            continue

        if is_within_distance(
            trigger_wp.transform,
            wrapper.context.vehicle.get_transform(),
            wrapper.context.traffic_light_max_distance,
            [0, 90],
        ):
            return True

    return False


@function_tool
def vehicle_obstacle_detected(
    wrapper: RunContextWrapper[VehicleInfo],
) -> tuple[bool, str, float]:
    """Check if there is a vehicle that can block the vehicle.

    Args:
        vehicle_list (list of carla.Vehicle): list contatining vehicle objects.
            If None, all vehicle in the scene are used
        max_distance: max freespace to check for obstacles.
            If None, the base threshold value is used

    Returns:
        tuple[bool, str, float]: True if there is a vehicle that can block the vehicle, False otherwise.
        The tuple contains a boolean value, a string of the detected vehicle's location, and a float value.
        The float value is the distance between the vehicle and the detected vehicle.
        If there is no vehicle that can block the vehicle, the tuple contains (False, "null", -1).
    """

    def get_route_polygon():
        route_bb = []
        extent_y = wrapper.context.vehicle.bounding_box.extent.y
        ego_location = wrapper.context.vehicle.get_location()
        r_ext = extent_y + wrapper.context.offset
        l_ext = -extent_y + wrapper.context.offset
        r_vec = wrapper.context.vehicle.get_transform().get_right_vector()
        p1 = ego_location + carla.Location(r_ext * r_vec.x, r_ext * r_vec.y)
        p2 = ego_location + carla.Location(l_ext * r_vec.x, l_ext * r_vec.y)
        route_bb.extend([[p1.x, p1.y, p1.z], [p2.x, p2.y, p2.z]])

        for wp in wrapper.context.total_routes:
            if ego_location.distance(wp.transform.location) > wrapper.context.vehicle_max_distance:
                break

            r_vec = wp.transform.get_right_vector()
            p1 = wp.transform.location + carla.Location(r_ext * r_vec.x, r_ext * r_vec.y)
            p2 = wp.transform.location + carla.Location(l_ext * r_vec.x, l_ext * r_vec.y)
            route_bb.extend([[p1.x, p1.y, p1.z], [p2.x, p2.y, p2.z]])

        if len(route_bb) < 3:
            return None

        return Polygon(route_bb)

    if wrapper.context.ignore_vehicles:
        return (False, "null", -1)

    vehicle = wrapper.context.vehicle
    vehicle_list = wrapper.context.carla_manager.world_manager.get_actors().filter("*vehicle*")
    max_distance = wrapper.context.vehicle_max_distance

    ego_transform = vehicle.get_transform()
    ego_location = ego_transform.location
    ego_wpt = wrapper.context.carla_manager.world_manager.get_waypoint_from_location(ego_location)

    lane_offset = wrapper.context.lane_offset
    if ego_wpt.lane_id < 0 and lane_offset != 0:
        lane_offset *= -1

    ego_front_transform = ego_transform
    ego_front_transform.location += carla.Location(
        vehicle.bounding_box.extent.x * ego_transform.get_forward_vector()
    )

    opposite_invasion = abs(wrapper.context.offset) + vehicle.bounding_box.extent.y > ego_wpt.lane_width / 2
    use_bbs = wrapper.context.use_bbs_detection or opposite_invasion or ego_wpt.is_junction

    route_polygon = get_route_polygon()

    for target_vehicle in vehicle_list:
        if target_vehicle.id == vehicle.id:
            continue

        target_transform = target_vehicle.get_transform()
        if target_transform.location.distance(ego_location) > max_distance:
            continue

        target_wpt = wrapper.context.carla_manager.world_manager.get_waypoint_from_location(
            target_transform.location, lane_type=carla.LaneType.Any
        )
        if (use_bbs or target_wpt.is_junction) and route_polygon:
            target_bb = target_vehicle.bounding_box
            target_vertices = target_bb.get_world_vertices(target_vehicle.get_transform())
            target_list = [[v.x, v.y, v.z] for v in target_vertices]
            target_polygon = Polygon(target_list)

            if route_polygon.intersects(target_polygon):
                return (
                    True,
                    extract_location_to_string(target_vehicle.get_location()),
                    compute_distance(target_vehicle.get_location(), ego_location),
                )
        else:
            if target_wpt.road_id != ego_wpt.road_id or target_wpt.lane_id != ego_wpt.lane_id + lane_offset:
                next_wpt = get_incoming_waypoint_and_routes(wrapper.context.total_routes, steps=3)
                if not next_wpt:
                    continue
                if (
                    target_wpt.road_id != next_wpt.road_id
                    or target_wpt.lane_id != next_wpt.lane_id + lane_offset
                ):
                    continue

            target_forward_vector = target_transform.get_forward_vector()
            target_extent = target_vehicle.bounding_box.extent.x
            target_rear_transform = target_transform
            target_rear_transform.location -= carla.Location(
                x=target_extent * target_forward_vector.x,
                y=target_extent * target_forward_vector.y,
            )

            if is_within_distance(
                target_rear_transform,
                ego_front_transform,
                max_distance,
                [wrapper.context.low_angle_th, wrapper.context.up_angle_th],
            ):
                return (
                    True,
                    extract_location_to_string(target_transform.location),
                    compute_distance(target_transform.location, ego_transform.location),
                )

    return (False, "null", -1)
