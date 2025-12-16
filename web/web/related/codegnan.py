import pandas as pd
from flask_restful import Resource
import gspread
from oauth2client.service_account import ServiceAccountCredentials

class CodeGnan(Resource):
    def __init__(self):
        super

    def get(self):
        #data = pd.read_csv('assets/homepage.csv')
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        credentials = ServiceAccountCredentials.from_json_keyfile_name("credentials.json", scope)
        client = gspread.authorize(credentials)

        sheet_url = "https://docs.google.com/spreadsheets/d/12IBqz7aPxa4wIyUwA5qKAx2A9VExIFMSdOSYQXLt-4s/edit?pli=1&gid=0"
        sheet = client.open_by_url(sheet_url)


        worksheet = sheet.get_worksheet(0)

        rows = worksheet.get_all_values()

        data = pd.DataFrame(rows[1:], columns=rows[0])  
        data['Date'] = pd.to_datetime(data['Date'], format="%d-%m-%Y", errors='coerce')
        data['year'] = data['Date'].dt.year
        
        cleaned_data = data.dropna(subset=['Branch', 'Company Name', 'College', 'YOP'])

        yops = cleaned_data['YOP'].tolist()
        year = data['year'].tolist()
        
        yops_list = {}

        for yr in year:
            try:
                yr_int = int(yr)
                if yr_int in yops_list:
                    yops_list[yr_int] += 1
                else:
                    yops_list[yr_int] = 1
            except (ValueError, TypeError):
                continue
        
        yops_list = dict(sorted(yops_list.items(), key=lambda x: x[1], reverse=True))

        return  yops_list