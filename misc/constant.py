OBJECT_UNUSED = [
    "DashedSingleYellow",
    "Stencil_ArrowType4L",
    "oneWayL_Assembly",
    "ChevronRegion",
    "LaneR_L2_Assembly",
    "Stencil_STOP",
    "NoTurnLeft_Round_Assembly",
    "DoNotEnter_Assembly",
    "LaneR_L3Assembly",
    "LaneR_L1_Assembly",
    "Stencil_ArrowType4R",
    "SignPost_10ft",
    "NoTurn_Assembly",
    "LaneR_L0_Assembly",
    "oneWayR_Assembly",
    "MichiganTurnAssembly",
]

OBJECT_SEARCH_DICT = {
    "speed_30": ["speed_30", "Speed_30", "Speedlimit30Assembly"],
    "speed_40": ["Speed_40", "Speedlimit40Assembly"],
    "speed_60": ["speed_60", "Speed_60", "Speedlimit60Assembly"],
    "speed_90": ["Speed_90", "Speedlimit90Assembly"],
    "parallel_open_crosswalk": ["SimpleCrosswalk"],
    "ladder_crosswalk": ["LadderCrosswalk"],
    "continental_crosswalk": ["ContinentalCrosswalk"],
    "dashed_single_white": ["DashedSingleWhite"],
    "solid_single_white": ["SolidSingleWhite"],
    "crosswalk": [
        "SimpleCrosswalk",
        "LadderCrosswalk",
        "ContinentalCrosswalk",
        "SolidSingleWhite",
        "DashedSingleWhite",
    ],
    "stop_line": ["StopLine"],
    "stop_sign_on_road": ["StopSign", "Stencil_STOP"],
}

SIGNAL_UNUSED = []


SIGNAL_SEARCH_DICT = {
    "traffic_light": ["Signal_3Light_Post01"],
    "stop": ["Sign_Stop"],
    "yield": ["Sign_Yield"],
}


ACTION = [
    "turn_left",
    "turn_right",
    "go_straight",
    "change_lane_to_left",
    "change_lane_to_right",
    "stop",
    "block_the_ego",
    "cross_the_road",
    "on_the_sidewalk",
]
SPEED_MOVENT = ["slow down", "speed up", "constant"]
AGENT_BEHAVIOR = ["cautious", "normal", "aggressive"]
AGENT_TYPE = [
    "ambulance",
    "police",
    "firetruck",
    "bus",
    "truck",
    "motorcycle",
    "car",
    "pedestrian",
    "cyclist",
]
WEATHER = [
    "ClearNight",
    "ClearNoon",
    "ClearSunset",
    "CloudyNight",
    "CloudyNoon",
    "CloudySunset",
    "DustStorm",
    "HardRainNight",
    "HardRainNoon",
    "HardRainSunset",
    "MidRainSunset",
    "MidRainyNight",
    "MidRainyNoon",
    "SoftRainNight",
    "SoftRainNoon",
    "SoftRainSunset",
    "WetCloudyNight",
    "WetCloudyNoon",
    "WetCloudySunset",
    "WetNight",
    "WetNoon",
    "WetSunset",
]

ROAD_TYPE = ["driving", "sidewalk", "shoulder"]

RELATIVE_POSITION = """
- front: The agent is in front of the ego car
- back: The agent is behind the ego car
- left: The agent is on the left side of the ego car
- right: The agent is on the right side of the ego car
- front_left: The agent is in front and on the left side of the ego car
- front_right: The agent is in front and on the right side of the ego car
- back_left: The agent is behind and on the left side of the ego car
- back_right: The agent is behind and on the right side of the ego car
- road_of_left_turn: The agent is on different roads that ego car should take a left turn to reach
- road_of_right_turn: The agent is on different roads that ego car should take a right turn to reach
- road_of_straight: The agent is on different roads that ego car should go straight to reach
- at_the_destination: The agent is near at the destination of the ego car
- near_the_crosswalk: The agent is near at the crosswalk, used for pedestrian
"""

CAR_TYPE = [
    "ambulance",
    "police",
    "firetruck",
    "car",
    "truck",
    "bus",
    "motorcycle",
]
NUM_POINT_PER_CAR = 3
NULL_SPACE = 2
DISTANCE_FOR_ROUTE = 2.0
DIR_TO_COLOR = {
    "left": (0, 255, 0),
    "right": (0, 0, 255),
    "straight": (255, 0, 0),
}
LANE_TO_WAYPOINT = {
    "Driving": "get_driving",
    "Shoulder": "get_shoulder",
    "Sidewalk": "get_side_walk",
}
FRONT_CAMERA = {
    "x": -1.5,
    "y": 0.0,
    "z": 2.0,
    "roll": 0.0,
    "pitch": 0.0,
    "yaw": 0.0,
    "image_size_x": 900,
    "image_size_y": 256,
    "fov": 100,
}
BEV_CAMERA = {
    "x": 0.0,
    "y": 0.0,
    "z": 50.0,
    "roll": 0.0,
    "pitch": -90.0,
    "yaw": 0.0,
    "image_size_x": 512,
    "image_size_y": 512,
    "fov": 50.0,
}
