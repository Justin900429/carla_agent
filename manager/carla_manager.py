import random
from typing import Optional, Tuple

import carla
import numpy as np
import pygame

from manager.world_manager import WorldManager
from tools.render import BirdeyeRender, RenderConfig, default_render_config


class CarlaManager:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 2000,
        use_render: bool = True,
        render_config: RenderConfig = default_render_config,
    ):
        self.client = carla.Client(host, port)
        self.client.set_timeout(10.0)
        self.world = self.client.get_world()
        self.traffic_manager = self.client.get_trafficmanager()
        self.world_manager = WorldManager(self.world)
        self.use_render = use_render
        self.render = None
        self.original_settings = None

        # Parameters for render
        self.render_config = render_config

    def set_world(self):
        self.world = self.client.get_world()
        self.world_manager.set_world(self.world)

    def set_carla_sync_mode(self, sync):
        settings = self.world.get_settings()
        settings.synchronous_mode = sync
        settings.fixed_delta_seconds = 0.1 if sync else None
        self.world.apply_settings(settings)
        self.traffic_manager.set_synchronous_mode(sync)

    def _init_render(self):
        pygame.init()
        flag = pygame.HWSURFACE | pygame.DOUBLEBUF

        window_size = (
            self.render_config.screen_size * 2,
            self.render_config.screen_size * self.render_config.num_scenario,
        )
        self.display = pygame.display.set_mode(window_size, flag)
        self.render = BirdeyeRender(
            world_manager=self.world_manager,
            screen_size=self.render_config.screen_size,
            obs_range=self.render_config.obs_range,
            d_behind=self.render_config.d_behind,
        )

    def __enter__(self):
        self.set_world()
        self.set_carla_sync_mode(True)
        if self.use_render:
            self._init_render()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.set_carla_sync_mode(False)
        self.world_manager.destroy_all_actors()
        if self.render is not None:
            pygame.quit()

    def get_random_location_for_spawn(
        self,
        filter_with_type: Optional[carla.LaneType] = None,
        no_junction: bool = False,
    ):
        driving_waypoints = self.world_manager.get_all_waypoints_from_road()
        if filter_with_type is not None:
            driving_waypoints = [
                waypoint
                for waypoint in driving_waypoints
                if (waypoint.lane_type & filter_with_type) == waypoint.lane_type
            ]
        if no_junction:
            driving_waypoints = [waypoint for waypoint in driving_waypoints if not waypoint.is_junction]
        return random.choice(driving_waypoints)

    def spawn_ego_vehicle(
        self,
        model: str = "vehicle.tesla.model3",
        transform: Optional[carla.Transform] = None,
        filter_with_type: Optional[carla.LaneType] = None,
        no_junction: bool = False,
    ) -> carla.Vehicle:
        blueprint = self.world.get_blueprint_library().find(model)
        if transform is None:
            transform = self.get_random_location_for_spawn(filter_with_type, no_junction).transform
        new_spawn_point = carla.Transform(transform.location + carla.Location(z=0.1), transform.rotation)
        vehicle = self.world_manager.spawn_actor(blueprint, new_spawn_point)
        if vehicle is not None:
            self.world_manager.add_ego_vehicle(vehicle)
            if self.render is not None and self.render.hero_id is None:
                self.render.set_hero(vehicle, vehicle.id)
        return vehicle

    def spawn_other_vehicle(
        self,
        ego_id: int,
        model: str = "vehicle.tesla.model3",
        transform: Optional[carla.Transform] = None,
        filter_with_type: Optional[carla.LaneType] = None,
        no_junction: bool = False,
    ) -> carla.Vehicle:
        blueprint = self.world.get_blueprint_library().find(model)
        if transform is None:
            transform = self.get_random_location_for_spawn(filter_with_type, no_junction).transform
        new_spawn_point = carla.Transform(transform.location + carla.Location(z=0.1), transform.rotation)
        vehicle = self.world_manager.spawn_actor(blueprint, new_spawn_point)
        self.world_manager.add_background_vehicle(ego_id, vehicle)
        return vehicle

    def get_frame(
        self,
        birdeye_render_types: Tuple[str, ...] = ("roadmap", "actors", "waypoints"),
    ) -> np.ndarray:
        if self.render is None:
            raise ValueError("Render is not enabled")
        birdeye_surface = self.render.render(birdeye_render_types)
        birdeye_surface = pygame.surfarray.array3d(birdeye_surface)
        center = (int(birdeye_surface.shape[0] / 2), int(birdeye_surface.shape[1] / 2))
        width = height = int(self.render.screen_size / 2)
        birdeye = birdeye_surface[
            center[0] - width : center[0] + width, center[1] - height : center[1] + height
        ]
        return self.render.display_to_rgb(birdeye, self.render_config.screen_size)
