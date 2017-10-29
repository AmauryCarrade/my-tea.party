import math
import random
import re

from bs4 import BeautifulSoup, UnicodeDammit

from ..import_teas import TeaVendorImporter
from ...utils import save_distant_file
from ...model import TeaVendor


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

        newby_logo = save_distant_file('https://www.newbyteas.co.uk'
                                       '/skin/frontend/ultimo/default/images/newbylogo2017.png')
        self.vendor, _ = TeaVendor.get_or_create(
            name='Newby',
            slug='newby',
            defaults={
                'description': 'Luxury teas, tisanes & tea gifts',
                'link': self.HOME_URL,
                'twitter': 'NewbyTeas',
                'logo': newby_logo
            }
        )

        self.re_tip_place = re.compile(r'place ((?P<amount_silk>[a-zA-Z0-9]+) silken pyramid|(?P<amount_g>\d+) ?g per cup|(?P<amount_spoons>[a-zA-Z0-9]+) teaspoon ?(?:of tea)?(?:\((?:\d)+g\))?) (?:in|into) (?P<boil_type>water|boiled water|freshly boiled water|freshly, fully boiled water)')  # noqa
        self.re_tip_use_spoon = re.compile(r'use (?P<amount_spoons>[a-zA-Z0-9]+) tea(?:- )?spoons? (?:of tea)? per (?P<container>cup|(?:[0-9- ])+ ?(?:ml|Ml|ML))(?: \(approx\.? (?P<container_size>(?:[0-9- ])+ ?(?:ml|Ml|ML))\))?')  # noqa
        self.re_tip_use_g = re.compile(r'use (?P<amount_g>\d+) ?g of (?:matcha powder|tea) per (?P<container_size>(?:[0-9- ])+ ?(?:ml|Ml|ML)) of (?P<boiled>boiled)? ?water')  # noqa
        self.re_tip_use_water = re.compile(r'use (?:fresh, fully boiled|freshly boiled|freshly-boiled) water')

        self.re_tip_extract_temp = re.compile(r'(?:left to cool to|cooled to|at a temperature of|cooled at|until it reaches about) (?P<temperature>[0-9- ]+)(?: )*(?:c|C|degrees?)')  # noqa
        self.re_tip_extract_time = re.compile(r'(?:brew )?for (?P<duration>[a-zA-Z0-9- ]{1,}?) (?:minutes?|mins?)')

        self.re_remove_non_numbers = re.compile('[^0-9.]')
        self.re_remove_numbers = re.compile('[0-9.]')

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
                name = link_elem.get_text()
                if any([keyword in name for keyword in ['Tea Bags', 'Selection Box', 'Gift Selection', 'Gift Set']]):
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

            name_elem = product_elem.find(class_='product-name')
            if name_elem:
                name = product_elem.find(class_='product-name').get_text().strip()
            else:
                self.failed.append(link)
                yield None, []
                continue

            # no gift 4 u
            if 'Gift Box' in name or 'Advent Calendar' in name or 'Accessories' in name:
                yield None, []
                continue

            description = ''  # No description here...
            long_description = ''
            tea_tags = []

            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords:
                tea_tags = [v.strip().lower() for v in meta_keywords.attrs['content'].split(',')]

            # ...or is there one?
            if ' - ' in name:
                parts = name.split(' - ')
                name = ' - '.join(parts[1:]).strip()
                description = parts[0].strip()

            tips_raw = None
            tips_mass = None
            tips_volume = None
            tips_temperature = None
            tips_duration = None
            tips_extra = None
            tips_max_brews = 1

            long_description_elem = product_elem.find(class_='short-description')
            if long_description_elem:
                long_description = (UnicodeDammit(long_description_elem.encode_contents())
                    .unicode_markup.strip())

            # Extracts tips (ugh) and ingredients

            for row in product_elem.select('.box-collateral .box-additional table tr'):
                row_title = row.find('th').get_text().lower()
                if 'cup' in row_title:
                    tips_raw = row.find('td').get_text().strip()
                    tips_volume = 25
                    tips_mass = 2000
                    if 'http://' in tips_raw:
                        if any([tag in tea_tags for tag in ['white tea', 'green tea']]):
                            tips_temperature = 80
                            tips_duration = 3 * 60
                        else:
                            tips_temperature = 95
                            tips_duration = 4 * 60
                        if 'loose leaf tea' not in tea_tags:
                            tips_duration -= 1 * 60
                    elif tips_raw.lower() != 'n/a':
                        # We here have to parse the human-friendly help text to retrieve the tips
                        tips_raw_lower_phrases = [p.strip() for p in tips_raw.lower().replace(u'\u00B0', ' ')
                                                                                     .replace(u'\u2013', '-')
                                                                                     .split('.')]

                        def human_number_to_int(number):
                            '''
                            Converts a number or an interval of numbers to an int.
                            numbers can be in human format (“one”…).
                            If multiple numbers are detected, the average is returned.
                            '''
                            words = {
                                'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
                                'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12
                            }
                            numbers = [n.strip() for n in number.split('-')]
                            ints = []
                            for n in numbers:
                                if n in words:
                                    ints.append(words[n])
                                try:
                                    ints.append(int(n, 10))
                                except ValueError:
                                    pass
                            return float(sum(ints)) / float(len(ints))

                        for tip in tips_raw_lower_phrases:
                            match_place = self.re_tip_place.search(tip)
                            if match_place:
                                if match_place['amount_silk']:
                                    tips_mass = -human_number_to_int(match_place['amount_silk'])
                                elif match_place['amount_g']:
                                    tips_mass = human_number_to_int(match_place['amount_g']) * 1000
                                elif match_place['amount_spoons']:
                                    tips_mass = human_number_to_int(match_place['amount_spoons']) * 2000
                                if match_place['boil_type']:
                                    tips_temperature = 100 if 'fully' in match_place['boil_type'] else 95

                            match_place = self.re_tip_use_spoon.search(tip)
                            if match_place:
                                if match_place['amount_spoons']:
                                    tips_mass = human_number_to_int(match_place['amount_spoons']) * 2000
                                if match_place['container']:
                                    container_size = (match_place['container_size'] if match_place['container'] == 'cup'
                                                                                    and match_place['container_size']
                                                                                    else match_place['container'])
                                    if container_size:
                                        tips_volume_ml = human_number_to_int(container_size.lower()
                                                                                           .replace('ml', '')
                                                                                           .strip())
                                        tips_volume = int(tips_volume_ml / 10.0)

                            match_place = self.re_tip_use_g.search(tip)
                            if match_place:
                                if match_place['amount_g']:
                                    tips_mass = human_number_to_int(match_place['amount_g']) * 1000
                                if match_place['container_size']:
                                    tips_volume_ml = human_number_to_int(match_place['container_size'].lower()
                                                                                                      .replace('ml', '')
                                                                                                      .strip())
                                    tips_volume = int(tips_volume_ml / 10.0)
                                if match_place['boiled']:
                                    tips_temperature = 95

                            match_water = self.re_tip_use_water.search(tip)
                            if match_water:
                                tips_temperature = 100 if 'fully' in tip else 95

                            match_temp = self.re_tip_extract_temp.search(tip)
                            if match_temp and match_temp['temperature']:
                                tips_temperature = human_number_to_int(match_temp['temperature'])

                            match_time = self.re_tip_extract_time.search(tip)
                            if match_time:
                                tips_duration = math.ceil(human_number_to_int(match_time['duration'])) * 60

                            if 'a second brew can be enjoyed using the same leaf' in tip:
                                tips_max_brews = 2

                            if 'watch as the bulb blossoms' in tip or 'whisk well until the powder' in tip:
                                extra = tip.capitalize()
                                if tips_extra is not None:
                                    tips_extra += ' ' + extra
                                else:
                                    tips_extra = extra

                    else:
                        tips_volume = None
                        tips_mass = None
                        tips_raw = '(Pas de conseil disponible)'

                elif 'ingredient' in row_title:
                    ingredients_elem = row.find('td')
                    if ingredients_elem:
                        ingredients = ingredients_elem.get_text().strip()

                elif 'weight' in row_title:
                    try:
                        price_unit_elem = row.find('td')
                        if price_unit_elem:
                            price_unit = str(int(float(price_unit_elem.get_text().strip()))) + 'g'
                        else:
                            raise ValueError
                    except Exception:
                        price_unit = '100g'

            # Retrieves an unique ID

            try:
                tea_id_numeric = product_elem.find(class_='sku').find(class_='value').get_text().strip()
            except Exception:
                tea_id_numeric = str(random.randint(10000000, 99999999))

            if tea_id_numeric in self.teas_ids:
                tea_id_numeric += '-' + link.split('/')[-1]
            if tea_id_numeric in self.teas_ids:
                tea_id_numeric += str(random.randint(10000000, 99999999))

            self.teas_ids.append(tea_id_numeric)

            # Retrieves an image

            image = None
            image_elem = product_elem.find(class_='product-image')

            if image_elem:
                image_elem = image_elem.find('a', class_='product-image-gallery')
                if image_elem and image_elem.get('href'):
                    image = save_distant_file(image_elem.get('href'))

            # Retrieves the price

            price = None
            price_elem = product_elem.find(class_='price-box')

            if price_elem:
                price_elem = price_elem.find(class_='price')
                if price_elem:
                    price_raw = price_elem.get_text().strip()
                    try:
                        price = float(self.re_remove_non_numbers.sub('', price_raw).replace(',', '.'))
                    except Exception:
                        price = None

            # Determines the types

            types = self._retrieve_teas_types(*tea_tags, name, description, long_description)

            # Returns the thing

            data = {
                'name': name,
                'vendor': self.vendor,
                'vendor_internal_id': tea_id_numeric,
                'description': description,
                'long_description': long_description,
                'ingredients': ingredients,
                'tips_raw': tips_raw,
                'tips_temperature': tips_temperature,
                'tips_mass': tips_mass,
                'tips_volume': tips_volume,
                'tips_duration': tips_duration,
                'tips_extra': tips_extra,
                'tips_max_brews': tips_max_brews,
                'illustration': image,
                'price': price,
                'price_unit': price_unit,
                'link': link
            }

            yield data, types

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
