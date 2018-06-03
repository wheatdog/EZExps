import os
import sys
import importlib
import gspread

import local_dependency 

from datetime import datetime
from pymongo import MongoClient
from tempfile import mkstemp
from bson.objectid import ObjectId
from git import Repo
from oauth2client.service_account import ServiceAccountCredentials
from bson.objectid import ObjectId

PURPOSE='test this experiments'
DATABASE='crossdata-seg'
SRCFILE='main.py'
FLUFFY=False

AUTH_JSON_PATH='private/auth.json'
GSHEET_KEY='private/spreadsheet_key'

def get_git_commit_hash(run_file):
    path = os.path.dirname(os.path.realpath(run_file))
    repo = Repo(path)

    return repo.git.rev_parse('HEAD')

def auth_gss_client(path, scopes):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(path, scopes)
    return gspread.authorize(credentials)

def update_sheet(gss_client, key, exp_data):
    wks = gss_client.open_by_key(key)
    exists_worksheets = [item.title for item in wks.worksheets()]
    sheet_name = '{}.archive'.format(DATABASE)
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

def upload_to_gsheet(post):
    gss_scopes = ['https://spreadsheets.google.com/feeds']
    gss_client = auth_gss_client(AUTH_JSON_PATH, gss_scopes)

    with open(GSHEET_KEY) as f:
        skey = f.read().strip()
        update_sheet(gss_client, skey, post)

def main():

    client = MongoClient()
    db = client[DATABASE]
    collect = db['runs']

    # A Hack to make SRCFILE work while exps.py is in the different folder
    print(os.getcwd())
    sys.path.append(os.getcwd())

    src_mod = SRCFILE[:-3] if SRCFILE.endswith('.py') else SRCFILE
    mod = importlib.import_module(src_mod)

    post = {}

    time_start = datetime.now()

    args = mod.get_args()

    post['args'] = vars(args)

    post['src'] = {}
    post['src']['files'] = local_dependency.check(SRCFILE, fluffy=FLUFFY)
    post['src']['git_commit'] = get_git_commit_hash(SRCFILE)
    post['purpose'] = PURPOSE

    old_stdout = os.dup(sys.stdout.fileno())
    old_stderr = os.dup(sys.stderr.fileno())

    log_fd, log_filename = mkstemp()
    os.close(log_fd)
    print(log_filename)

    pipe_read, pipe_write = os.pipe()
    pid = os.fork()
    if pid == 0:
        # Child

        file_read = os.fdopen(pipe_read)

        with open(log_filename, 'w') as file_log:
            for content in file_read:
                print(content, end='')
                print(content, end='', file=file_log, flush=True)

            file_log.flush()
            os.fsync(file_log.fileno())

        os._exit(255)
    else:
        # Parent
        os.dup2(pipe_write, sys.stdout.fileno())
        os.dup2(pipe_write, sys.stderr.fileno())

    post['artifacts'] = mod.main(args)
    os.wait()

    os.dup2(old_stdout, sys.stdout.fileno())
    os.dup2(old_stderr, sys.stderr.fileno())

    file_log = open(log_filename)

    post['logs'] = str(file_log.read())
    os.unlink(log_filename)

    time_end = datetime.now()
    post['time'] = {}
    post['time']['start'] = time_start.strftime("%Y-%m-%d %H:%M:%S")
    post['time']['end'] = time_end.strftime("%Y-%m-%d %H:%M:%S")
    post['time']['elapsed'] = str(time_end - time_start)

    result = collect.insert_one(post)

    post = collect.find_one({'_id': ObjectId(result.inserted_id)})
    upload_to_gsheet(post)

if __name__ == '__main__':
    main()
