import asyncio
import math
from dataclasses import dataclass

import carla
import numpy as np
import skimage
from agents import Agent, RunContextWrapper, Runner, function_tool

from manager.carla_manager import CarlaManager
from tools.route_planner import GlobalRoutePlanner

CALL_EVERY_N_FRAMES = 5


def get_destination_point(carla_manager: CarlaManager, vehicle: carla.Vehicle) -> carla.Location:
    destination_location = carla_manager.get_random_location_for_spawn().transform.location
    while carla_manager.world_manager.compute_distance(vehicle.get_location(), destination_location) < 50:
        destination_location = carla_manager.get_random_location_for_spawn().transform.location
    return destination_location


@dataclass
class VehicleInfo:
    vehicle: carla.Vehicle
    carla_manager: CarlaManager
    destination_point: carla.Waypoint
    frame_idx: int


@function_tool
async def fetch_vehicle_destination_point(wrapper: RunContextWrapper[VehicleInfo]) -> str:
    """Return the destination point of the vehicle

    Args:
        wrapper (RunContextWrapper[VehicleInfo]): Context of the vehicle
    """
    location = wrapper.context.destination_point.transform.location
    return f"x: {location.x:.2f}, y: {location.y:.2f}, z: {location.z:.2f}"


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


def tick_the_world(vehicle_info: VehicleInfo):
    """This function will tick the world, which is the main function to update the world

    Args:
        wrapper (RunContextWrapper[VehicleInfo]): Context of the vehicle
    """
    vehicle_info.carla_manager.world_manager.world.tick()
    frame = vehicle_info.carla_manager.get_frame()
    skimage.io.imsave(f"frames/frame_{vehicle_info.frame_idx:04d}.png", frame)
    vehicle_info.frame_idx += 1


def reach_destination(
    vehicle_info: VehicleInfo,
    threshold: float = 0.8,
) -> bool:
    diff = vehicle_info.destination_point.transform.location.distance(vehicle_info.vehicle.get_location())
    if vehicle_info.frame_idx % CALL_EVERY_N_FRAMES == 0:
        print(f"diff: {diff}")
    return diff < threshold


async def main():
    with CarlaManager() as carla_agent:
        vehicle = carla_agent.spawn_ego_vehicle()
        destination_point = get_destination_point(carla_agent, vehicle)
        route_planner = GlobalRoutePlanner(carla_agent.world_manager.map, 2.0)
        route = route_planner.trace_route(vehicle.get_location(), destination_point, point_only=True)
        vehicle_info = VehicleInfo(vehicle, carla_agent, route[2], 0)
        carla_agent.render.set_waypoints(
            [[p.transform.location.x, p.transform.location.y] for p in route[2:3]]
        )

        while not reach_destination(vehicle_info, threshold=0.5):
            if vehicle_info.frame_idx % CALL_EVERY_N_FRAMES == 0:
                agent = Agent[VehicleInfo](
                    name="Driving Assistant",
                    tools=[
                        fetch_vehicle_destination_point,
                        fetch_vehicle_location,
                        fetch_rotation_difference,
                        control_vehicle,
                    ],
                    instructions="""
                    You are a helpful assistant to control the vehicle. The scene is simulated within a Carla environment.
                    Your task is to find out the best control for the vehicle to reach the destination point.
                    Before controlling the vehicle, please check the heading difference for steering and the distance to the destination point for throttle and brake.
                    """,
                )
                await Runner.run(
                    starting_agent=agent,
                    input="Control the vehicle to the destination point.",
                    context=vehicle_info,
                )
            tick_the_world(vehicle_info)


if __name__ == "__main__":
    asyncio.run(main())
