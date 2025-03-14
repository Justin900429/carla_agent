# TTSGv2

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



