# Carla with LLM Agent

## Introduction

Drive a vehicle in the [CARLA](https://carla.org/) simulator with an **LLM agent** instead of a hand-written controller. At a fixed interval the agent is handed the ego car's situation and a set of tools, and it decides how to act. What it does:

- **Obeys traffic lights** — slows down and brakes when the light ahead is red.
- **Avoids obstacles** — detects vehicles blocking the way and stops behind them.
- **Follows a planned route** — a global route planner lays out the path, and the agent steers/throttles to reach the destination.
- **Reroutes when stuck** — picks a new destination when the ego car stays blocked for too long.
- **Reasons about lane changes** — checks whether a left or right lane change is allowed before committing.
- **Grounded in CARLA docs** — the simulator's documentation is indexed into a vector database for the agent to reference.

### Demo

| Stable driving | Turning left |
| :---: | :---: |
| ![Stable driving](assets/stable.gif) | ![Turning left](assets/turn_left.gif) |

### Control logic

The high-level control for the agent is shown below:

```mermaid
flowchart LR
    A(["Start"]) --> B{"check_traffic_light<br>Is the light red?"}
    B -- Yes --> C(["control_vehicle<br>Slow down and brake"])
    B -- No --> D{"check_vehicle_obstacle<br>Is there an obstacle?"}
    D -- No --> I(["get_rotation_difference"])
    D -- Yes --> E{"blocked_rounds > 5?"}
    E -- No --> C
    E -- Yes --> F{"is_left/right_lane_change_allowed<br>New destination available?"}
    F -- No --> C
    F -- Yes --> I
    I --> J(["control_vehicle<br>Provide proper control"])

     A:::terminal
     B:::decision
     C:::action
     D:::decision
     E:::decision
     F:::decision
     I:::action
     J:::terminal
    classDef terminal stroke:#2ecc71,stroke-width:2
    classDef decision stroke:#e67e22,stroke-width:2,stroke-dasharray: 5 5
    classDef action stroke:#3498db,stroke-width:1.5
    style A stroke:#D50000
    style C stroke:#00C853
```

## Setup

### Dependencies

We maintain our dependencies with `uv`. Please ensure you have it installed. To setup the project, run the following command:
```shell
uv sync
```

### Data

We use the documents from Carla as our database, please download with:
```shell
# Default version is 0.9.15
bash script/download_doc.sh

# If you want to specify a different version, run:
bash script/download_doc.sh 0.10.0
```

### API Key

Please setup the API key from [OpenAI](https://platform.openai.com/settings/organization/api-keys) and place it in `./.env` by:

```text
OPENAI_API_KEY={KEY_HERE}
```

## Usage

```shell
# Default to GPT-4o-mini. 
python chat_agent

# Specify `--model_type` to choose from different models.
python chat_agent.py --model_type gpt-4o
```