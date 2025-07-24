# Testora: Regression Testing with a Natural Language Oracle

Testora is an automated approach to check behavioral changes introduced by a pull request against the title, description, etc. of the pull request.

Paper:
[https://arxiv.org/abs/2503.18597](https://arxiv.org/abs/2503.18597)

## Installation

Testora uses two kinds of Docker containers:

* A Visual Studio Code Dev Container for running Testora itself. See [devcontainer.json](.devcontainer/devcontainer.json).

* Docker-in-docker containers for target projects to analyze with Testora. These containers are created when creating the dev container. See [postCreateCommands.sh](.devcontainer/postCreateCommands.sh).

To install and run Testora, follow these steps:

1) Install [Visual Studio Code](https://code.visualstudio.com/download) and its ["Dev Containers" extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers).

2) Open Testora in Visual Studio Code:
   
   ```code .```

3) In Visual Studio Code, build the Dev Container and reopen the project in the container:

    ```Ctrl + Shift + P```

    ```Dev Containers: Rebuild and Reopen in Container```

    This will take a couple of minutes, because in addition to Testora, it will set up three instances of the project under analysis. We use three instances to efficiently switch between the commits just before and just after a PR, as well as the latest commit in the main branch.

4) In the main directory, create a file `.openai_token` with an OpenAI API key. This is required for invoking an LLM, which is an essential part of Testora.

5) In the main directory, create a file `.github_token` with a (free to create) GitHub API key. This is required because Testora interacts with the GitHub API to retrieve details about the PRs to analyze.

## Running Testora on a Single Pull Request

[testora.RegressionFinder](src/testora/RegressionFinder.py) is the main entry point to run Testora.
To apply it to a specific PR of a project, run it like this:

```python -m testora.RegressionFinder --project scipy --pr 21768```

The project must be one of the projects that were set up while building the Dev Container. The above command produces a `logs_<timestamp>.json` file.

## Inspecting Results in the Web UI

We provide a Web UI to inspect detailed logs of Testora.

1) Launch the web server:

    ```python -m testora.webui.WebUI --files logs_*.json```

2) Visit [http://localhost:4000/](http://localhost:4000/) in your browser.

3) Click on the value in the "Status" column to inspect the detailed logs of a PR.

## Running Testora on Many Pull Requests

For large-scale experiments, we use an SQL database that stores PRs to analyze and, once a PR has been analyzed, stores the results of Testora on this PR.
The database itself is *not* part of this public release, but you may replicate the setup with your own database using [these two database schemas](src/testora/evaluation/sql/).

Assuming you have set up the database:

1) Add PRs to check into the database:

    ```python -m testora.evaluation.PreparePRChunks```

2) Run [testora.RegressionFinder](src/testora/RegressionFinder.py) in database mode, which fetches PRs to check from the database and applies the approach to each PR.

    ```python -m testora.RegressionFinder --db```

    You can launch multiple instances of this command in parallel in different Dev Containers. Each of the parallel instances will fetch one PR at a time and write the result back into the database, until all PRs have been analyzed.

3) Check the status of PRs to analyze:

    ```python -m testora.evaluation.EvalTaskManager --status```

4) Once some or all PRs have been analyzed, download the results (i.e., `logs_*.json` files) from the database for inspection:

    ```python -m testora.evaluation.EvalTaskManager --fetch```

    To inspect the logs, use the WebUI as described above.

## Results Reported in the Paper

### RQ1: Real-World Problems Found by Testora

See [this sheet](https://docs.google.com/spreadsheets/d/1We-EwrNv_0U1Wco_eAUbxwjyFkkPI9kM7tkaRgP0yyI/edit?usp=sharing) for details on the 30 real-world problems, the corresponding PRs, the issues we reported, and their status.

### RQ2 (Effectiveness of Test Generation) and RQ4 (Costs)

Download the logs as described in [DATA.md](data/DATA.md).
This will create a folder [data/results_03_2025/](data/results_03_2025/), which contains the raw logs of running Testora in its default configuration.

To analyze the logs, run the following command:

```python -m testora.evaluation.PRAnalysisStats```

It will do the following:
 * Read the logs of all 1,274 PRs analyzed for RQ2 and RQ4
 * Compute the test generation statistics reported in RQ2
 * Compute the token cost statistics reported in RQ4
 * Output the corresponding LaTeX tables
 * Output LaTeX macros that define results used repeatedly in the paper (e.g., monetary cost per PR)
 * Write the plots that show time costs and token costs into [data/figures](data/figures)

### RQ3: Accuracy of Classifier

Our dataset of 164 manually labeled data points is in [data/ground_truth](data/ground_truth).

To run evaluate the classifier against the ground truth, we use [ClassificationEvaluator.py](src/testora/evaluation/ClassificationEvaluator.py). 
If not done yet for RQ2, download the logs as described in [DATA.md](data/DATA.md).
Afterward, the raw logs of running Testora with three LLMs (GPT-4o-mini, GPT-4o, DeepSeek-R1) and two different prompting techniques (multi-question classifier, single-question classifier) are available in [data/classification_results_03_2025/](data/classification_results_03_2025/).

To compute the precision, recall, and F1 score, run the following command:

```python -m testora.evaluation.ClassificationResultsSummarizer```

It will output detailed results for each PR in the ground truth dataset, and the at end, the overall results.
To switch between different LLMs and prompting techniques, edit [ClassificationResultsSummarizer.py](src/testora/evaluation/ClassificationResultsSummarizer.py) to modify the lines at the beginning that select a model-prompt combination.
