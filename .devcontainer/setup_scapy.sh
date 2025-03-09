#!/bin/bash

echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing scapy-dev containers"
docker rm -f scapy-dev1
docker rm -f scapy-dev2
docker rm -f scapy-dev3

mkdir clone1
cd clone1

echo "Creating first clone of scapy"
git clone https://github.com/secdev/scapy.git
cd scapy
echo "Building dev container for scapy (first clone)"
docker run -t -d --name scapy-dev1 -v ${PWD}:/home/scapy python:3.10
docker exec -w /home/scapy scapy-dev1 pip install -e .
echo "Done with first clone"

#####
echo "Creating second clone of scapy"
cd ../..
cp -r clone1 clone2
cd clone2/scapy
echo "Building dev container for scapy (second clone)"
docker run -t -d --name scapy-dev2 -v ${PWD}:/home/scapy python:3.10
docker exec -w /home/scapy scapy-dev2 pip install -e .
echo "Done with second clone"

echo "Creating third clone of scapy"
cd ../..
cp -r clone1 clone3
cd clone3/scapy
echo "Building dev container for scapy (third clone)"
docker run -t -d --name scapy-dev3 -v ${PWD}:/home/scapy python:3.10
docker exec -w /home/scapy scapy-dev3 pip install -e .
echo "Done with third clone"

cd ../../../Testora