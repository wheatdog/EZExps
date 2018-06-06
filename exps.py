import os
import sys
import argparse
import importlib
import gspread
import pprint
import configparser

import local_dependency 

from datetime import datetime
from pymongo import MongoClient
from tempfile import mkstemp
from bson.objectid import ObjectId
from git import Repo
from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from bson.objectid import ObjectId
from termcolor import colored

from pytee import Pytee

DATABASE='demo'

AUTH_JSON_PATH='private/auth.json'
GSHEET_KEY='private/spreadsheet_key'

def get_args_from_file():
    config = configparser.ConfigParser()
    config.read('ezexps.ini')
    return config['default']

def get_args():

    config = get_args_from_file()

    parser = argparse.ArgumentParser(description='Experiment Wrapper')
    parser.add_argument('--fluffy-check', action='store_true',
                        help='Enable fluffy dependency check')
    parser.add_argument('--database', type=str,
                        default=config['database'] if 'database' in config else DATABASE,
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
    print(colored('==== Experiment Summary ====', 'green'))
    pp = pprint.PrettyPrinter(indent=2)
    post = {k: v for k, v in post.items() if k != 'logs'}
    pp.pprint(post)

def get_git_commit_hash(run_file):
    path = os.path.dirname(os.path.realpath(run_file))
    repo = Repo(path, search_parent_directories=True)
    return repo.git.rev_parse('HEAD')

def auth_gss_client(path, scopes):
    credentials = service_account.Credentials.from_service_account_file(
                path)
    scoped_credentials = credentials.with_scopes(scopes)
    gss_client = gspread.Client(auth=scoped_credentials)
    gss_client.session = AuthorizedSession(scoped_credentials)
    return gss_client

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


    log_fd, log_filename = mkstemp()
    os.close(log_fd)
    tee = Pytee(log_filename)
    print(log_filename)

    tee.start()
    try:
        post['artifacts'] = mod.main(exps_args)
        tee.end()
    except KeyboardInterrupt:
        tee.end()
        print(colored('The reason to stop this experiment:', 'red'), end=' ')
        post['purpose'] = '(Got interrupted: {}) {}'.format(input(), post['purpose'])

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
