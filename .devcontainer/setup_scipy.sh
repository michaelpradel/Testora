#!/bin/bash

# Stops execution if error occours
set -e 



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
cd ../..

cd ..
echo "Building base image"
docker build --progress=plain --tag scipy_testcontainer -f .devcontainer/scipy_testcontainer .

cd clones
cd clone1/scipy
echo "Building dev container for scipy (first clone)"
docker run -t -d --name scipy-dev1 -v ${PWD}:/home/scipy scipy_testcontainer
echo "Done with first clone"

echo "Creating second clone of scipy"
cd ../..
sudo cp -r clone1 clone2  
cd clone2/scipy
echo "Building dev container for scipy (second clone)"
docker run -t -d --name scipy-dev2 -v ${PWD}:/home/scipy scipy_testcontainer
echo "Done with second clone"

echo "Creating third clone of scipy"
cd ../..
sudo cp -r clone1 clone3
cd clone3/scipy
echo "Building dev container for scipy (third clone)"
docker run -t -d --name scipy-dev3 -v ${PWD}:/home/scipy scipy_testcontainer
echo "Done with third clone"

cd ../../../Testora
