import argparse
import random

from testora.RegressionFinder import clean_output, get_repo
from testora.execution.DockerExecutor import DockerExecutor
from testora.execution.TestExecution import TestExecution
from testora.llms.LLMCache import LLMCache
from testora.llms.OpenAIGPT import OpenAIGPT
from testora.prompts.TestGenerationPrompt import TestGenerationPrompt
from testora.util import APIFinder
from testora.util.Logs import Event, LLMEvent, TestExecutionEvent, append_event


llm = LLMCache(OpenAIGPT())


def find_apis(module_name, container_name, cloned_repo_manager, docker_executor):
    with open(APIFinder.__file__, "r") as f:
        api_finder_code = f.read()
    output, _ = docker_executor.execute_python_code(
        api_finder_code,
        f"--module {module_name}"
    )
    return output.splitlines()


def generate_tests(project_name, qualified_api):
    prompt = TestGenerationPrompt(project_name, qualified_api)
    raw_answer = llm.query(prompt)
    append_event(LLMEvent(pr_nb=-1,
                 message="Raw answer",
                 content="\n---(next sample)---".join(raw_answer)))

    generated_tests = prompt.parse_answer(raw_answer)
    for idx, test in enumerate(generated_tests):
        append_event(LLMEvent(pr_nb=-1,
                     message=f"Generated test {idx+1}",
                     content=test))
    return generated_tests


def execute_tests(tests, cloned_repo_manager, docker_executor):
    test_executions = [TestExecution(t) for t in tests]

    append_event(
        Event(pr_nb=-1, message=f"Compiling {cloned_repo_manager.repo_name}"))

    # to trigger re-compilation (e.g., for pandas or scikit-learn)
    docker_executor.execute_python_code(
        f"import {cloned_repo_manager.module_name}")

    append_event(
        Event(pr_nb=-1,
              message=f"Done with compiling {cloned_repo_manager.repo_name}"))

    for test_execution in test_executions:
        output, coverage_report = docker_executor.execute_python_code(
            test_execution.code)
        output = clean_output(output)
        test_execution.output = output
        test_execution.coverage_report = coverage_report

        append_event(TestExecutionEvent(pr_nb=-1,
                                        message="Test execution",
                                        code=test_execution.code,
                                        output=test_execution.output))


def analyze_module(module_name):
    project_name = "scipy"

    _, cloned_repo_manager = get_repo(project_name)
    cloned_repo = cloned_repo_manager.get_cloned_repo("81de2abc")
    container_name = cloned_repo.container_name
    print(f"Using container: {container_name}")

    docker_executor = DockerExecutor(container_name,
                                     project_name=cloned_repo_manager.repo_name)

    apis = find_apis(module_name, container_name,
                     cloned_repo_manager,
                     docker_executor)
    api = random.choice(apis)
    print(f"Target API: {api}")

    qualified_api = f"{module_name}.{api}"
    tests = generate_tests(project_name, qualified_api)
    print(f"Got {len(tests)} tests for {qualified_api}")

    execute_tests(tests, cloned_repo_manager, docker_executor)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", type=str, required=True,
                        help="Module to analyze (e.g., scipy.fft)")
    args = parser.parse_args()
    analyze_module(args.module)


if __name__ == "__main__":
    main()
