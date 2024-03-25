import docker
import tarfile
import tempfile
from os.path import join
from os import chdir, getcwd

# def exec(cmd):
#     result = subprocess.run(cmd, shell=True, stderr=subprocess.STDOUT, stdout=subprocess.PIPE, text=True)
#     if result.returncode != 0:
#         print(result.stdout)
#         raise RuntimeError(f"Failed to execute command: {cmd}")
#     return result.stdout



class DockerExecutor:
    def __init__(self):
        client = docker.from_env()
        self.container = client.containers.get("BugGPT_base")

    def execute_python(self, code):
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
        res2 = self.container.exec_run("python -m unittest /tmp/code.py")
        print("Command results in:\n"+res2.output.decode("utf-8"))
