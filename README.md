# Testora

An automated approach to check behavioral changes introduced by a pull request against natural language information associated with the pull request.

## Entry Points for Using Testora

[testora.evaluation.PreparePRChunks.py](src/testora/evaluation/PreparePRChunks.py): Adds PRs to check into a database.

[testora.RegressionFinder](src/testora/RegressionFinder.py): Fetches PRs to check from the database and applies the approach to each PR.

[testora.evaluation.EvalTaskManager](src/testora/evaluation/EvalTaskManager.py): Use this to see the status of PRs to analyze and to fetch a local copy of results from the database.

[testora.webui.WebUI](src/testora/webui/WebUI.py): Shows results of applying Testora in a web interface.

## Docker Containers

Testora uses two kinds of Docker containers:

1) A Visual Studio Code Dev Container for running Testora itself. See [devcontainer.json](.devcontainer/devcontainer.json).

2) Docker-in-docker containers for target projects to analyze with Testora. These containers are created when creating the dev container. See [postCreateCommands.sh](.devcontainer/postCreateCommands.sh).

## Note

This repository is not yet fully prepared for allowing others to use Testora.