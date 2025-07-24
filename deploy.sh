#!/bin/bash

# 部署腳本：構建 Docker 映像並推送到 Docker Hub
docker build -t sacahan/mediagrabber:latest .
# 登入 Docker Hub
docker login
# 推送 Docker 映像到 Docker Hub
docker push sacahan/mediagrabber:latest
