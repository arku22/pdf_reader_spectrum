from PyPDF2 import PdfReader as Reader
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd


load_dotenv()

pdf_dir = os.environ.get("pdf_loc")
pdf_filenames = os.listdir(pdf_dir)
df_columns = {"statement_date": None,
              "service_from": None,
              "service_to": None,
              "wifi_service_charge": pd.Series(dtype='float'),
              "spectrum_internet_charge": pd.Series(dtype='float'),
              "promo_discount": pd.Series(dtype='float'),
              "taxes": pd.Series(dtype='float'),
              "total": pd.Series(dtype='float')}
df = pd.DataFrame(df_columns)
for filename in pdf_filenames:

    print(f"Reading file {filename}")
    reader = Reader(os.path.join(pdf_dir, filename))
    pg_1 = reader.pages[0]
    txt = pg_1.extract_text()
    txt_lines = txt.splitlines()
    imp_lines = txt_lines[13:40]

    service_from = txt_lines[5].split(' ')[2]
    date_from = datetime.strptime(service_from, "%m/%d/%y").date()
    service_to = txt_lines[5].split(' ')[4]
    date_to = datetime.strptime(service_to, "%m/%d/%y").date()
    pg_2 = reader.pages[1]
    txt_lines_pg_2 = pg_2.extract_text().splitlines()
    wifi_service_charge = float(txt_lines_pg_2[14].split(' ')[-1])
    spectrum_internet_charge = float(txt_lines_pg_2[15].split(' ')[-1])
    promotional_discount_charge = float(txt_lines_pg_2[16].split(' ')[-1])
    taxes = float(txt_lines_pg_2[22].split(' ')[-1][1:])
    total_due = round(wifi_service_charge + spectrum_internet_charge + promotional_discount_charge + taxes, 2)
    temp_dict = {"statement_date": date_from,
                 "service_from": date_from,
                 "service_to": date_to,
                 "wifi_service_charge": wifi_service_charge,
                 "spectrum_internet_charge": spectrum_internet_charge,
                 "promo_discount": promotional_discount_charge,
                 "taxes": taxes,
                 "total": total_due}
    temp_df = pd.DataFrame(temp_dict, index=[0])
    df = pd.concat([df, temp_df], axis=0, ignore_index=True)
    df.to_excel("output.xlsx")

print(df)

