#!/bin/bash

echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing marshmallow-dev containers"
docker rm -f marshmallow-dev1
docker rm -f marshmallow-dev2
docker rm -f marshmallow-dev3

mkdir clone1
cd clone1

echo "Creating first clone of marshmallow"
git clone https://github.com/marshmallow-code/marshmallow.git
cd marshmallow
echo "Building dev container for marshmallow (first clone)"
docker run -t -d --name marshmallow-dev1 -v ${PWD}:/home/marshmallow python:3.10
docker exec -w /home/marshmallow marshmallow-dev1 pip install -e '.[dev]'
echo "Done with first clone"

#####
echo "Creating second clone of marshmallow"
cd ../..
cp -r clone1 clone2
cd clone2/marshmallow
echo "Building dev container for marshmallow (second clone)"
docker run -t -d --name marshmallow-dev2 -v ${PWD}:/home/marshmallow python:3.10
docker exec -w /home/marshmallow marshmallow-dev1 pip install -e '.[dev]'
echo "Done with second clone"

echo "Creating third clone of marshmallow"
cd ../..
cp -r clone1 clone3
cd clone3/marshmallow
echo "Building dev container for marshmallow (third clone)"
docker run -t -d --name marshmallow-dev3 -v ${PWD}:/home/marshmallow python:3.10
docker exec -w /home/marshmallow marshmallow-dev1 pip install -e '.[dev]'
echo "Done with third clone"

cd ../../../BugGPT