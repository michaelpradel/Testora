#!/bin/bash

pip install --user -r requirements.txt
pip install -e .

echo "Setting up pandas"
# .devcontainer/setup_pandas.sh
# .devcontainer/setup_scikit-learn.sh
# .devcontainer/setup_scipy.sh
.devcontainer/setup_numpy.sh