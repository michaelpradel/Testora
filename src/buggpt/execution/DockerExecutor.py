import docker
import tarfile
import tempfile
from os.path import join
from os import chdir, getcwd
from buggpt.util import Stats


class DockerExecutor:
    def __init__(self):
        client = docker.from_env()
        self.container = client.containers.get("BugGPT_base")
        self.container.start()

    def execute_python_test(self, code):
        Stats.test_execution_attempts += 1
        # copy code into container (via tarfile)
        with tempfile.TemporaryDirectory() as tmp_dir:
            code_file = join(tmp_dir, "code.py")
            with open(code_file, "w") as f:
                f.write(code)
            tar_file = join(tmp_dir, "archive.tar")
            with tarfile.open(tar_file, mode="w") as tar:
                wd = getcwd()
                try:
                    chdir(tmp_dir)
                    tar.add("code.py")
                finally:
                    chdir(wd)

            data = open(tar_file, "rb").read()
            self.container.put_archive("/tmp", data)

        # execute the code in the container
        exec_result = self.container.exec_run(
            "python -m unittest /tmp/code.py")
        test_execution_output = exec_result.output.decode("utf-8")
        print(f"Command results in:\n{test_execution_output}")
        if "FAIL: " in test_execution_output:
            Stats.test_failures += 1
        elif "ERROR: " in test_execution_output:
            Stats.test_errors += 1
        elif "Ran 1 test" in test_execution_output and "OK" in test_execution_output:
            Stats.test_passes += 1
        elif test_execution_output.startswith("Traceback"):
            Stats.test_crashes += 1
        else:
            print(f"Warning: Unknown test result")
            Stats.test_other_results += 1
