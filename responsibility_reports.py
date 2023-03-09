from selenium import webdriver
import urllib.request
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException
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

company_map = {}


def extract_name_from_link(redirected_pdf_url: str):
    if "/" in redirected_pdf_url:
        pdf_filename = redirected_pdf_url.split('/')[-1].replace(".pdf", "")
        if len(pdf_filename) > 0:
            return pdf_filename
    return None


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
        self.old_report_links = set()
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

        for i, (name, url,) in enumerate(self.company_urls.items()):
            try:
                f = open(f"company_info/{name.replace('/', '')}.json", mode="r", encoding="utf-8")
                f.close()
                continue
            except FileNotFoundError:
                pass

            old_report_links = set()
            self.driver.get(url)
            time.sleep(1)
            info = self.driver.find_element(By.CLASS_NAME, 'left_list_block').text.split("\n")
            try:
                ticker_name = info[1]
            except Exception:
                ticker_name = "NOTFOUND"
            try:
                exchange = info[3].replace("More", "").strip()
            except Exception:
                exchange = "NA"
            try:
                industry = info[5].replace("More", "").strip()
            except Exception as e:
                industry = "NA"
            try:
                sector = info[7].replace("More", "").strip()
            except Exception as e:
                sector = "NA"
            try:
                about_company = self.driver.find_element(By.CLASS_NAME, 'company_description')
            except Exception:
                about_company = "NA"
            try:
                num_employees = self.driver.find_element(By.CLASS_NAME, 'employees')
            except NoSuchElementException:
                num_employees = 0
            try:
                location = self.driver.find_element(By.CLASS_NAME, 'location')
            except NoSuchElementException:
                location = "NA"
            try:
                all_links = self.driver.find_elements(By.TAG_NAME, 'a')
            except Exception:
                all_links = []
            company_data = {
                'info': {
                    'company_name': name,
                    'company_url': url,
                    'ticker_name': ticker_name,
                    'exchange': exchange,
                    'industry': industry,
                    'sector': sector,
                    'about_company': about_company.text.strip() if about_company else "NA",
                    'num_employees': num_employees.text.strip() if type(num_employees) != int else "NA",
                    'location': location.text.strip() if type(location) != str else "NA"
                },
                'reports': []
            }
            company_map[name] = company_data
            for link in all_links:
                link_href = link.get_attribute('href')
                if link_href and "HostedData" in link_href:
                    old_report_links.add(link_href)

            for link in old_report_links:
                company_map[name]["reports"].append({
                    "pdf_url": link,
                    "report_name": extract_name_from_link(link)
                })
            print(company_data)
            try:
                most_recent_el = self.driver.find_element(By.CLASS_NAME, "most_recent_content_block")
                report_link_div = most_recent_el.find_element(By.CLASS_NAME, "view_btn")
                pdf_link = report_link_div.find_element(By.TAG_NAME, "a").get_attribute("href")
                redirected_pdf_url = requests.get(pdf_link).url
                # self.driver.get(pdf_link)
                # time.sleep()
                company_map[name]["reports"].append({
                    "pdf_url": redirected_pdf_url,
                    "report_name": extract_name_from_link(redirected_pdf_url)
                })
                # time.sleep(3)
            except Exception as e:
                print(f"Error: {e}")
            # print(company_map)
            with open(f"company_info/{name.replace('/', '')}.json", mode="w", encoding="utf-8") as f:
                json.dump(obj=company_map[name], fp=f, indent=2, default=str)

        # with open("responsibility_reports_data.json", mode="w", encoding="utf-8") as f:
        #     json.dump(obj=self.output, fp=f, indent=2, default=str)


if __name__ == '__main__':
    azn = ResponsibilityReport()
    azn.driver.quit()
