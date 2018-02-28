# -*- coding: utf-8 -*-
import scrapy
from esf.items import ScrapeItem,IndexItem,AgentItem
from scrapy.loader import ItemLoader
from scrapy.loader.processors import MapCompose,Join,TakeFirst
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from scrapy.utils.project import get_project_settings
from scrapy.http import Request
import sqlite3
import re
import socket
import datetime
from urllib.request import urljoin, urlparse
import random
import time
import logging
from bs4 import BeautifulSoup
import requests


class KunshanAllScrapeScripe(scrapy.spiders.CrawlSpider):
    start_urls = [ 'http://house.ks.js.cn/secondhand.asp']
    name = 'KunShanAllScrapeSpider'
    spc_reg = re.compile(r"\s+")

    rules = (Rule(LinkExtractor(restrict_xpaths='//div[@class="page"]')),
             Rule(LinkExtractor(restrict_xpaths='//ul[@id="xylist"]/li//a'), callback="parse_item")
             )

    def parse_item(self,response):
        # agency table
        l = ItemLoader(item=AgentItem(), response=response)
        l.default_output_processor = TakeFirst()
        l.add_xpath("name", '//div[@class="sthys3"]/text()', re=r"：(\w+)")
        l.add_xpath("telephone", '//div[@class="sttelct2 sttelct"]/text()',
                    MapCompose(lambda x: "".join(x.split())))
        l.item.setdefault("company", None)
        l.add_xpath("company", '//li[@class="st14 stb starial"]//text()')
        l.add_xpath("address", '//div[@class="xflilist"]/div[3]//text()',
                    re = r'：(\w+)')
        l.add_xpath("register_date", '//div[@class="jbfx"]/text()', re=r'登记日期：([\d/]+)')
        l.add_value("district", "昆山")
        l.add_xpath("subdistrict",'(//div[@class="xx_xq_l200"])[2]/text()', re='区域：(?:昆山)?(\\w+)')

        # housekeeping
        l.add_value("source", response.url)
        l.add_value("project", self.settings.get("BOT_NAME"))
        l.add_value("spider", self.name)
        l.add_value("server", socket.gethostname())
        l.add_value("date", datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        yield l.load_item()

        # properties table
        l = ItemLoader(item=ScrapeItem(), response=response)
        l.default_output_processor = TakeFirst()
        l.add_xpath('title', '//div[@class="xxview_title"]/text()')
        l.add_value("url", response.url)
        l.add_xpath("price", '//div[@class="xx_xq_l200"]/span[@class="st22 '
                             'sthuangs stb starial"]/text()')
        l.add_xpath("address",'//div[@class="wydzleft"]/text()', MapCompose(lambda x: x.strip()),
                    re=r'物业地址：([^\x01-\x1f]+)')
        l.add_value("district", "昆山")
        l.add_xpath("subdistrict", '(//div[@class="xx_xq_l200"])[2]/text()', re='区域：(?:昆山)?(\\w+)')
        l.add_xpath("agent_name", '//div[@class="sthys3"]/text()', re=r"：(\w+)")
        l.item.setdefault("agent_company", None)
        l.add_xpath("agent_company", '//li[@class="st14 stb starial"]//text()')
        l.add_xpath('agent_phone','//div[@class="sttelct2 sttelct"]/text()',
                    MapCompose(lambda x: "".join(x.split())))
        l.add_value('source_name', "昆山视窗")
        l.add_value("category", "secondhose")
        l.add_xpath("recent_activation", '//div[@class="fyfbtime"]/text()', re = '查看人次：(\\d+)')

        # housekeeping
        l.add_value("source", response.request.url)
        l.add_value("project", self.settings.get("BOT_NAME"))
        l.add_value("spider", self.name)
        l.add_value("server", socket.gethostname())
        l.add_value("date", datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
        yield l.load_item()

    def start_requests(self):
        if get_project_settings().get('REFRESH_URLS') != 0:
            self.logger.critical("refresh urls ....")
            with sqlite3.connect("data/esf_urls.db") as cnx:
                cursor = cnx.cursor()
                cursor.execute("select source from main.agencies where name is null and district ='昆山'")
                urls = [r[0] for r in cursor.fetchall()]
                cursor.execute("DELETE from main.agencies where name is null and district ='昆山'")
                cnx.commit()
            for url in urls:
                yield Request(url=url, callback=self.parse_item)
        else:
            for url in self.start_urls:
                yield Request(url=url)

    # def parse(self, response):
    #     self.logger.info("start parese url %s" %response.url)
    #     for div in response.xpath('//ul[@id="xylist"]/li[@class="listzwt"]'):
    #         l = ItemLoader(item=ScrapeItem(), selector=div)
    #         l.default_output_processor = TakeFirst()
    #         l.add_xpath("title",'./div[@class="xlist_1"]/a/text()', MapCompose(lambda x: self.spc_reg.sub("",x)), Join())
    #         l.add_xpath("url",'./div[@class="xlist_1"]/a/@href',
    #                     MapCompose(lambda x: urljoin(response.url, x )))
    #         l.add_xpath("price", '(./div[@class="xlist_3"])[3]/text()')
    #         l.add_xpath("address",'./div[@class="xlist_1"]/a/text()',
    #                     MapCompose(lambda x: self.spc_reg.sub("", x)),Join())
    #
    #         l.add_value("district", "昆山")
    #
    #         l.add_xpath("subdistrict",'./div[@class="xlist_2"]/text()')
    #
    #         # housekeeping
    #         l.add_value("source", response.url)
    #         l.add_value("project", self.settings.get("BOT_NAME"))
    #         l.add_value("spider", self.name)
    #         l.add_value("server", socket.gethostname())
    #         l.add_value("date", datetime.datetime.now().strftime("%Y%m%d%H%M%S"))
    #
    #         yield l.load_item()

    # def start_requests(self):
    #     self.cnx = sqlite3.connect(get_project_settings().get("STORE_DATABASE"))
    #     self.cursor = self.cnx.cursor()
    #     self.cursor.execute("SELECT DISTINCT url from properties where spider = '%s'" %self.name)
    #     fetched_urls = [url[0] for url in self.cursor.fetchall()]
    #     for url in self.start_urls:
    #         if url not in fetched_urls:
    #             yield Request(url)

    # def __del__(self):
    #     self.cursor.close()
    #     self.cnx.close()
