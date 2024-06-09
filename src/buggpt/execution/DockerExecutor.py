import docker
import tarfile
import tempfile
from os.path import join
from os import chdir, getcwd


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

    def execute_python_code(self, code):
        self.copy_code_to_container(code, "/tmp/code.py")
        command = "timeout 30s python -u /tmp/code.py"  # -u to avoid non-deterministic buffering
        
        # for scipy, make sure we run inside the scipy-dev environment
        if self.container.name.startswith("scipy-dev"):
            command = f"bash -c 'source /root/conda/etc/profile.d/conda.sh && source /root/conda/etc/profile.d/mamba.sh && mamba activate scipy-dev && {command}"
        
        exec_result = self.container.exec_run(command)
        output = exec_result.output.decode("utf-8")
        return output


if __name__ == "__main__":
    code = """
x = 23
print(x)
x.foo()
print("never reach this")
"""

    executor = DockerExecutor("pandas-dev")
    output = executor.execute_python_code(code)
    print(output)
