#!/bin/bash

set -e

# Be sure to "docker login" first..

docker buildx build --tag prmoorevoltron/superset-sqlalchemy-adbc-flight-sql:latest --platform linux/amd64,linux/arm64 --push .
