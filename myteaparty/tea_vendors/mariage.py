import click
import datetime
import requests
import re

from bs4 import BeautifulSoup, UnicodeDammit

from ..commands import TeaVendorImporter
from ..teaparty import app
from ..utils import save_distant_file
from ..model import Tea, TeaType, TypeOfATea, TeaVendor, database

class MariageFreresImporter(TeaVendorImporter):

    BASE_URL = 'http://www.mariagefreres.com'
    BASE_FR = BASE_URL + '/FR'
    HOMEPAGE = BASE_FR + '/accueil.html'

    def __init__(self, session):
        super().__init__(session)

        self.links = []
        self.teas_links = []
        self.teas_ids = []
        self.raw_teas_links = []
        self.teas_by_id = {}

        self.failed = []

        mf_logo = save_distant_file('https://upload.wikimedia.org/wikipedia/commons/a/ad/Logo_seul.jpg')
        self.vendor, _ = TeaVendor.get_or_create(
            name='Mariage Frères',
            slug='mf',
            defaults={
                'description': 'Thé français depuis 1854',
                'link': self.BASE_URL,
                'logo': mf_logo
            }
        )

    def get_vendor(self):
        """
        Returns an instance of the TeaVendor for this vendor.
        This method is called multiple times; it's result should be cached.

        :return: TeaVendor
        """
        return self.vendor

    def _extract_tea_id_from_link(self, url):
        """
        Extracts the tea ID from an URL and returns a tuple containing the
        tea raw ID (like TC7001) and numeric ID (like 7001).
        """
        tea_id = url.split('/')[-1].split('.')[0].split('-')[-1].upper()
        tea_id_numeric = int(tea_id.strip('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        return (tea_id, tea_id_numeric)

    def prepare_references(self):
        """
        This is called first, before the references crawling.
        It should prepare the crawl (e.g. list pages to analyze) and
        return a number of steps used by the retrieve_references
        method below, for an optimized UI.

        :return: The number of steps of the retrieve_references method,
                 or None if nothing has been retrieved.
        """
        # We first try to retrieve tea pages references from the details pages
        # listed in the bottom of any page

        r = self.session.get(self.HOMEPAGE)
        if not r.ok:
            return None

        soup = BeautifulSoup(r.text, 'html.parser')
        categories = soup.find(id='bas_centre').find_all(id='bas_centre_rep')[2].find_all(class_='bas_lien')

        for category in categories:
            link = category.find('a')
            if link:
                link_href = link.get('href')
                if link_href:
                    self.links.append(link_href.replace('./', self.BASE_FR + '/'))

        for menu in [2, 3, 4, 5]:
            s_menu_anchor = soup.find(id='menu_' + str(menu))
            if s_menu_anchor:
                s_menu = s_menu_anchor.find(class_='s-menu_' + str(menu))
                if s_menu:
                    self.links.extend([l.get('href').replace('./', self.BASE_FR + '/') for l in s_menu.findAll('a')
                                       if l.get('href')])

        return len(self.links)

    def retrieve_references(self):
        """
        Retrieves the references. Yelds each time a step (defined in the previous
        method) is achieved (e.g. one page analyzed).
        """
        for link in self.links:
            r = self.session.get(link)
            if not r.ok:
                self.failed.append(link)
                yield
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            tea_links_here = soup.find_all('a', class_='Lien-Titre-Liste')
            for link in tea_links_here:
                link_href = link.get('href')
                if link_href:
                    link_href = link_href.replace('./', self.BASE_FR + '/')
                    if link_href not in self.raw_teas_links:
                        self.raw_teas_links.append(link_href)

            yield

    def analyze_references(self):
        """
        Analyses and if needed cleanup the references.

        :return: a tuple with the number of references found, and a list
                 of errored references (strings)
        """
        # We now want to cleanup the links list.
        # There are duplicates, links to non-tea items, etc.
        # Tea pages have an ID in the URL beginning with a T.
        # For duplicates, we try to use the one with ID “T<number>” if available, else the first found.
        # We first group the teas by ID (filtering non-tea items on the fly) and then use the better one

        for tea in self.raw_teas_links:
            tea_id, tea_id_numeric = self._extract_tea_id_from_link(tea)
            if not tea_id.startswith('T'):
                continue

            if tea_id_numeric not in self.teas_by_id:
                self.teas_by_id[tea_id_numeric] = {}

            self.teas_by_id[tea_id_numeric][tea_id] = tea

        for tea_numeric_id in self.teas_by_id:
            teas = self.teas_by_id[tea_numeric_id]
            best_id = None
            best_link = None

            if len(teas) == 1:
                best_id = next(iter(teas))
                best_link = teas[best_id]
            else:
                for tea_id, tea in teas.items():
                    if tea_id.strip('0123456789') == 'T':
                        best_id = tea_id
                        best_link = tea
                        break
                # No tea ID formatted T<number>
                if best_id is None:
                    best_id = next(iter(teas))
                    best_link = teas[best_id]

            self.teas_ids.append(best_id.strip('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
            self.teas_links.append(best_link)

        return len(self.teas_ids), self.failed

    def get_retrieved_internal_ids(self):
        """
        Returns the retrieved teas internal IDs from the vendor (the
        one returned as vendor_internal_id in crawl_teas).
        This is used to ckeck for deleted teas and mark them as such.

        This method is called after analyze_references.

        :return: a list containing the retrieved teas internal IDs.
        """
        return self.teas_ids

    def crawl_teas(self):
        """
        Crawl the teas themselves. Yelds for each tea retrieved a tuple with a dict
        containing the keys in the Tea model, and a list with the tags of this tea
        (instances of the TypeOfATea, see self.get_tea_types()).
        """
        self.failed = []

        tea_types = self.get_tea_types()
        re_remove_non_numbers = re.compile('[^0-9.]')

        for tea_link in self.teas_links:
            tea_id, tea_id_numeric = self._extract_tea_id_from_link(tea_link)
            try:
                r = self.session.get(tea_link)
                r.raise_for_status()
            except Exception:
                self.failed.append(tea_link)
                continue

            soup = BeautifulSoup(r.text, 'html.parser')

            # Retrives basic infos (name, descriptions...)

            name = (soup.find('h1').get_text()
                                   .replace('®', '').replace('©', '')
                                   .replace('™', '').strip())

            description = soup.find('h2').get_text().strip()

            long_description = None

            long_description_element = soup.find(id='fiche_desc')
            if long_description_element:
                long_description = (UnicodeDammit(
                    long_description_element.encode_contents())
                    .unicode_markup.strip().replace('</br>', '')
                    .strip('<br/>').strip())

            # Retrives tips

            tips_raw = None
            tips_mass = None
            tips_volume = None
            tips_temperature = None
            tips_duration = None

            tips_block = soup.find(id='fiche_conseil_prepa')

            if tips_block:
                tips_raw = (tips_block.get_text()
                            .replace('CONSEILS DE PRÉPARATION :', '')
                            .strip())

                # We try to extract raw data.
                # Usual format: "2,5 g / 20 cl - 95°C - 5 min"
                # Conversion of '/' to '-' to cut the string, and
                # ',' to '.', to parse float numbers.
                tips_parts = (tips_raw.replace('/', '-')
                                      .replace(',', '.')
                                      .lower()
                                      .split(' - '))

                for tips_part in tips_parts:
                    tip_numeric = float(re_remove_non_numbers.sub('', tips_part))
                    if 'cl' in tips_part:
                        tips_volume = int(tip_numeric)
                    elif 'c' in tips_part:
                        tips_temperature = int(tip_numeric)
                    elif 'g' in tips_part:
                        tips_mass = int(tip_numeric * 1000)
                    elif 'min' in tips_part:
                        tips_duration = int(tip_numeric * 60)
            else:
                # Maybe another tips format found on some specific pages
                tips_block = soup.find(id='fiche_suggestion')
                if tips_block:
                    tips_raw = tips_block.get_text().replace('CONSEILS DE PRÉPARATION :', '').strip()

            # Retrives illustration

            image = None

            image_block = soup.find(id='A9', class_='valignmiddle')
            if image_block:
                image_tag = image_block.find('img')
                if image_tag and image_tag.get('src'):
                    image = save_distant_file(self.BASE_FR + '/' + image_tag.get('src'))

            # Retrives price

            price = None
            price_unit = None

            price_block = soup.find(id='fiche_ref_div')
            # Raw format of this block: "Ref : T8201&nbsp;&nbsp;-&nbsp;&nbsp;Prix : 8€ / 100g"
            if price_block:
                price_raw = price_block.get_text().replace('&nbsp;', '').split('-')
                if len(price_raw) >= 2:
                    price_raw = price_raw[1].strip().split(':')
                    price_raw = price_raw[1] if len(price_raw) >= 2 else price_raw[0]
                    if '/' in price_raw:
                        price_raw = price_raw.split('/')
                        price = price_raw[0].strip()
                        price_unit = price_raw[1].strip()
                    else:
                        price = price_raw.strip()
                        price_unit = 'boîte'

            if price:
                price = float(re_remove_non_numbers.sub('', price))

            # Retrives tea types

            tea_tags = [tag.get_text().strip('#').strip().lower() for tag in soup.select('#A11 a.fiche_ref_lien')]
            lower_description = description.lower()
            types = []
            for tea_type, keywords in tea_types:
                keywords_lower = [w.lower() for w in keywords]
                if tea_type not in types and (any(keyword in tea_tags for keyword in keywords_lower) or
                                              any(keyword in lower_description for keyword in keywords_lower)):
                    types.append(tea_type)

            # Returns the thing

            data = {
                'name': name,
                'vendor': self.vendor,
                'vendor_internal_id': tea_id_numeric,
                'description': description,
                'long_description': long_description,
                'tips_raw': tips_raw,
                'tips_temperature': tips_temperature,
                'tips_mass': tips_mass,
                'tips_volume': tips_volume,
                'tips_duration': tips_duration,
                'illustration': image,
                'price': price,
                'price_unit': price_unit,
                'link': tea_link
            }

            yield data, types

    def get_crawl_errors(self):
        """
        Returns a list of crawling errors (e.g. URL not crawled because
        of network error or 404).

        :return: List of errors.
        """
        return self.failed

Importer = MariageFreresImporter
