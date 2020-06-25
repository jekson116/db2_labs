# -*- coding: utf-8 -*-
from scrapy.http.response import Response
import scrapy


class WalletSpider(scrapy.Spider):
    name = 'wallet'
    allowed_domains = ['www.wallet.ua']
    start_urls = ['https://wallet.ua/c/f-umbrellas-pol_girls-pol_boys/']

    def parse(self, response: Response):
        products = response.xpath("//div[contains(@class, 'prd-wrap')]")[:20]
        print(products)
        for product in products:
            yield {
                'img': 'https://wallet.ua/' + product.xpath(
                    ".//img[contains(@class, 'first-picture')]/@src").get(),
                'price': product.xpath(".//em[contains(@class, 'old crate')]/@data-rate").get(),
                'description': product.xpath(".//a[contains(@class, 'name')]/text()").get()
            }
