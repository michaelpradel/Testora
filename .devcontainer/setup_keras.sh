#!/bin/bash

echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing keras-dev containers"
docker rm -f keras-dev1
docker rm -f keras-dev2
docker rm -f keras-dev3

mkdir clone1
cd clone1

echo "Creating first clone of keras"
git clone https://github.com/keras-team/keras.git
cd keras
echo "Building dev container for keras (first clone)"
docker run -t -d --name keras-dev1 -v ${PWD}:/home/keras python:3.10
docker exec -w /home/keras keras-dev1 pip install -r requirements.txt
docker exec -w /home/keras keras-dev1 pip install -e ./
docker exec -w /home/keras keras-dev1 pip install coverage
echo "Done with first clone"

echo "Creating second clone of keras"
cd ../..
cp -r clone1 clone2
cd clone2/keras
echo "Building dev container for keras (second clone)"
docker run -t -d --name keras-dev2 -v ${PWD}:/home/keras python:3.10
docker exec -w /home/keras keras-dev2 pip install -r requirements.txt
docker exec -w /home/keras keras-dev2 pip install -e ./
docker exec -w /home/keras keras-dev2 pip install coverage
echo "Done with second clone"

echo "Creating third clone of keras"
cd ../..
cp -r clone1 clone3
cd clone3/keras
echo "Building dev container for keras (third clone)"
docker run -t -d --name keras-dev3 -v ${PWD}:/home/keras python:3.10
docker exec -w /home/keras keras-dev3 pip install -r requirements.txt
docker exec -w /home/keras keras-dev3 pip install -e ./
docker exec -w /home/keras keras-dev3 pip install coverage
echo "Done with third clone"

cd ../../../BugGPT