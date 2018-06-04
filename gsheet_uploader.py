import gspread
from pymongo import MongoClient

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from bson.objectid import ObjectId

AUTH_JSON_PATH='private/auth.json'
GSHEET_KEY='private/spreadsheet_key'
DATABASE='crossdata-seg'


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

def main():
    gss_scopes = ['https://spreadsheets.google.com/feeds']
    gss_client = auth_gss_client(AUTH_JSON_PATH, gss_scopes)

    client = MongoClient()
    db = client[DATABASE]
    collect = db['runs']
    test_id='5b14d5e01d41c88d0492623c'
    post = collect.find_one({'_id': ObjectId(test_id)})

    sheet_name = '{}.archive'.format(DATABASE)
    with open(GSHEET_KEY) as f:
        skey = f.read().strip()
        update_sheet(gss_client, skey, sheet_name, post)

if __name__ == '__main__':
    main()
