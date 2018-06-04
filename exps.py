import os
import sys
import argparse
import importlib
import gspread
import pprint

import local_dependency 

from datetime import datetime
from pymongo import MongoClient
from tempfile import mkstemp
from bson.objectid import ObjectId
from git import Repo
from oauth2client.service_account import ServiceAccountCredentials
from bson.objectid import ObjectId

DATABASE='crossdata-seg'
FLUFFY=False

AUTH_JSON_PATH='private/auth.json'
GSHEET_KEY='private/spreadsheet_key'

def get_args():
    parser = argparse.ArgumentParser(description='Experiment Wrapper')
    parser.add_argument('--fluffy-check', action='store_true', default=FLUFFY,
                        help='Enable fluffy dependency check')
    parser.add_argument('--database', type=str, default=DATABASE,
                        help='database')
    parser.add_argument('purpose', type=str,
                        help='purpoes of this experiment')
    parser.add_argument('srcfile', type=str,
                        help='source file in a form of *.py')

    # This is a Hack for passing argument to SRCFILE
    cnt = 0
    for i in sys.argv[1:]:
        cnt += 1
        if i[-3:] == '.py':
            break

    old_argv = sys.argv
    sys.argv = sys.argv[:cnt+1]
    args = parser.parse_args() 
    assert(args.srcfile[-3:] == '.py')

    sys.argv = old_argv[cnt+1:]
    sys.argv.insert(0, old_argv[0])
    return args

def summary_exps(post):
    pp = pprint.PrettyPrinter(indent=2)
    post = {k: v for k, v in post.items() if k != 'logs'}
    pp.pprint(post)

def get_git_commit_hash(run_file):
    path = os.path.dirname(os.path.realpath(run_file))
    repo = Repo(path, search_parent_directories=True)
    return repo.git.rev_parse('HEAD')

def auth_gss_client(path, scopes):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(path, scopes)
    return gspread.authorize(credentials)

def update_sheet(gss_client, key, sheet_name, exp_data):
    wks = gss_client.open_by_key(key)
    exists_worksheets = [item.title for item in wks.worksheets()]
    if sheet_name not in exists_worksheets:
        wks.add_worksheet(sheet_name, 0, 0)
    sheet = wks.worksheet(sheet_name)

    upload_data = [
            str(exp_data['_id']),
            exp_data['time']['start'],
            exp_data['time']['end'],
            exp_data['time']['elapsed'],
            exp_data['purpose'],
            str(exp_data['args']),
            str(exp_data['src'])
            ]

    sheet.insert_row(upload_data, 2)

def upload_to_gsheet(post, sheet_name):
    gss_scopes = ['https://spreadsheets.google.com/feeds']
    gss_client = auth_gss_client(AUTH_JSON_PATH, gss_scopes)

    with open(GSHEET_KEY) as f:
        skey = f.read().strip()
        update_sheet(gss_client, skey, sheet_name, post)

def main(args):

    client = MongoClient()
    db = client[args.database]
    collect = db['runs']

    # A Hack to make SRCFILE work while exps.py is in the different folder
    print(os.getcwd())
    sys.path.append(os.getcwd())

    src_mod = args.srcfile[:-3]
    mod = importlib.import_module(src_mod)

    post = {}

    time_start = datetime.now()

    exps_args = mod.get_args()

    post['args'] = vars(exps_args)

    post['src'] = {}
    post['src']['files'] = local_dependency.check(args.srcfile, fluffy=args.fluffy_check)
    post['src']['git_commit'] = get_git_commit_hash(args.srcfile)
    post['purpose'] = args.purpose

    old_stdout = os.dup(sys.stdout.fileno())
    old_stderr = os.dup(sys.stderr.fileno())

    log_fd, log_filename = mkstemp()
    os.close(log_fd)
    print(log_filename)

    pipe_read, pipe_write = os.pipe()
    pid = os.fork()
    if pid == 0:
        # Child
        os.close(pipe_write)

        file_read = os.fdopen(pipe_read)

        with open(log_filename, 'w') as file_log:
            for content in file_read:
                print(content, end='')
                print(content, end='', file=file_log)

            file_log.flush()
            os.fsync(file_log.fileno())

        os._exit(255)
    else:
        # Parent
        os.dup2(pipe_write, sys.stdout.fileno())
        os.dup2(pipe_write, sys.stderr.fileno())

    post['artifacts'] = mod.main(exps_args)

    os.dup2(old_stdout, sys.stdout.fileno())
    os.dup2(old_stderr, sys.stderr.fileno())
    os.close(pipe_write)
    os.waitpid(pid, 0)

    file_log = open(log_filename)

    post['logs'] = file_log.read()
    os.unlink(log_filename)

    time_end = datetime.now()
    post['time'] = {}
    post['time']['start'] = time_start.strftime("%Y-%m-%d %H:%M:%S")
    post['time']['end'] = time_end.strftime("%Y-%m-%d %H:%M:%S")
    post['time']['elapsed'] = str(time_end - time_start)

    result = collect.insert_one(post)
    post = collect.find_one({'_id': ObjectId(result.inserted_id)})

    summary_exps(post)
    sheet_name = '{}.archive'.format(args.database)
    upload_to_gsheet(post, sheet_name)

if __name__ == '__main__':
    main(get_args())
