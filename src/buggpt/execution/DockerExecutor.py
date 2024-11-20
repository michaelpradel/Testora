import os
import docker
import tarfile
import tempfile
from os.path import join
from os import chdir, getcwd


class DockerExecutor:
    def __init__(self, container_name, coverage_files):
        client = docker.from_env()
        self.container = client.containers.get(container_name)
        self.container.start()
        self.coverage_files = coverage_files

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

    def copy_file_from_container(self, file_path_in_container, target_dir):
        data, _ = self.container.get_archive(file_path_in_container)
        temp_tar_file = "temp.tar"
        with open(temp_tar_file, "wb") as f:
            for d in data:
                f.write(d)
        
        with tarfile.open(temp_tar_file, mode="r") as tar:
            tar.extractall(target_dir)

        os.remove(temp_tar_file)

    def execute_python_code(self, code):
        # create a fresh directory to get rid of any old state
        self.container.exec_run("rm -rf /tmp/BugGPT")
        self.container.exec_run("mkdir /tmp/BugGPT")

        self.copy_code_to_container(code, "/tmp/BugGPT/BugGPT_test_code.py")
        coverage_files = ",".join(f"\"{f}\"" for f in self.coverage_files)
        # -u to avoid non-deterministic buffering
        command = (
            f"timeout 300s python -u -m coverage run "
            f"--include={coverage_files} "
            f"--data-file /tmp/coverage_report /tmp/BugGPT/BugGPT_test_code.py"
        )

        # for scipy and numpy, make sure we run inside the their dev environment
        if self.container.name.startswith("scipy-dev"):
            command = (
                f"bash -c 'source /root/conda/etc/profile.d/conda.sh"
                f" && source /root/conda/etc/profile.d/mamba.sh && mamba activate scipy-dev"
                f" && {command}'"
            )
        elif self.container.name.startswith("numpy-dev"):
            command = (
                f"bash -c 'source /root/conda/etc/profile.d/conda.sh"
                f" && source /root/conda/etc/profile.d/mamba.sh"
                f"' && mamba activate numpy-dev && {command}'"
            )

        exec_result = self.container.exec_run(command)
        output = exec_result.output.decode("utf-8")

        self.copy_file_from_container(
            "/tmp/coverage_report", ".")
        with open("coverage_report", "r") as f:
            coverage_report = f.read()

        return output, coverage_report


if __name__ == "__main__":
    code = """
x = 23

print(x)
x.foo()
print("never reach this")
"""

    executor = DockerExecutor("pandas-dev", coverage_files=[])
    output = executor.execute_python_code(code)
    print(output)
