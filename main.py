from PyPDF2 import PdfReader as reader
from datetime import datetime
import os


pdf_path = os.environ.get("pdf_path")
r = reader(pdf_path)
pg_1 = r.pages[0]
txt = pg_1.extract_text()
txt_lines = txt.splitlines()
imp_lines = txt_lines[13:40]
print(type(pg_1.extract_text()))
print(pg_1.extract_text())
service_from = txt_lines[5].split(' ')[2]
date_from = datetime.strptime(service_from, "%m/%d/%y").date()
service_to = txt_lines[5].split(' ')[4]
date_to = datetime.strptime(service_to, "%m/%d/%y").date()
pg_2 = r.pages[1]
txt_lines_pg_2 = pg_2.extract_text().splitlines()
wifi_service_charge = float(txt_lines_pg_2[14].split(' ')[-1])
spectrum_internet_charge = float(txt_lines_pg_2[15].split(' ')[-1])
promotional_discount_charge = float(txt_lines_pg_2[16].split(' ')[-1])
taxes = float(txt_lines_pg_2[22].split(' ')[-1][1:])
total_due = round(wifi_service_charge + spectrum_internet_charge + promotional_discount_charge + taxes, 2)

