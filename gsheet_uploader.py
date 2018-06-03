import gspread
from pymongo import MongoClient

from oauth2client.service_account import ServiceAccountCredentials
from bson.objectid import ObjectId

AUTH_JSON_PATH='private/auth.json'
GSHEET_KEY='private/spreadsheet_key'
DATABASE='crossdata-seg'


def auth_gss_client(path, scopes):
    credentials = ServiceAccountCredentials.from_json_keyfile_name(path, scopes)
    return gspread.authorize(credentials)

def update_sheet(gss_client, key, exp_data):
    wks = gss_client.open_by_key(key)
    exists_worksheets = [item.title for item in wks.worksheets()]
    if DATABASE not in exists_worksheets:
        wks.add_worksheet(DATABASE, 0, 0)
    sheet = wks.worksheet(DATABASE)

    upload_data = [
            str(exp_data['_id']),
            exp_data['time']['start'],
            exp_data['time']['end'],
            exp_data['time']['elapsed'],
            #exp_data['purpose'],
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
    test_id='5b12cd0b1d41c87432d6bef5' 
    post = collect.find_one({'_id': ObjectId(test_id)})

    with open(GSHEET_KEY) as f:
        skey = f.read().strip()
        update_sheet(gss_client, skey, post)

if __name__ == '__main__':
    main()
