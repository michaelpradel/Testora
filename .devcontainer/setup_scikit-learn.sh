#!/bin/bash

echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing scikit-learn containers"
docker rm -f scikit-learn-dev1
docker rm -f scikit-learn-dev2
docker rm -f scikit-learn-dev3

mkdir clone1
cd clone1

echo "Creating first clone of scikit-learn"
git clone https://github.com/scikit-learn/scikit-learn.git
cd scikit-learn
echo "Building dev container for scikit-learn (first clone)"
docker run -t -d --name scikit-learn-dev1 -v ${PWD}:/home/scikit-learn python:3.10
docker exec -w /home/scikit-learn scikit-learn-dev1 pip install wheel numpy scipy cython meson-python ninja
docker exec -w /home/scikit-learn scikit-learn-dev1 pip install --editable . --verbose --no-build-isolation --config-settings editable-verbose=true
echo "Done with first clone"

echo "Creating second clone of scikit-learn"
cd ../..
cp -r clone1 clone2
cd clone2/scikit-learn
echo "Building dev container for scikit-learn (first clone)"
docker run -t -d --name scikit-learn-dev2 -v ${PWD}:/home/scikit-learn python:3.10
docker exec -w /home/scikit-learn scikit-learn-dev2 pip install wheel numpy scipy cython meson-python ninja
docker exec -w /home/scikit-learn scikit-learn-dev2 pip install --editable . --verbose --no-build-isolation --config-settings editable-verbose=true
echo "Done with second clone"

echo "Creating third clone of scikit-learn"
cd ../..
cp -r clone1 clone3
cd clone3/scikit-learn
echo "Building dev container for scikit-learn (first clone)"
docker run -t -d --name scikit-learn-dev3 -v ${PWD}:/home/scikit-learn python:3.10
docker exec -w /home/scikit-learn scikit-learn-dev3 pip install wheel numpy scipy cython meson-python ninja
docker exec -w /home/scikit-learn scikit-learn-dev3 pip install --editable . --verbose --no-build-isolation --config-settings editable-verbose=true
echo "Done with third clone"

cd ../../../Testora
