import sys
import os
import argparse

from modulegraph.modulegraph import ModuleGraph
from io import StringIO

def get_args():
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--run-file', type=str)
    return parser.parse_args()

def get_modulegraph_report(run_file):
    m = ModuleGraph('.')
    m.run_script(run_file)

    result = StringIO()
    old_stdout = sys.stdout
    sys.stdout = result
    m.report()
    result = result.getvalue()
    sys.stdout = old_stdout

    return result


def main(args):
    path = os.path.dirname(os.path.realpath(args.run_file))
    os.chdir(path)

    result = get_modulegraph_report(args.run_file)

    cwd = os.getcwd()
    for line in result.split('\n')[3:]:
        line = line.split()
        if len(line) != 3:
            continue
        if line[2].startswith(cwd):
            print(line[2])

if __name__ == '__main__':
    args = get_args()
    main(args)
