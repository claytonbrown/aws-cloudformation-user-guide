import scrapy
from scrapy.linkextractors import LinkExtractor

class AwsiconsSpider(scrapy.Spider):
    name = 'awsicons'
    allowed_domains = ['aws.amazon.com']
    start_urls = ['https://aws.amazon.com/architecture/icons/']

    def parse(self, response):
        pass
