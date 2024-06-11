#!/bin/bash

apt install -y gcc g++ gfortran libopenblas-dev liblapack-dev pkg-config python3-pip python3-dev

wget -O Miniforge3.sh "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-$(uname)-$(uname -m).sh"
bash Miniforge3.sh -b -p "${HOME}/conda"
source "${HOME}/conda/etc/profile.d/conda.sh"
source "${HOME}/conda/etc/profile.d/mamba.sh"

mamba env create -f environment.yml
mamba activate numpy-dev

pip install -e . --no-build-isolation