import sys
import os
import argparse

from modulegraph.modulegraph import ModuleGraph
from io import StringIO
from git import Repo
from termcolor import colored


def get_args():
    parser = argparse.ArgumentParser(description='PyTorch MNIST Example')
    parser.add_argument('--run-file', type=str)
    return parser.parse_args()


def get_dependencies_file(run_file):
    # A hack that change cwd to the basedir of run file
    old_cwd = os.getcwd()
    path = os.path.dirname(os.path.realpath(run_file))
    os.chdir(path)

    m = ModuleGraph('.')
    m.run_script(run_file)

    # A hack that redirect stdout to string
    result = StringIO()
    old_stdout = sys.stdout
    sys.stdout = result
    m.report()
    result = result.getvalue()
    sys.stdout = old_stdout

    cwd = os.getcwd()
    os.chdir(old_cwd)

    files = []
    for line in result.split('\n')[3:]:
        line = line.split()
        if len(line) != 3:
            continue
        if line[2].startswith(cwd):
            files.append(line[2])

    return files


def check(run_file, fluffy=False):

    deps = get_dependencies_file(run_file)

    path = os.path.dirname(os.path.realpath(run_file))
    repo = Repo(path, search_parent_directories=True)
    changed_files = repo.git.diff('HEAD', name_only=True)
    repo_root = repo.git.rev_parse("--show-toplevel")
    deps = [os.path.relpath(item, repo_root) for item in deps]

    exit_code = 0
    for dep in deps:
        if dep in changed_files:
            status = colored('M', 'red')
            exit_code = -1
        elif dep in repo.untracked_files:
            status = colored('U', 'magenta')
            exit_code = -1
        else:
            status = 'C'
        print(status, dep)

    if exit_code == -1:
        if not fluffy:
            print(colored('\nPlease commit modified or untracked files!', 'red'))
            exit(exit_code)
        else:
            print(colored('\nYou have modified or untracked files. Use at your own risk!', 'red'))

    return deps


if __name__ == '__main__':
    args = get_args()
    check(run_file)
