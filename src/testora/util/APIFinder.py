import argparse
import importlib
import inspect


def print_apis(module_name):
    module = importlib.import_module(module_name)
    for name, obj in inspect.getmembers(module):
        if callable(obj):
            print(name)


if __name__ == "__main__":
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--module", type=str,
                           help="Module to analyze (e.g., scipy.fft)")
    args = argparser.parse_args()
    print_apis(args.module)
