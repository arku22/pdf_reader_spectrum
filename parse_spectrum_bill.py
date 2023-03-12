import pandas as pd
import os
from PyPDF2 import PdfReader as Reader
from datetime import datetime
import re
from dotenv import load_dotenv


# load env variables
load_dotenv()


class ParseSpectrumBill:
    """
    Parse available spectrum bills (pdf files) in /assets/ and return a prepared monthly summary
    """

    def __init__(self):

        self.pdf_dir = os.environ.get("pdf_loc")
        self.pdf_filenames = os.listdir(self.pdf_dir)
        self.promo_flag = False
        self.one_time_charges_flag = False

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

        self.df = pd.DataFrame(df_columns)

    @staticmethod
    def get_service_period(pg_txt: str) -> tuple[datetime.date, datetime.date]:
        """
        extract bill service start and end date
        :param pg_txt: str String extracted from pdf file
        :return: tuple (start_date, end_date)
        """
        service_date_regex = re.compile(r"service from (\d\d/\d\d/\d\d) through (\d\d/\d\d/\d\d)", re.IGNORECASE)
        mo = service_date_regex.search(pg_txt)
        service_start_dt = datetime.strptime(mo.group(1), "%m/%d/%y").date()
        service_end_dt = datetime.strptime(mo.group(2), "%m/%d/%y").date()

        return service_start_dt, service_end_dt

    @staticmethod
    def get_wifi_charges(pg_txt: str) -> float:
        """
        extract wifi charges
        :param pg_txt: str String extracted from pdf file
        :return: float wifi charges
        """
        wifi_service_regex = re.compile(r"wifi service (\d+.\d\d)", re.IGNORECASE)
        mo = wifi_service_regex.search(pg_txt)
        wifi_service_chrge = float(mo.group(1))
        return wifi_service_chrge

    @staticmethod
    def get_spectrum_internet_charge(pg_txt: str) -> float:
        """
        extract spectrum internet charges
        :param pg_txt: str String extracted from pdf file
        :return: float spectrum internet charges
        """
        spectrum_internet_regex = re.compile(r"spectrum internet (\d+.\d\d)", re.IGNORECASE)
        mo = spectrum_internet_regex.search(pg_txt)
        spectrum_internet_chrge = float(mo.group(1))
        return spectrum_internet_chrge

    @staticmethod
    def get_taxes(pg_txt: str) -> float:
        """
        extract total taxes from bill
        :param pg_txt: str String extracted from pdf file
        :return: float tax charges
        """
        taxes_regex = re.compile(r"taxes, fees and charges total \$(\d+.\d\d)", re.IGNORECASE)
        mo = taxes_regex.search(pg_txt)
        taxes_value = float(mo.group(1))

        return taxes_value

    @staticmethod
    def get_total_dues(pg_txt: str) -> tuple[float, datetime.date]:
        """
        extract amount of printed dues and due date
        :param pg_txt: str String extracted from pdf file
        :return: tuple (printed_dues, due_date)
        """
        due_date_regex = re.compile(r"total due by\s+(\d\d/\d\d/\d\d)\s+\$(\d+.\d\d)", re.IGNORECASE)
        mo = due_date_regex.search(pg_txt)
        due_date = datetime.strptime(mo.group(1), "%m/%d/%y").date()

        printed_total = float(mo.group(2))

        return printed_total, due_date

    def get_promotional_discount(self, pg_txt: str) -> tuple[float, datetime.date] | None:
        """
        check and return any promotional discounts and validity
        :param pg_txt: str String extracted from pdf file
        :return: tuple|None (promo_discount_value, discount_expiry_date) or None
        """
        promotional_discount_regex = re.compile(r"promotional discount (-\d+.\d\d)", re.IGNORECASE)
        mo = promotional_discount_regex.search(pg_txt)
        if mo:
            self.promo_flag = True
            promotional_discount_value = float(mo.group(1))

            promo_discount_expiry_regex = re.compile(r"your promotional price will expire on (\d\d/\d\d/\d\d)",
                                                     re.IGNORECASE)
            mo = promo_discount_expiry_regex.search(pg_txt)
            promo_discount_expiry_date = datetime.strptime(mo.group(1), "%m/%d/%y").date()

            return promotional_discount_value, promo_discount_expiry_date

        return None

    def get_one_time_charges(self, pg_txt: str) -> float | None:
        """
        check and return any one time charges
        :param pg_txt: str String extracted from pdf file
        :return: float|None : one_time_charge_value or None
        """
        one_time_charges_regex = re.compile(r"one-time charges total\s+\$(\d+.\d\d)", re.IGNORECASE)
        mo = one_time_charges_regex.search(pg_txt)
        if mo:
            self.one_time_charges_flag = True
            one_time_charges_total = float(mo.group(1))

            return one_time_charges_total

        return None

    def get_computed_bill_total(self,
                                wifi_service_charge: float,
                                spectrum_internet_charge: float,
                                taxes: float,
                                promotional_discount_value: float = 0.0,
                                one_time_charges_total: float = 0.0
                                ) -> float:
        """
        compute and return totals using extracted values
        :param wifi_service_charge: float
        :param spectrum_internet_charge: float
        :param taxes: float
        :param promotional_discount_value: float
        :param one_time_charges_total: float
        :return: float
        """
        computed_total = wifi_service_charge + spectrum_internet_charge + taxes
        if self.promo_flag:
            computed_total += promotional_discount_value
        if self.one_time_charges_flag:
            computed_total += one_time_charges_total

        return computed_total

    def prepare_bill_summary(self):
        """
        Parse all available billing statements in /assets/ , prepare monthly billing summary and return summary
        :return: pd.DataFrame monthly billing summary
        """

        # loop over available bill pdfs
        for filename in self.pdf_filenames:

            self.promo_flag = False  # tracks if bill has a promo discount applied
            self.one_time_charges_flag = False  # tracks if bill has a one time charge applied
            print(f"Reading file {filename}")

            reader = Reader(os.path.join(self.pdf_dir, filename))
            pg_2 = reader.pages[1]  # all relevant info exists in page 2
            pg_2_txt = pg_2.extract_text()

            # -------------------------- SERVICE PERIOD --------------------------
            service_start_date, service_end_date = self.get_service_period(pg_2_txt)

            # -------------------------- WIFI SERVICE CHARGES --------------------------
            wifi_service_charge = self.get_wifi_charges(pg_2_txt)

            # -------------------------- SPECTRUM INTERNET CHARGES --------------------------
            spectrum_internet_charge = self.get_spectrum_internet_charge(pg_2_txt)

            # -------------------------- PROMOTIONAL DISCOUNT --------------------------
            promotional_discount_value, promo_discount_expiry_date = self.get_promotional_discount(pg_2_txt)

            # -------------------------- ONE-TIME CHARGES --------------------------
            one_time_charges_total = self.get_one_time_charges(pg_2_txt)

            # -------------------------- TOTAL TAXES --------------------------
            taxes_value = self.get_taxes(pg_2_txt)

            # -------------------------- BILL DUES --------------------------
            printed_total, due_date = self.get_total_dues(pg_2_txt)

            # -------------------------- COMPUTED TOTAL --------------------------
            computed_total = self.get_computed_bill_total(wifi_service_charge=wifi_service_charge,
                                                          spectrum_internet_charge=spectrum_internet_charge,
                                                          taxes=taxes_value,
                                                          promotional_discount_value=promotional_discount_value,
                                                          one_time_charges_total=one_time_charges_total
                                                          )

            # prep dataframe to append to summary dataframe
            temp = {"statement_date": service_start_date,
                    "service_from": service_start_date,
                    "service_to": service_end_date,
                    "wifi_service_charge": wifi_service_charge,
                    "spectrum_internet_charge": spectrum_internet_charge,
                    "one_time_charge": one_time_charges_total if self.one_time_charges_flag else None,
                    "promo_applied": self.promo_flag,
                    "promo_discount": promotional_discount_value if self.promo_flag else None,
                    "taxes": taxes_value,
                    "computed_total": computed_total,
                    "printed_total": printed_total,
                    "due_date": due_date
                    }
            temp_df = pd.DataFrame(temp, index=[0])

            self.df = pd.concat([self.df, temp_df], axis=0, ignore_index=True)  # append to summary dataframe

        # ------------------------- CLEAN UP DATAFRAME -------------------------
        self.df.sort_values(by="statement_date", ascending=True, inplace=True)  # sort by statement date
        self.df.set_index(pd.Series(range(1, len(self.pdf_filenames) + 1)), inplace=True)  # set index to start from 1
        self.df.to_excel("output.xlsx")  # save as xlsx file

        print("\n\nSUMMARY PREPARED and saved at /output.xlsx!\n\n")

        return self.df
