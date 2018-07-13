import os
import gspread

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

from .base import Keeper

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
            exp_data['time']['start'],
            exp_data['time']['end'],
            exp_data['time']['elapsed'],
            exp_data['purpose'],
            str(exp_data['args']),
            str(exp_data['src'])
            ]

    if '_id' in exp_data:
        upload_data.insert(0, str(exp_data['_id']))

    sheet.insert_row(upload_data, 2)

class GSheetKeeper(Keeper):
    def __init__(self, database=None, auth_json_path=None, gsheet_key_path=None):
        assert(os.path.isfile(auth_json_path) and os.path.isfile(gsheet_key_path))

        gss_scopes = ['https://spreadsheets.google.com/feeds']
        self.gss_client = auth_gss_client(auth_json_path, gss_scopes)
        self.sheet_name = '{}.archive'.format(database)

        with open(gsheet_key_path) as f:
            self.gsheet_key = f.read().strip()

    def push(self, data):
        update_sheet(self.gss_client, self.gsheet_key, self.sheet_name, data)
