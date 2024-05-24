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
docker exec -w /home/scipy scipy-dev1 apt install -y gcc g++ gfortran libopenblas-dev liblapack-dev pkg-config
docker exec -w /home/scipy scipy-dev1 wget -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
docker exec -w /home/scipy scipy-dev1 bash Miniforge3.sh -b -p "${HOME}/conda"
docker exec -w /home/scipy scipy-dev1 source "${HOME}/conda/etc/profile.d/conda.sh"
docker exec -w /home/scipy scipy-dev1 source "${HOME}/conda/etc/profile.d/mamba.sh"
docker exec -w /home/scipy scipy-dev1 mamba env create -f environment.yml
docker exec -w /home/scipy scipy-dev1 mamba activate scipy-dev
docker exec -w /home/scipy scipy-dev1 pip install -e . --no-build-isolation
echo "Done with first clone"

# todo: 2 more clones

cd ../../../BugGPT
