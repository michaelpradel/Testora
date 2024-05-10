import docker
import tarfile
import tempfile
from os.path import join
from os import chdir, getcwd
from buggpt.util import Stats


class DockerExecutor:
    def __init__(self, container_name):
        client = docker.from_env()
        self.container = client.containers.get(container_name)
        self.container.start()

    def copy_code_to_container(self, code, target_file_path):
        target_dir = target_file_path.rsplit("/", 1)[0]
        target_file_name = target_file_path.rsplit("/", 1)[1]

        with tempfile.TemporaryDirectory() as tmp_dir:
            code_file = join(tmp_dir, target_file_name)
            with open(code_file, "w") as f:
                f.write(code)
            tar_file = join(tmp_dir, "archive.tar")
            with tarfile.open(tar_file, mode="w") as tar:
                wd = getcwd()
                try:
                    chdir(tmp_dir)
                    tar.add(target_file_name)
                finally:
                    chdir(wd)

            data = open(tar_file, "rb").read()
            self.container.put_archive(target_dir, data)

    # def execute_python_test(self, code, python_project=None, is_test=True):
    #     Stats.test_execution_attempts += 1

    #     self.copy_code_to_container(code, "/tmp/code.py")

    #     # prepare command
    #     python_command = "python -m unittest /tmp/code.py" if is_test else "python /tmp/code.py"

    #     if not python_project:
    #         command = python_command
    #         workdir = None
    #     else:
    #         command = f"bash -c 'source myenv/bin/activate && {python_command}'"
    #         workdir = f"/projects_under_test/{python_project.name}"

    #     # execute the code in the container
    #     exec_result = self.container.exec_run(command, workdir=workdir)
    #     test_execution_output = exec_result.output.decode("utf-8")
    #     print(f"Command results in:\n{test_execution_output}")
    #     if "FAIL: " in test_execution_output:
    #         Stats.test_failures += 1
    #         return True, test_execution_output
    #     elif "ERROR: " in test_execution_output:
    #         Stats.test_errors += 1
    #     elif "Ran 1 test" in test_execution_output and "OK" in test_execution_output:
    #         Stats.test_passes += 1
    #     elif test_execution_output.startswith("Traceback"):
    #         Stats.test_crashes += 1
    #     else:
    #         print(f"Warning: Unknown test result")
    #         Stats.test_other_results += 1

    #     return False, None

    def execute_python_code(self, code):
        self.copy_code_to_container(code, "/tmp/code.py")
        command = "python /tmp/code.py"
        exec_result = self.container.exec_run(command, demux=True)
        stdout_output = exec_result.output[0].decode(
            "utf-8") if exec_result.output[0] else ""
        stderr_output = exec_result.output[1].decode(
            "utf-8") if exec_result.output[1] else ""
        return stdout_output, stderr_output
