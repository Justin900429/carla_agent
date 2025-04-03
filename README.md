# Carla with LLM Agent

## Introduction

### Control logic

The high-level control for the agent is shown below:

```mermaid
flowchart LR
    A(["Start"]) --> B{"check_traffic_light<br>Is the light red?"}
    B -- Yes --> C(["Slow down and brake"])
    B -- No --> D{"check_vehicle_obstacle<br>Is there an obstacle?"}
    D -- No --> G(["get_ego_car_location"])
    D -- Yes --> E{"Is ego car stationary<br>for a while?"}
    E -- No --> C
    E -- Yes --> F{"Tools → Is new<br>destination available?"}
    F -- No --> C
    F -- Yes --> G
    G --> H(["get_destination_point"])
    H --> I(["get_rotation_difference"])
    I --> J(["control_vehicle<br>Provide proper control"])

     A:::terminal
     B:::decision
     C:::action
     D:::decision
     G:::action
     E:::decision
     F:::decision
     H:::action
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