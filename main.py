from PyPDF2 import PdfReader as Reader
from datetime import datetime
import os
from dotenv import load_dotenv
import pandas as pd
import re


# load env variables
load_dotenv()
pdf_dir = os.environ.get("pdf_loc")
pdf_filenames = os.listdir(pdf_dir)

# define dataframe to hold bill summary
df_columns = {"statement_date": None,
              "service_from": None,
              "service_to": None,
              "wifi_service_charge": pd.Series(dtype='float'),
              "spectrum_internet_charge": pd.Series(dtype='float'),
              "one_time_charge": None,
              "promo_applied": pd.Series(dtype='bool'),
              "promo_discount": pd.Series(dtype='float'),
              "taxes": pd.Series(dtype='float'),
              "computed_total": pd.Series(dtype='float'),
              "printed_total": pd.Series(dtype='float'),
              "due_date": None}
df = pd.DataFrame(df_columns)

# loop over available bill pdfs
for filename in pdf_filenames:

    promo_flag = False  # tracks if bill has a promo discount applied
    one_time_charges_flag = False   # tracks if bill has a one time charge applied
    print(f"Reading file {filename}")

    reader = Reader(os.path.join(pdf_dir, filename))
    pg_2 = reader.pages[1]  # all relevant info exists in page 2
    pg_2_txt = pg_2.extract_text()

    ############################ SERVICE PERIOD #####################################
    service_date_regex = re.compile(r"service from (\d\d/\d\d/\d\d) through (\d\d/\d\d/\d\d)", re.IGNORECASE)
    mo = service_date_regex.search(pg_2_txt)
    service_start_date = datetime.strptime(mo.group(1), "%m/%d/%y").date()
    service_end_date = datetime.strptime(mo.group(2), "%m/%d/%y").date()

    ############################ WIFI SERVICE CHARGES #####################################
    wifi_service_regex = re.compile(r"wifi service (\d+.\d\d)", re.IGNORECASE)
    mo = wifi_service_regex.search(pg_2_txt)
    wifi_service_charge = float(mo.group(1))

    ############################ SPECTRUM INTERNET CHARGES #####################################
    spectrum_internet_regex = re.compile(r"spectrum internet (\d+.\d\d)", re.IGNORECASE)
    mo = spectrum_internet_regex.search(pg_2_txt)
    spectrum_internet_charge = float(mo.group(1))

    ############################ PROMOTIONAL DISCOUNT #####################################
    promotional_discount_regex = re.compile(r"promotional discount (-\d+.\d\d)", re.IGNORECASE)
    mo = promotional_discount_regex.search(pg_2_txt)
    if mo:
        promo_flag = True
        promotional_discount_value = float(mo.group(1))

        promo_discount_expiry_regex = re.compile(r"your promotional price will expire on (\d\d/\d\d/\d\d)", re.IGNORECASE)
        mo = promo_discount_expiry_regex.search(pg_2_txt)
        promo_discount_expiry_date = datetime.strptime(mo.group(1), "%m/%d/%y").date()

    ############################ ONE-TIME CHARGES #####################################
    one_time_charges_regex = re.compile(r"one-time charges total\s+\$(\d+.\d\d)", re.IGNORECASE)
    mo = one_time_charges_regex.search(pg_2_txt)
    if mo:
        one_time_charges_flag = True
        one_time_charges_total = float(mo.group(1))

    ############################ TOTAL TAXES #####################################
    taxes_regex = re.compile(r"taxes, fees and charges total \$(\d+.\d\d)", re.IGNORECASE)
    mo = taxes_regex.search(pg_2_txt)
    taxes_value = float(mo.group(1))

    ############################ BILL DUE DATE #####################################
    due_date_regex = re.compile(r"total due by\s+(\d\d/\d\d/\d\d)\s+\$(\d+.\d\d)", re.IGNORECASE)
    mo = due_date_regex.search(pg_2_txt)
    due_date = datetime.strptime(mo.group(1), "%m/%d/%y").date()

    printed_total = float(mo.group(2))

    ############################ BILL TOTAL #####################################
    computed_total = wifi_service_charge + spectrum_internet_charge + taxes_value
    if promo_flag:
        computed_total += promotional_discount_value
    if one_time_charges_flag:
        computed_total += one_time_charges_total

    temp = {"statement_date": service_start_date,
            "service_from": service_start_date,
            "service_to": service_end_date,
            "wifi_service_charge": wifi_service_charge,
            "spectrum_internet_charge": spectrum_internet_charge,
            "one_time_charge": one_time_charges_total if one_time_charges_flag else None,
            "promo_applied": promo_flag,
            "promo_discount": promotional_discount_value if promo_flag else None,
            "taxes": taxes_value,
            "computed_total": computed_total,
            "printed_total": printed_total,
            "due_date": due_date
            }
    temp_df = pd.DataFrame(temp, index=[0])

    df = pd.concat([df, temp_df], axis=0, ignore_index=True)    # append to bill summary holding dataframe


##################### CLEAN UP DATAFRAME ############################
df.sort_values(by="statement_date", ascending=True, inplace=True)   # sort by statement date
df.set_index(pd.Series(range(1, len(pdf_filenames)+1)), inplace=True)   # set index to start from 1
df.to_excel("output.xlsx")  # save as xlsx file
print(df)

