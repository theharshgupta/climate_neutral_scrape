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


class CompanyPage:
    def __init__(self, url_webpage, driver):
        self.driver = driver
        self.url_webpage = url_webpage
        self.company_webpage_url = None
        self.company_name = None
        self.industry = None
        self.story = None
        self.definition = None
        self.current_cert_yr = 0
        self.first_cert_yr = 0
        self.soup = None
        self.url_thumbnail = None
        self.meta_keywords = None  # Less accurate than self.tags
        self.movie = None
        self.html_doc = None
        self.story = ""
        self.scope1 = 0
        self.scope2 = 0
        self.scope3 = 0
        self.investment = 0
        self.total_emissions = 0
        self.emissions_offset = 0
        self.offset_sources = []
        self.tags = []
        self.completed_reductions = ""
        self.in_progress_reductions = ""
        self.curr_yr_reductions = ""

        self.options = webdriver.ChromeOptions()

    def extract_info(self):
        """
        Extracts the carbon info for each company.
        :return:
        """
        self.driver.get(self.url_webpage)
        # company_elements = self.driver.find_elements(By.CLASS_NAME, 'container')

        # Top info
        top_info_el = self.driver.find_element(By.CLASS_NAME, 'brand-meta')
        top_info = top_info_el.text.split("\n")
        self.company_name = top_info[1]
        self.industry = top_info[3]
        self.first_cert_yr = top_info[5]
        self.current_cert_yr = top_info[7]

        # Sustainability story
        story = self.driver.find_element(By.CLASS_NAME, 'brand_top-sustainability-story')
        self.story = story.text

        # Brand climate definition
        definition = self.driver.find_element(By.CLASS_NAME, 'brand_top-definition-wrapper')
        self.definition = definition.text

        # 01 Measure
        # Total emissions
        total_emissions_els = self.driver.find_elements(By.CLASS_NAME, 'total-cell')
        total_emissions_h4 = total_emissions_els[0].find_element(By.TAG_NAME, 'h4')
        emissions_offset_h4 = total_emissions_els[1].find_element(By.TAG_NAME, 'h4')
        self.total_emissions = total_emissions_h4.text
        self.emissions_offset = emissions_offset_h4.text

        # Scope 1, 2, 3
        scope123 = self.driver.find_elements(By.CLASS_NAME, 'brand-3col-block')
        for scope_el in scope123:
            # print(scope_el.text)

            if "Scope 1" in scope_el.text:
                self.scope1 = scope_el.text.split("\n")[-1]

            elif "Scope 2" in scope_el.text:
                self.scope2 = scope_el.text.split("\n")[-1]

            elif "Scope 3" in scope_el.text:
                self.scope3 = scope_el.text.split("\n")[-1]

            elif "Investment in Carbon Credits" in scope_el.text:
                self.investment = scope_el.text.split("\n")[-1]

        # 02 offset

        # Offset sources
        source_els = self.driver.find_elements(By.CLASS_NAME, 'w-dyn-item')
        carbon_offset_sources = []
        for source_el in source_els:
            source_text = source_el.text.strip()
            if len(source_text) > 3:
                carbon_offset_sources.append(source_text.split("?")[0].strip())
        self.offset_sources = carbon_offset_sources

        # 03 Reduce
        link = self.driver.find_element(By.CLASS_NAME, "reduce-content_completed-wrapper")
        link.click()
        reduction_els = self.driver.find_elements(By.CLASS_NAME, 'reduce-content_year-wrapper')
        for el in reduction_els:
            print(el.text)
            print("_____")
            if "Completed Reductions" in el.text:
                self.completed_reductions = el.text

            elif "In Progress Reductions" in el.text:
                self.in_progress_reductions = el.text

            elif "Current Year Reduction" in el.text:
                self.curr_yr_reductions = el.text

        return self.template()

    def template(self):
        return {
            "company": self.company_name,
            "webpage": self.url_webpage,
            "industry": self.industry,
            "first_certified_year": self.first_cert_yr,
            "current_certified_year": self.current_cert_yr,
            "story": self.story,
            "definition": self.definition,
            "total_emissions": self.total_emissions,
            "scope3_emissions": self.scope3,
            "scope2_emissions": self.scope2,
            "scope1_emissions": self.scope1,
            "total_carbon_credit_investment": self.investment,
            "emissions_offset": self.emissions_offset,
            "completed_reductions": self.completed_reductions,
            "in_progress_reductions": self.in_progress_reductions,
            "current_year_reductions": self.curr_yr_reductions,
        }


class ClimateNeutral:
    def __init__(self, category, **kwargs):
        self.category = category
        self.endpoint = ENDPOINTS.get(self.category)
        self.companies = []
        self.companies_urls = []
        self.PAGE_RANGE = [1, 10]
        self.current_page_url = None
        self.current_page_num = None
        self.success_num = None

        self.output = []

        self.options = webdriver.ChromeOptions()
        is_headless = kwargs.get("headless", True)
        self.options.add_argument('--headless') if is_headless else None
        self.driver = webdriver.Chrome(ChromeDriverManager().install(), options=self.options)

        for page_num in range(self.PAGE_RANGE[0], self.PAGE_RANGE[1]):
            print(f"Page Number: {page_num}")
            self.current_page_num = page_num
            self.extract_page(page_num)

        for company_url in self.companies_urls:
            company = CompanyPage(company_url, self.driver)
            try:
                company_output = company.extract_info()
                self.output.append(company_output)
                print(company_output['company'])
            except Exception as e:
                print(e)

        pp.pprint(self.output)
        with open("data.json", mode="w", encoding="utf-8") as f:
            json.dump(obj=self.output, fp=f, indent=2, default=str)


    def template(self):
        return {
            "page_number": self.current_page_num,
            "timestamp": datetime.now(),
            "page_url": self.current_page_url,
            "category": self.category,
        }

    def extract_page(self, page_num: int):
        """
        Returns video links with the metadata.
        :param page_num:
        :return: Video links
        """
        self.current_page_url = AZN_BASE_URL + self.endpoint.substitute(page=page_num)
        self.driver.get(self.current_page_url)
        time.sleep(3)
        company_elements_box = self.driver.find_element(By.XPATH, '//*[@id="seamless-replace-new"]/div[2]/div[1]')
        company_elements = company_elements_box.find_elements(By.TAG_NAME, 'a')
        self.success_num = 0
        self.companies = []

        for company_element in company_elements:
            try:
                company_page_url = company_element.get_attribute('href')
                if "brand/" in company_page_url:
                    self.companies_urls.append(company_page_url)
                    print(company_page_url)
            except StaleElementReferenceException:
                continue

class ResponsibilityReport:
    def __init__(self, **kwargs):
        # set location using os.path.join or set it manually if needed...
        path_loc = os.path.join(os.getcwd(), "temp")

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
        self.driver.get(self.current_page_url)
        time.sleep(3)
        company_list = self.driver.find_elements(By.CLASS_NAME, "companyName")
        self.company_urls = {}
        for comp in company_list:
            company_url = comp.find_element(By.TAG_NAME, "a")
            self.company_urls[company_url.text] = company_url.get_attribute("href")

        for name, url in self.company_urls.items():
            self.driver.get(url)
            time.sleep(1)
            print(name)
            try:
                most_recent_el = self.driver.find_element(By.CLASS_NAME, "most_recent_content_block")
                report_link_div = most_recent_el.find_element(By.CLASS_NAME, "view_btn")
                pdf_link = report_link_div.find_element(By.TAG_NAME, "a").get_attribute("href")
                self.driver.get(pdf_link)
                time.sleep(5)
            except Exception as e:
                print("Error--------")

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
