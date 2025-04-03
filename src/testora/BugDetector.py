import argparse

from testora.RegressionFinder import get_repo
from testora.execution.DockerExecutor import DockerExecutor
from testora.util import APIFinder


def analyze_module(module_name):
    _, cloned_repo_manager = get_repo("scipy")
    cloned_repo = cloned_repo_manager.get_cloned_repo("81de2abc")
    container_name = cloned_repo.container_name
    print(f"Using container: {container_name}")
    docker_executor = DockerExecutor(container_name,
                                     project_name=cloned_repo_manager.repo_name)

    with open(APIFinder.__file__, "r") as f:
        api_finder_code = f.read()
    output, _ = docker_executor.execute_python_code(
        api_finder_code,
        f"--module {module_name}"
    )
    print(output)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", type=str, required=True,
                        help="Module to analyze (e.g., scipy.fft)")
    args = parser.parse_args()
    analyze_module(args.module)


if __name__ == "__main__":
    main()
