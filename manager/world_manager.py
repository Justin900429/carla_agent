from collections import defaultdict
from typing import Callable, Optional

import carla

from agent_misc.constant import DISTANCE_FOR_ROUTE


class WorldManager:
    def __init__(self, world=None):
        self.set_world(world)
        self.ego_vehicle: dict[int, carla.Vehicle] = {}
        self.background_vehicles: dict[int, dict[int, carla.Vehicle]] = defaultdict(lambda: {})

    def get_actors(self):
        return self.world.get_actors()

    def set_world(self, world):
        self.world = world

    @property
    def map(self):
        return self.world.get_map()

    def get_random_location_from_navigation(self):
        return self.world.get_random_location_from_navigation()

    def set_attribute(self, attribute, value):
        getattr(self.world, attribute)(value)

    def draw_point(self, location: carla.Location, color: tuple[int, int, int] = (255, 0, 0)):
        self.world.debug.draw_string(
            location,
            "O",
            color=carla.Color(*color),
            life_time=10,
            draw_shadow=False,
            persistent_lines=True,
        )

    def get_waypoint_from_location(
        self,
        location: carla.Location,
        project_to_road: bool = True,
        lane_type: carla.LaneType = carla.LaneType.Driving,
    ) -> carla.Waypoint:
        return self.map.get_waypoint(
            location,
            project_to_road=project_to_road,
            lane_type=lane_type,
        )

    def get_waypoint_from_location_with_ensure(
        self, location: carla.Location, lane_type_list: list[carla.LaneType]
    ) -> carla.Waypoint:
        for lane_type in lane_type_list:
            waypoint = self.get_waypoint_from_location(location, lane_type)
            if waypoint is not None:
                return waypoint
        return self.get_waypoint_from_location(location, carla.LaneType.Driving)

    def get_all_waypoints_from_road(self, road_id: Optional[int] = None) -> list[carla.Waypoint]:
        all_waypoints = self.map.generate_waypoints(distance=DISTANCE_FOR_ROUTE)
        road_waypoints = []
        for waypoint in all_waypoints:
            waypoint = self.map.get_waypoint(waypoint.transform.location)
            if waypoint is not None and (road_id is None or (waypoint.road_id == road_id)):
                road_waypoints.append(waypoint)
        return road_waypoints

    def compute_distance(self, location1: carla.Location, location2: carla.Location) -> float:
        return location1.distance(location2)

    def get_side_walk(self, road_id: int) -> list[carla.Waypoint]:
        road_waypoints = self.get_all_waypoints_from_road(road_id)
        side_walk_points = []
        for waypoint in road_waypoints:
            side_walk_point = self.map.get_waypoint(
                waypoint.transform.location,
                project_to_road=True,
                lane_type=carla.LaneType.Sidewalk,
            )
            if side_walk_point is not None:
                side_walk_points.append(side_walk_point)
        return side_walk_points

    def get_shoulder(self, road_id: int) -> list[carla.Waypoint]:
        road_waypoints = self.get_all_waypoints_from_road(road_id)
        shoulder_points = []
        for waypoint in road_waypoints:
            shoulder_point = self.map.get_waypoint(
                waypoint.transform.location,
                project_to_road=True,
                lane_type=carla.LaneType.Shoulder,
            )
            if shoulder_point is not None:
                shoulder_points.append(shoulder_point)
        return shoulder_points

    def get_driving(self, road_id: int) -> list[carla.Waypoint]:
        road_waypoints = self.get_all_waypoints_from_road(road_id)
        return road_waypoints

    def get_left_right_driving_points(
        self, road_id: int
    ) -> tuple[list[carla.Waypoint], list[carla.Waypoint]]:
        if not isinstance(road_id, (list, tuple)):
            road_id = [road_id]
        road_waypoints = []
        for road in road_id:
            road_waypoints.extend(self.get_driving(road))
        right_driving_points = []
        left_driving_points = []
        for driving_point in road_waypoints:
            if driving_point.lane_id < 0:
                right_driving_points.append(driving_point)
            elif driving_point.lane_id > 0:
                left_driving_points.append(driving_point)
        return right_driving_points, left_driving_points

    def get_driving_points_with_road_and_lane_id(self, road_id: int, lane_id: int) -> list[carla.Waypoint]:
        if not isinstance(road_id, (list, tuple)):
            road_id = [road_id]
        road_waypoints = []
        for road in road_id:
            road_waypoints.extend(self.get_driving(road))
        driving_points = []
        for driving_point in road_waypoints:
            if driving_point.lane_id == lane_id:
                driving_points.append(driving_point)
        return driving_points

    def spawn_actor(self, blueprint, transform, attach_to=None, tick=True):
        actor = self.world.try_spawn_actor(blueprint, transform, attach_to)
        if actor is not None and tick:
            self.world.tick()
        return actor

    def on_tick(self, callable: Callable):
        self.world.on_tick(callable)

    def tick(self, seconds=10):
        self.world.tick(seconds)

    def add_ego_vehicle(self, vehicle: carla.Vehicle):
        if vehicle.id not in self.ego_vehicle:
            self.ego_vehicle[vehicle.id] = vehicle

    def add_background_vehicle(self, ego_id: int, vehicle: carla.Vehicle):
        if vehicle.id not in self.background_vehicles[ego_id]:
            self.background_vehicles[ego_id][vehicle.id] = vehicle

    def get_all_ego_ids(self):
        return list(self.ego_vehicle.keys())

    def destroy_all_actors(self):
        for vehicle in self.ego_vehicle.values():
            if vehicle.is_alive:
                vehicle.destroy()
        for vehicles in self.background_vehicles.values():
            for vehicle in vehicles.values():
                if vehicle.is_alive:
                    vehicle.destroy()
