#!/bin/bash

pip install --user -r requirements.txt
pip install -e .

echo "Setting up project-under-analysis"
.devcontainer/setup_scipy.sh
.devcontainer/setup_pandas.sh
.devcontainer/setup_keras.sh
.devcontainer/setup_marshmallow.sh

## Not really supported (as of now):
# .devcontainer/setup_scikit-learn.sh
# .devcontainer/setup_numpy.sh
# .devcontainer/setup_transformers.sh
# .devcontainer/setup_pytorch_geometric.sh
# .devcontainer/setup_scapy.sh