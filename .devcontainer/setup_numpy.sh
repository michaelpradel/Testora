#!/bin/bash

echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing numpy-dev containers"
docker rm -f numpy-dev1
docker rm -f numpy-dev2
docker rm -f numpy-dev3

mkdir clone1
cd clone1

echo "Creating first clone of numpy"
git clone https://github.com/numpy/numpy.git
cd numpy
git submodule update --init
echo "Building dev container for numpy (first clone)"
docker run -t -d --name numpy-dev1 -v ${PWD}:/home/numpy python:3.10
docker cp /workspaces/BugGPT/.devcontainer/setup_numpy_to_run_in_container.sh numpy-dev1:/root/setup.sh
docker exec numpy-dev1 chmod +x /root/setup.sh
docker exec -w /home/numpy numpy-dev1 /root/setup.sh
echo "Done with first clone"

# TODO: 2 more clones

cd ../../../BugGPT
