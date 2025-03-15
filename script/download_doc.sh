#!/bin/bash -e

VERSION=${1:-0.9.15}

# Download the zip file
wget https://github.com/carla-simulator/carla/archive/refs/tags/${VERSION}.zip
unzip -q ${VERSION}.zip
rm ${VERSION}.zip
mv carla-${VERSION}/Docs carla_docs

# Cleaning the docs
rm -rf carla_docs/img
find carla_docs -name "*.js" -type f -delete
find carla_docs -name "*.css" -type f -delete
