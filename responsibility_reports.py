from selenium import webdriver
import urllib.request
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from string import Template
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import time
from hashlib import md5
import logging
from selenium.common.exceptions import StaleElementReferenceException
from pprint import PrettyPrinter
import os

pp = PrettyPrinter(indent=2)

AZN_BASE_URL = "https://www.responsibilityreports.com/Companies?exch=2"

ENDPOINTS = {
    "certified": Template("certified-brands?page=$page"),
}
ENCODING_STANDARD = "utf-8"
BS_PARSER = "lxml"


class ResponsibilityReport:
    def __init__(self, **kwargs):
        path_loc = os.path.join(os.getcwd(), "reports")

        self.options = webdriver.ChromeOptions()
        chrome_prefs = {
            "download.prompt_for_download": False,
            "plugins.always_open_pdf_externally": True,
            "download.open_pdf_in_system_reader": False,
            "profile.default_content_settings.popups": 0,
            "download.default_directory": path_loc
        }
        self.options.add_experimental_option("prefs", chrome_prefs)
        is_headless = kwargs.get("headless", True)
        self.options.add_argument('--headless') if is_headless else None
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)
        self.current_page_url = AZN_BASE_URL
        self.company_urls = {}
        self.pdf_mapping = {}
        self.output = []

        self.driver.get(self.current_page_url)
        time.sleep(3)
        self.fetch_pdfs()

    def get_company_pg_urls(self):
        company_list = self.driver.find_elements(By.CLASS_NAME, "companyName")
        for comp in company_list:
            company_url = comp.find_element(By.TAG_NAME, "a")
            self.company_urls[company_url.text] = company_url.get_attribute("href")

        with open("name_url_mapping.json", mode="w", encoding="utf-8") as f:
            json.dump(obj=self.company_urls, fp=f, indent=2, default=str)

    def fetch_pdfs(self):
        with open('name_url_mapping.json') as f:
            self.company_urls = json.load(f)

        for i, (name, url) in enumerate(self.company_urls.items()):
            # if i == 6:
            #     break
            self.driver.get(url)
            time.sleep(2)
            print(name)
            try:
                most_recent_el = self.driver.find_element(By.CLASS_NAME, "most_recent_content_block")
                report_link_div = most_recent_el.find_element(By.CLASS_NAME, "view_btn")
                pdf_link = report_link_div.find_element(By.TAG_NAME, "a").get_attribute("href")
                redirected_pdf_url = requests.get(pdf_link).url
                # self.driver.get(pdf_link)
                # time.sleep()
                self.output.append({
                    "company_name": name,
                    "url": url,
                    "pdf_url": redirected_pdf_url
                })
                if "/" in redirected_pdf_url:
                    pdf_filename = redirected_pdf_url.split('/')[-1]
                    if len(pdf_filename) > 0:
                        self.pdf_mapping[pdf_filename] = name

                # time.sleep(3)
            except Exception as e:
                print(f"Error: {e}")

        with open("report_name_mapping.json", mode="w", encoding="utf-8") as f:
            json.dump(obj=self.pdf_mapping, fp=f, indent=2, default=str)

        with open("responsibility_reports_data.json", mode="w", encoding="utf-8") as f:
            json.dump(obj=self.output, fp=f, indent=2, default=str)


if __name__ == '__main__':
    # options = webdriver.ChromeOptions()
    # options.add_argument('--headless')
    # driver = webdriver.Chrome(ChromeDriverManager().install(), options=options)
    # test_company = CompanyPage("https://www.climateneutral.org/brand/22-degrees", driver)
    # test_company.extract_info()
    # test_company.driver.quit()
    azn = ResponsibilityReport()
    azn.driver.quit()
