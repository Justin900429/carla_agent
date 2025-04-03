import asyncio
import base64
import os

import carla
import cv2
import numpy as np
import skimage
import tyro
from agents import Agent, Runner, set_tracing_export_api_key
from dotenv import load_dotenv

from agent_misc.agent_functool import (
    VehicleInfo,
    check_traffic_light,
    check_vehicle_obstacle,
    control_vehicle,
    get_rotation_difference,
    is_left_lane_change_allowed,
    is_right_lane_change_allowed,
)
from agent_misc.constant import SYSTEM_PROMPT_WO_VISION
from agent_misc.utils import setup_logger
from manager.carla_manager import CarlaManager
from tools.route_planner import GlobalRoutePlanner

CALL_EVERY_N_FRAMES = 5
REACH_DESTINATION_THRESHOLD = 5

chat_agent_logger = setup_logger(
    "chat_agent",
    format="[%(asctime)s] %(levelname)s - %(message)s",
    level="info",
)


def random_generate_destination_point(
    carla_manager: CarlaManager, location: carla.Location
) -> carla.Location:
    destination_location = carla_manager.get_random_waypoint_for_spawn().transform.location
    while carla_manager.world_manager.compute_distance(location, destination_location) < 50:
        destination_location = carla_manager.get_random_waypoint_for_spawn().transform.location
    return destination_location


def encode_image_for_llm_agent(image: np.ndarray) -> str:
    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode(".jpg", image)
    return base64.b64encode(buffer).decode("utf-8")


def save_frame(vehicle_info: VehicleInfo, frame_path: str, increment: bool = False):
    os.makedirs(frame_path, exist_ok=True)
    frame = vehicle_info.carla_manager.get_frame()
    skimage.io.imsave(os.path.join(frame_path, f"frame_{vehicle_info.frame_idx:04d}.png"), frame)
    if increment:
        vehicle_info.frame_idx += 1


def format_previous_control_to_string(previous_control: list[str]) -> str:
    gather_control = "\n".join(previous_control)
    return f"Previous control (newest to oldest):\n{gather_control}"


def format_previous_location_to_string(previous_location: list[str]) -> str:
    gather_location = "\n".join(previous_location)
    return f"Previous location (newest to oldest):\n{gather_location}"


def tick_the_world(vehicle_info: VehicleInfo):
    """This function will tick the world, which is the main function to update the world"""
    vehicle_info.carla_manager.world_manager.world.tick()


def reach_destination(
    vehicle_info: VehicleInfo,
    threshold: float = 0.8,
) -> bool:
    diff = vehicle_info.destination_point.transform.location.distance(vehicle_info.vehicle.get_location())
    if vehicle_info.frame_idx % CALL_EVERY_N_FRAMES == 0:
        chat_agent_logger.info(f"Distance to destination: {diff:.3f}")
    return diff < threshold


async def chat_with_agent(model_type: str = "gpt-4o-mini"):
    with CarlaManager() as carla_agent:
        start_point = carla_agent.get_random_waypoint_for_spawn(
            filter_with_type=carla.LaneType.Driving, no_junction=True
        ).transform.location
        destination_point = random_generate_destination_point(carla_agent, start_point)
        route_planner = GlobalRoutePlanner(carla_agent.world_manager.map, 2.0)
        route = route_planner.trace_route(start_point, destination_point, point_only=True)
        vehicle = carla_agent.spawn_ego_vehicle(
            filter_with_type=carla.LaneType.Driving, transform=route[0].transform
        )
        vehicle_info = VehicleInfo(
            vehicle=vehicle,
            carla_manager=carla_agent,
            destination_point=destination_point,
            route_planner=route_planner,
            frame_idx=0,
        )

        # Spawn a vehicle that block in front of the ego (testing)
        new_spawn_waypoint = route[0].next(10)
        if new_spawn_waypoint is not None:
            new_spawn_location = new_spawn_waypoint[0].transform.location
            new_spawn_location = carla_agent.world_manager.get_waypoint_from_location(new_spawn_location)
            carla_agent.spawn_other_vehicle(vehicle.id, transform=new_spawn_location.transform)
        else:
            chat_agent_logger.info("No new spawn waypoint found")
            return

        vehicle_info.total_routes = route
        try:
            while len(vehicle_info.total_routes) > 0:
                point = vehicle_info.total_routes[0]
                plot_length = min(len(vehicle_info.total_routes), 10)
                carla_agent.render.set_waypoints(
                    [
                        [p.transform.location.x, p.transform.location.y]
                        for p in vehicle_info.total_routes[:plot_length]
                    ]
                )
                vehicle_info.destination_point = point
                while not reach_destination(vehicle_info, threshold=REACH_DESTINATION_THRESHOLD):
                    if vehicle_info.frame_idx % CALL_EVERY_N_FRAMES == 0:
                        agent = Agent[VehicleInfo](
                            name="Driving Assistant",
                            tools=[
                                check_traffic_light,
                                check_vehicle_obstacle,
                                get_rotation_difference,
                                control_vehicle,
                                is_left_lane_change_allowed,
                                is_right_lane_change_allowed,
                            ],
                            instructions=SYSTEM_PROMPT_WO_VISION,
                            model=model_type,
                        )
                        # frame = vehicle_info.carla_manager.get_frame()
                        # base64_image = encode_image_for_llm_agent(frame)
                        await Runner.run(
                            starting_agent=agent,
                            input=[
                                {
                                    "role": "user",
                                    "content": [
                                        {
                                            "type": "input_text",
                                            "text": "Control the vehicle to the destination point.\n"
                                            f"Round for ego being blocked: {vehicle_info.blocked_rounds}\n"
                                            f"{format_previous_control_to_string(vehicle_info.previous_control)}\n"
                                            f"{format_previous_location_to_string(vehicle_info.previous_location)}",
                                        },
                                        # {
                                        #     "type": "input_image",
                                        #     "image_url": f"data:image/jpeg;base64,{base64_image}",
                                        # },
                                    ],
                                }
                            ],
                            context=vehicle_info,
                        )
                    tick_the_world(vehicle_info)
                    save_frame(vehicle_info, "frames", increment=True)
                vehicle_info.total_routes.pop(0)
        except KeyboardInterrupt:
            chat_agent_logger.info("Closing")


def main(model_type: str = "gpt-4o-mini"):
    asyncio.run(chat_with_agent(model_type))


if __name__ == "__main__":
    load_dotenv()
    set_tracing_export_api_key(os.getenv("OPENAI_API_KEY"))
    tyro.cli(main)
