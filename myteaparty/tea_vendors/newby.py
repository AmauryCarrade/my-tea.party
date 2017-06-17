import click
import datetime
import requests
import re

from bs4 import BeautifulSoup, UnicodeDammit

from ..commands import TeaVendorImporter
from ..teaparty import app
from ..utils import save_distant_file
from ..model import Tea, TeaType, TypeOfATea, TeaVendor, database


class NewbyImporter(TeaVendorImporter):

    HOME_URL = 'https://www.newbyteas.com'
    SHOP_URL = 'https://www.newbyteas.co.uk'

    def __init__(self, session, retries=3):
        super().__init__(session, retries)

        self.links = []
        self.teas_links = []
        self.teas_ids = []
        self.raw_teas_links = []
        self.teas_by_id = {}

        self.failed = []

        newby_logo = save_distant_file('https://www.newbyteas.co.uk/skin/frontend/ultimo/default/images/newbylogo2017.png')
        self.vendor, _ = TeaVendor.get_or_create(
            name='Newby',
            slug='newby',
            defaults={
                'description': 'Luxury teas, tisanes & tea gifts',
                'link': self.HOME_URL,
                'logo': newby_logo
            }
        )

    def get_vendor(self):
        """
        Returns an instance of the TeaVendor for this vendor.
        This method is called multiple times; it's result should be cached.

        :return: TeaVendor
        """
        return self.vendor

    def prepare_references(self):
        """
        This is called first, before the references crawling.
        It should prepare the crawl (e.g. list pages to analyze) and
        return a number of steps used by the retrieve_references
        method below, for an optimized UI.

        :return: The number of steps of the retrieve_references method,
                 or None if nothing has been retrieved.
        """
        r = self._get(self.SHOP_URL)
        if not r:
            return None

        soup = BeautifulSoup(r.text, 'html.parser')
        self.links = [link.attrs['href'] for link in soup.select('#nav li > ul li a')
                                         if 'newby-accessories' not in link.attrs['href']
                                         and link.attrs['href'].strip('/') != self.SHOP_URL]
        return len(self.links)

    def retrieve_references(self):
        """
        Retrieves the references. Yields each time a step (defined in the previous
        method) is achieved (e.g. one page analyzed).
        """
        for link in self.links:
            r = self._get(link)
            if not r:
                self.failed.append(link)
                yield
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            for product in soup.select('.products-grid li.item'):
                link_elem = product.find('h2').find('a')
                title = link_elem.get_text()
                if any([keyword in title for keyword in ['Tea Bags', 'Selection Box', 'Gift Selection', 'Gift Set']]):
                    continue
                self.teas_links.append(link_elem.attrs['href'])

            yield

    def analyze_references(self):
        """
        Analyses and if needed cleanup the references.

        :return: a tuple with the number of references found, and a list
                 of errored references (strings)
        """
        return len(self.teas_links), self.failed

    def crawl_teas(self):
        """
        Crawl the teas themselves. Yields for each tea retrieved a tuple with a dict
        containing the keys in the Tea model, and a list with the tags of this tea
        (instances of the TypeOfATea, see self.get_tea_types()).
        """
        self.failed = []
        self.teas_ids = []
        titles = []

        for link in self.teas_links:
            r = self._get(link)
            if not r:
                self.failed.append(link)
                yield None, []
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            product_elem = soup.find(class_='product-view')
            if not product_elem:
                yield None, []
                continue

            title = product_elem.find(class_='product-name').get_text()
            description = ''  # No description here
            long_description = ''
            tea_tags = [v.strip().lower() for v in soup.find('meta', name='keywords').attrs['content'].split(',')]

            tips_raw = None
            tips_mass = None
            tips_volume = None
            tips_temperature = None
            tips_duration = None

            long_description_elem = product_elem.find(class_='short-description')
            if long_description_elem:
                long_description = (UnicodeDammit(long_description_elem.encode_contents())
                    .unicode_markup.strip().replace('</br>', '').strip('<br/>').strip())

            for row in product_elem.select('.box-collateral .box-additional table tr'):
                row_title = row.find('th').get_text().lower()
                if 'cup' in row_title:
                    tips_raw = row.find('td').get_text().strip()
                    tips_volume = 25
                    tips_mass = 2000
                    if 'http://' in tips_raw:
                        if any([tag in tea_tags for tag in ['white tea', 'green tea']]):
                            tips_temperature = 80
                            tips_duration = 3*60
                        else:
                            tips_temperature = 95
                            tips_duration = 4*60
                        if 'loose leaf tea' not in tea_tags:
                            tips_duration -= 1*60
                    else:
                        # We here have to parse the human-friendly help text to retrieve the tips
                        tips_raw_lower = (tips_raw.lower().replace(u'\u00B0', '°')
                                                          .replace(u'\u2013', '-')
                                                          .replace('degrees', 'C'))
                        if 'boiled water' in tips_raw_lower:
                            tips_temperature = 95


            yield None, []

    def get_crawl_errors(self):
        """
        Returns a list of crawling errors (e.g. URL not crawled because
        of network error or 404).

        :return: List of errors.
        """
        return self.failed

    def get_retrieved_internal_ids(self):
        """
        Returns the retrieved teas internal IDs from the vendor (the
        one returned as vendor_internal_id in crawl_teas).
        This is used to ckeck for deleted teas and mark them as such.

        :return: a list containing the retrieved teas internal IDs.
        """
        return self.teas_ids

Importer = NewbyImporter
