#!/bin/bash

echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing pytorch_geometric-dev containers"
docker rm -f pytorch_geometric-dev1
docker rm -f pytorch_geometric-dev2
docker rm -f pytorch_geometric-dev3

mkdir clone1
cd clone1

echo "Creating first clone of pytorch_geometric"
git clone https://github.com/pyg-team/pytorch_geometric.git
cd pytorch_geometric
echo "Building dev container for pytorch_geometric (first clone)"
docker run -t -d --name pytorch_geometric-dev1 -v ${PWD}:/home/pytorch_geometric python:3.10
docker exec -w /home/pytorch_geometric pytorch_geometric-dev1 pip install -e '.[dev,full]'
echo "Done with first clone"

#####
echo "Creating second clone of pytorch_geometric"
cd ../..
cp -r clone1 clone2
cd clone2/pytorch_geometric
echo "Building dev container for pytorch_geometric (second clone)"
docker run -t -d --name pytorch_geometric-dev2 -v ${PWD}:/home/pytorch_geometric python:3.10
docker exec -w /home/pytorch_geometric pytorch_geometric-dev2 pip install -e '.[dev,full]'
echo "Done with second clone"

echo "Creating third clone of pytorch_geometric"
cd ../..
cp -r clone1 clone3
cd clone3/pytorch_geometric
echo "Building dev container for pytorch_geometric (third clone)"
docker run -t -d --name pytorch_geometric-dev3 -v ${PWD}:/home/pytorch_geometric python:3.10
docker exec -w /home/pytorch_geometric pytorch_geometric-dev3 pip install -e '.[dev,full]'
echo "Done with third clone"

cd ../../../Testora