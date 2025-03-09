
echo "Creating directory for clones"
cd ..
sudo mkdir clones
sudo chown vscode:vscode clones/
cd clones

echo "Cleaning any existing transformer containers"
docker rm -f transformers-dev1
docker rm -f transformers-dev2
docker rm -f transformers-dev3

mkdir clone1
cd clone1

echo "Creating first clone of transformers"
git clone https://github.com/huggingface/transformers.git
cd transformers
echo "Building dev container for transformers (first clone)"
docker run -t -d --name transformers-dev1 -v ${PWD}:/home/transformers python:3.10
docker exec -w /home/transformers transformers-dev1 pip install -e ".[dev]"
echo "Done with first clone"

echo "Creating second clone of transformers"
cd ../..
cp -r clone1 clone2
cd clone2/transformers
echo "Building dev container for transformers (second clone)"
docker run -t -d --name transformers-dev2 -v ${PWD}:/home/transformers python:3.10
docker exec -w /home/transformers transformers-dev2 pip install -e ".[dev]"
echo "Done with second clone"

echo "Creating third clone of transformers"
cd ../..
cp -r clone1 clone3
cd clone3/transformers
echo "Building dev container for transformers (third clone)"
docker run -t -d --name transformers-dev3 -v ${PWD}:/home/transformers python:3.10
docker exec -w /home/transformers transformers-dev3 pip install -e ".[dev]"
echo "Done with third clone"

cd ../../../Testora


