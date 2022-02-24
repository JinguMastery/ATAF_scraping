# -*- coding: utf-8 -*-
import os
import datetime as dt
import base64
import logging
import csv
import scrapy
from scrapy_splash.request import SplashRequest
from scrapy.selector import Selector
from ketl_scraping.spiders import MAX_SPLASH_TIMEOUT
from ketl_scraping.spiders.base_spiders.base_decision_spider import DecisionSpider
from ..settings import SPLASH_URL


SPLASH_CLEAN_GARBAGE_URL = f"{SPLASH_URL}/_gc"
PAGE_LOADER_SCRIPT = "./ketl_scraping/lua_scripts/ataf_page_loader.lua"
PAGE_TURNER_SCRIPT = "./ketl_scraping/lua_scripts/ataf_page_turner.lua"
COURT_MAPPING = {
    1: "Cour I (infrastructure, environnement, redevances, personnel)",
    2: "Cour II (économie, concurrence, formation)",
    3: "Cour III (assurances sociales, santé)",
    4: "Cour IV (droit d'asile)",
    5: "Cour V (droit d'asile)",
    6: "Cour VI (droit des étrangers, droit de cité)",
}


class JurisSpider(DecisionSpider, scrapy.Spider):
    name = "ataf_research"
    allowed_domains = ["jurispub.admin.ch"]
    base_url = "https://jurispub.admin.ch/publiws/?lang=fr"

    download_folder = "Ataf courts"
    sql_file_name = "ataf_courts.sqlite3"

    sql_fields = [
        ("Canton", "text"),  # important
        ("Jurisdiction", "text"),  # important
        ("Summary", "text"),
        ("Case reference", "text"),  # important
        ("Publication date", "integer"),  # important
        ("ATF references", "text"),
        ("ATAF references", "text"),
        ("ATAF decisions", "text"),
        ("Other decisions", "text"),
        ("Decision date", "integer"),  # important
        ("year", "integer"),  # important
        ("Url", "text"),
        ("PDF url", "text"),  # important
        ("Federal Laws and provisions", "text"),
        ("Official collection", "text"),
        ("Federal sheet", "text"),
        ("File name", "text"),  # important
        ("Descriptors", "text"),
        ("Language", "text"),
        ("Domain", "text"),
        ("Regeste", "text"),
    ]

    column_for_compare_new_data = "Case reference"

    date_fields_indexes = [4, 9]
    array_fields_indexes = [5, 6, 7, 13, 14, 15, 17]

    if not os.path.exists(PAGE_LOADER_SCRIPT) or not os.path.exists(PAGE_TURNER_SCRIPT):
        raise Exception("Lua script could not be loaded")
    with open(PAGE_LOADER_SCRIPT) as lua_script:
        lua_script_load_page = lua_script.read()
    with open(PAGE_TURNER_SCRIPT) as lua_script:
        lua_script_turn_page = lua_script.read()

    def __init__(self, *args, **kwargs):
        self.current_page = 0
        self.last_page = None
        self.start_year = 2015
        super().__init__(*args, **kwargs)
        open("./ketl_scraping/test_decision.csv", "w").close()
        for img in os.listdir("./ketl_scraping/images"):
            os.remove("./ketl_scraping/images/" + img)
        for html in os.listdir("./ketl_scraping/html_files"):
            os.remove("./ketl_scraping/html_files/" + html)
        for csv_file in os.listdir("./ketl_scraping/csv_files"):
            os.remove("./ketl_scraping/csv_files/" + csv_file)

    def start_requests(self):
        for court_num in COURT_MAPPING:
            for year in range(self.start_year, 2014, -1):
                year_ranges = []
                for month in range(1, 13):
                    if month == 12:
                        firstDay_nextMonth = dt.date(year + 1, 1, 1)
                    else:
                        firstDay_nextMonth = dt.date(year, month + 1, 1)
                    lastDay_month = firstDay_nextMonth - dt.timedelta(days=1)
                    year_ranges.append([f"01.{month}.{year}", lastDay_month.strftime("%d.%m.%Y")])
                for date_range in year_ranges:
                    yield SplashRequest(
                        self.base_url,
                        self.parse_search_page,
                        endpoint="execute",
                        args={
                            "lua_source": self.lua_script_load_page,
                            "dates": date_range,
                            "court": court_num,
                            "timeout": MAX_SPLASH_TIMEOUT,
                            "gc_url": SPLASH_CLEAN_GARBAGE_URL,
                        },
                        dont_filter=True,
                    )

    def parse_decisions(self, response):
        decisions = []
        html_data = {}
        logging.debug(list(response.data["decisions"]))
        """
        for img_ind in response.data["decision_images"]:
            with open("./ketl_scraping/images/decision" + img_ind + ".png", "wb") as image:
                img_data = base64.b64decode(response.data["decision_images"][img_ind])
                image.write(img_data)"""

        month_start_ind = response.data["date_range"].index(".") + 1
        year_start_ind = response.data["date_range"].index(".", month_start_ind) + 1
        year_end_ind = response.data["date_range"].index(",")
        month_num = response.data["date_range"][month_start_ind : year_start_ind - 1]
        year = response.data["date_range"][year_start_ind:year_end_ind]
        lang = response.data["language"]

        for decision_ind in response.data["decisions"]:
            current_decision = {}
            laws_dict = {}
            full_page = Selector(text=response.data["decisions"][decision_ind])
            html_data[decision_ind] = full_page.css("div.icePnlGrp#j_id8\\:j_id12").get()

            descriptors = full_page.css("span.iceOutTxt[id^=j_id8\\:j_id49]::text").getall()
            law_names = full_page.css(
                "span.iceOutTxt[id^=j_id8\\:j_id58][id$=j_id62]::text"
            ).getall()
            for i in range(len(law_names)):
                law_pdf_links = full_page.css(
                    "a.iceOutLnk[id^=j_id8\\:j_id58\\:" + str(i) + "\\:][id$=j_id66]::attr(href)"
                ).getall()
                law_articles = full_page.css(
                    "a.iceOutLnk[id^=j_id8\\:j_id58\\:" + str(i) + "\\:][id$=j_id66] > span::text"
                ).getall()
                laws_dict[law_names[i]] = [
                    (law_articles[j], law_pdf_links[j]) for j in range(len(law_pdf_links))
                ]

            official_links = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id72][id$=j_id74]::attr(href)"
            ).getall()
            official_ref_nums = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id72][id$=j_id74] > span::text"
            ).getall()
            sheet_links = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id88][id$=j_id90]::attr(href)"
            ).getall()
            sheet_ref_nums = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id88][id$=j_id90] > span::text"
            ).getall()
            other_decisions_links = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id96][id$=j_id98]::attr(href)"
            ).getall()
            other_decisions_ref_nums = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id96][id$=j_id98] > span::text"
            ).getall()
            atf_links = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id104][id$=j_id106]::attr(href)"
            ).getall()
            atf_ref_nums = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id104][id$=j_id106] > span::text"
            ).getall()
            ataf_links = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id128][id$=j_id130]::attr(href)"
            ).getall()
            ataf_ref_nums = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id128][id$=j_id130] > span::text"
            ).getall()
            ataf_decisions_links = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id136][id$=j_id138]::attr(href)"
            ).getall()
            ataf_decision_ref_nums = full_page.css(
                "a.iceOutLnk[id^=j_id8\\:j_id136][id$=j_id138] > span::text"
            ).getall()

            current_decision["descriptors"] = descriptors
            current_decision["federal laws"] = laws_dict
            current_decision["official"] = [
                (official_ref_nums[i], official_links[i]) for i in range(len(official_ref_nums))
            ]
            current_decision["sheet"] = [
                (sheet_ref_nums[i], sheet_links[i]) for i in range(len(sheet_ref_nums))
            ]
            current_decision["other decisions"] = [
                (other_decisions_ref_nums[i], other_decisions_links[i])
                for i in range(len(other_decisions_links))
            ]
            current_decision["atf"] = [
                (atf_ref_nums[i], atf_links[i]) for i in range(len(atf_links))
            ]
            current_decision["ataf"] = [
                (ataf_ref_nums[i], ataf_links[i]) for i in range(len(ataf_links))
            ]
            current_decision["ataf decisions"] = [
                (ataf_decision_ref_nums[i], ataf_decisions_links[i])
                for i in range(len(ataf_decisions_links))
            ]

            decisions.append(current_decision)
            case_reference = response.meta["case_references"][decision_ind - 1]

            scraped_data = [
                "ALL",
                COURT_MAPPING[response.data["court_num"]],
                None,
                case_reference,
                None,
                current_decision["atf"],
                current_decision["ataf"],
                current_decision["ataf decisions"],
                current_decision["other_decisions"],
                response.meta["decision_dates"][decision_ind - 1],
                year,
                None,
                response.meta["pdf_links"][decision_ind - 1],  # pdf url
                current_decision["federal laws"],
                current_decision["official"],
                current_decision["sheet"],
                case_reference + ".csv",
                current_decision["descriptors"],
                lang,
                response.meta["domains"][decision_ind - 1],
                response.meta["regestes"][decision_ind - 1],
            ]

            (
                scraped_data_for_pipeline,
                scraped_data_for_sqlite,
            ) = self.convert_scraped_data_for_pipeline_and_sqlite(scraped_data, already_array=True)
            additional_info_to_doc = self.generate_info_for_pipeline(scraped_data_for_pipeline)

            item = self.generate_item(
                scraped_data_for_sqlite,
                additional_info_to_doc,
                html_page=html_data[decision_ind],
            )

            download_full_path = os.path.join(self.download_path, case_reference + ".html")

            item["file_urls"] = [self.base_url]
            item["file_path"] = [download_full_path]
            yield item

        assert len(decisions) == len(response.data["decisions"])
        assert len(html_data) == len(response.data["decisions"])

        with open(f"./ketl_scraping/html_files/run_{month_num}_{year}_{lang}.html", "a") as file:
            for html_ind in html_data:
                file.write(html_data[html_ind] + "\n\n")
        with open(f"./ketl_scraping/csv_files/run_{month_num}_{year}_{lang}.csv", "a") as file:
            writer = csv.DictWriter(
                file,
                [
                    "descriptors",
                    "federal laws",
                    "official",
                    "sheet",
                    "other decisions",
                    "atf",
                    "ataf",
                    "ataf decisions",
                ],
            )
            writer.writerows(decisions)

    def parse_search_page(self, response):
        if not response.data:
            logging.debug("No results !")
            return

        logging.debug(list(response.data["htmls"]))
        logging.debug("num_pages = " + str(response.data["num_pages"]))
        logging.debug("num_htmls = " + str(len(response.data["htmls"])))
        """
        for img_ind in response.data["images"]:
            with open("./ketl_scraping/images/test" + img_ind + ".png", "wb") as image:
                img_data = base64.b64decode(response.data["images"][img_ind])
                image.write(img_data)"""

        for html_ind in response.data["htmls"]:
            full_page = Selector(text=response.data["htmls"][html_ind])
            n_decisions = len(full_page.css("tr[class^=iceDatTblRow]").getall())
            ref_num_list = full_page.css("a.iceCmdLnk[id$=j_id36]::text").getall()
            date_list = full_page.css("span.iceOutTxt[id$=j_id44]::text").getall()
            domain_list = full_page.css("span.iceOutTxt[id$=j_id50]::text").getall()
            regeste_list = full_page.css("span.iceOutTxt[id$=j_id58]::text").getall()
            pdf_link_list = full_page.css("a.iceOutLnk[id$=j_id37]::attr(href)").getall()

            month_num = response.data["date_range"][0][3:5].replace(".", "")
            logging.debug(
                "parsing page with " + str(n_decisions) + " decisions on month : " + month_num
            )
            assert len(ref_num_list) == n_decisions
            assert len(ref_num_list) == len(date_list)
            assert len(ref_num_list) == len(domain_list)
            assert len(ref_num_list) == len(pdf_link_list)
            if len(ref_num_list) != len(regeste_list):
                logging.error(COURT_MAPPING[response.data["court_num"]] + "\n")
                logging.error(response.data["date_range"][0] + "\n")

            with open("./ketl_scraping/test_decision.csv", "a") as file:
                for i in range(len(ref_num_list)):
                    decision_infos = (
                        ref_num_list[i]
                        + ", "
                        + date_list[i]
                        + ", "
                        + COURT_MAPPING[response.data["court_num"]]
                        + ", "
                        + domain_list[i]
                        + ", "
                    )
                    ataf_str = full_page.css(
                        "a.iceCmdLnk#form\\:resultTable\\:" + str(i) + "\\:j_id53::text"
                    ).get()
                    if ataf_str:
                        decision_infos += ataf_str + ", "
                    if len(ref_num_list) != len(regeste_list):
                        regeste_str = full_page.css(
                            "span.iceOutTxt#form\\:resultTable\\:" + str(i) + "\\:j_id58::text"
                        ).get()
                        if regeste_str:
                            decision_infos += regeste_str
                    else:
                        decision_infos += regeste_list[i]
                    decision_infos += " - " + pdf_link_list[i]
                    file.write(decision_infos + "\n")

            yield SplashRequest(
                self.base_url,
                self.parse_decisions,
                endpoint="execute",
                args={
                    "lua_source": self.lua_script_turn_page,
                    "dates": response.data["date_range"],
                    "court": response.data["court_num"],
                    "timeout": MAX_SPLASH_TIMEOUT,
                    "gc_url": SPLASH_CLEAN_GARBAGE_URL,
                    "lang": "FR",
                    "page": html_ind,
                },
                meta={
                    "case_references": ref_num_list,
                    "decision_dates": date_list,
                    "pdf_links": pdf_link_list,
                    "domains": domain_list,
                    "regestes": regeste_list,
                },
                dont_filter=True,
            )
