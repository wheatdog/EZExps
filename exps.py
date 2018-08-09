import os
import sys
import signal
import argparse
import importlib
import pprint
import yaml
import subprocess

import local_dependency 
import keeper

from collections import OrderedDict
from datetime import datetime
from tempfile import mkstemp
from git import Repo
from termcolor import colored

from pytee import Pytee

def get_args():

    # This is a Hack for passing argument to SRCFILE
    cnt = 0
    for i in sys.argv[1:]:
        cnt += 1
        if i[-3:] == '.py':
            break

    valid_region_argv = sys.argv[:cnt+1]
    sys.argv = [sys.argv[0]] + sys.argv[cnt+1:]

    parser = argparse.ArgumentParser(description='Experiment Wrapper')
    parser.add_argument('--config-file', type=str, default='ezexps.yml',
                        help='Specify config file')

    args, remaining_argv = parser.parse_known_args(valid_region_argv)

    defaults = {
            'database': 'demo'
            }

    if args.config_file:
        assert(os.path.isfile(args.config_file))
        with open(args.config_file) as f:
            config = yaml.load(f.read())
        assert('default' in config)
        defaults = config['default']

    parser.set_defaults(**defaults)
    parser.add_argument('--fluffy-check', action='store_true',
                        help='Enable fluffy dependency check')
    parser.add_argument('--relax-mode', action='store_true',
                        help='Enable relax mode so that you don\'t have to contain get_args and main in srcfile')
    parser.add_argument('purpose', type=str,
                        help='purpoes of this experiment')
    parser.add_argument('srcfile', type=str,
                        help='source file in a form of *.py')

    args = parser.parse_args(remaining_argv[1:]) 
    assert(args.srcfile[-3:] == '.py')

    return args

def summary_exps(post):
    print(colored('\n# Experiment Summary', 'green'))
    pp = pprint.PrettyPrinter(indent=2)
    post = {k: v for k, v in post.items() if k != 'logs'}
    pp.pprint(post)

def get_git_commit_hash(run_file):
    path = os.path.dirname(os.path.realpath(run_file))
    repo = Repo(path, search_parent_directories=True)
    return repo.git.rev_parse('HEAD')

def main(args):

    # A Hack to make SRCFILE work while exps.py is in the different folder
    print(colored('Add {} to PATH'.format(os.getcwd()), 'blue'))
    sys.path.append(os.getcwd())

    src_mod = args.srcfile[:-3]
    mod = importlib.import_module(src_mod)

    post = {}

    time_start = datetime.now()

    if not args.relax_mode:
        exps_args = mod.get_args()
        post['args'] = vars(exps_args)
    else:
        post['args'] = sys.argv[1:]

    print(colored('\n# Source Files Checking', 'green'))

    post['src'] = {}
    post['src']['files'] = local_dependency.check(args.srcfile, fluffy=args.fluffy_check)
    post['src']['git_commit'] = get_git_commit_hash(args.srcfile)
    post['purpose'] = args.purpose

    log_fd, log_filename = mkstemp()
    os.close(log_fd)
    tee = Pytee(log_filename)
    print(colored('Temporary log stdout to {}'.format(log_filename), 'blue'))


    def postprocessing(post):
        file_log = open(log_filename)

        post['logs'] = file_log.read()
        os.unlink(log_filename)

        time_end = datetime.now()
        post['time'] = {}
        post['time']['start'] = time_start.strftime("%Y-%m-%d %H:%M:%S")
        post['time']['end'] = time_end.strftime("%Y-%m-%d %H:%M:%S")
        post['time']['elapsed'] = str(time_end - time_start)

        print(colored('\n# Information Logging', 'green'))
        for kpr_name, param in args.keeper.items():
            print('Push to {}...'.format(kpr_name), end='')
            full_param = {} if param == None else param
            full_param['database'] = args.database
            kpr = getattr(keeper, kpr_name)(**full_param)
            kpr.push(post)
            print(colored('done', 'green'))

        summary_exps(post)

            
    def sigint_handler(signal, frame):
        tee.end()
        print(colored('The reason to stop this experiment:', 'red'), end=' ')
        post['purpose'] = '(Got interrupted: {}) {}'.format(input(), post['purpose'])
        postprocessing(post)
        exit()

    signal.signal(signal.SIGINT, sigint_handler)

    print(colored('\n# Experiment Begin', 'green'))
    tee.start()
    if not args.relax_mode:
        post['artifacts'] = mod.main(exps_args)
    else:
        post['artifacts'] = "In relax mode, artifacts are untrackable for now"
        exec_argv = ['python', args.srcfile] + sys.argv[1:]
        subprocess.Popen(exec_argv)

    tee.end()

    postprocessing(post)

if __name__ == '__main__':
    main(get_args())
