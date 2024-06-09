#!/bin/bash

echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing scipy-dev containers"
docker rm -f scipy-dev1
docker rm -f scipy-dev2
docker rm -f scipy-dev3

mkdir clone1
cd clone1

echo "Creating first clone of scipy"
git clone https://github.com/scipy/scipy.git
cd scipy
git submodule update --init
echo "Building dev container for scipy (first clone)"
docker run -t -d --name scipy-dev1 -v ${PWD}:/home/scipy python:3.10
docker cp /workspaces/BugGPT/.devcontainer/setup_scipy_to_run_in_container.sh scipy-dev1:/root/setup.sh
docker exec scipy-dev1 chmod +x /root/setup.sh
docker exec -w /home/scipy scipy-dev1 /root/setup.sh
echo "Done with first clone"

echo "Creating second clone of scipy"
cd ../..
cp -r clone1 clone2
cd clone2/scipy
echo "Building dev container for scipy (second clone)"
docker run -t -d --name scipy-dev2 -v ${PWD}:/home/scipy python:3.10
docker cp /workspaces/BugGPT/.devcontainer/setup_scipy_to_run_in_container.sh scipy-dev2:/root/setup.sh
docker exec scipy-dev2 chmod +x /root/setup.sh
docker exec -w /home/scipy scipy-dev2 /root/setup.sh
echo "Done with second clone"

echo "Creating third clone of scipy"
cd ../..
cp -r clone1 clone3
cd clone3/scipy
echo "Building dev container for scipy (third clone)"
docker run -t -d --name scipy-dev3 -v ${PWD}:/home/scipy python:3.10
docker cp /workspaces/BugGPT/.devcontainer/setup_scipy_to_run_in_container.sh scipy-dev3:/root/setup.sh
docker exec scipy-dev3 chmod +x /root/setup.sh
docker exec -w /home/scipy scipy-dev3 /root/setup.sh
echo "Done with third clone"

cd ../../../BugGPT
