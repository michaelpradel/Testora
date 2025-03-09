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
docker cp /workspaces/Testora/.devcontainer/setup_numpy_to_run_in_container.sh numpy-dev1:/root/setup.sh
docker exec numpy-dev1 chmod +x /root/setup.sh
docker exec -w /home/numpy numpy-dev1 /root/setup.sh
echo "Done with first clone"

echo "Creating second clone of numpy"
cd ../..
cp -r clone1 clone2
cd clone2/numpy
echo "Building dev container for numpy (second clone)"
docker run -t -d --name numpy-dev2 -v ${PWD}:/home/numpy python:3.10
docker cp /workspaces/Testora/.devcontainer/setup_numpy_to_run_in_container.sh numpy-dev2:/root/setup.sh
docker exec numpy-dev2 chmod +x /root/setup.sh
docker exec -w /home/numpy numpy-dev2 /root/setup.sh
echo "Done with second clone"

echo "Creating third clone of numpy"
cd ../..
cp -r clone1 clone3
cd clone3/numpy
echo "Building dev container for numpy (third clone)"
docker run -t -d --name numpy-dev3 -v ${PWD}:/home/numpy python:3.10
docker cp /workspaces/Testora/.devcontainer/setup_numpy_to_run_in_container.sh numpy-dev3:/root/setup.sh
docker exec numpy-dev3 chmod +x /root/setup.sh
docker exec -w /home/numpy numpy-dev3 /root/setup.sh
echo "Done with third clone"


cd ../../../Testora
