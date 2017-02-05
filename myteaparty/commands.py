import click
import datetime
import requests
import re
import titlecase

from bs4 import BeautifulSoup, UnicodeDammit
from slugify import slugify

from .teaparty import app
from .utils import save_distant_file
from .model import Tea, TeaType, TypeOfATea, TeaVendor, database


def get_crawling_session():
    """
    Returns a crawling session with user agent and other global options to
    use to crawl websites.

    :return: requests.Session
    """
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:52.0) '
                      'Gecko/20100101 Firefox/52.0 (compatible; '
                      'MyTeaPartyCrawler/0.1-experiment; '
                      '+https://amaury.carrade.eu/contact)'
    })

    return s


def get_tea_types():
    """
    Returns a list of tuples containing as first argument, the tea type
    instance, and as second, a list of names to be found in the pages
    to ckeck if the tea is this type.
    """
    def get_or_create(*args, **kwargs):
        return TeaType.get_or_create(*args, **kwargs)[0]

    return [
        (get_or_create(name='Thé noir', slug='noir', is_origin=False), ['Thé noir']),
        (get_or_create(name='Thé vert', slug='vert', is_origin=False), ['Thé vert']),
        (get_or_create(name='Thé blanc', slug='blanc', is_origin=False), ['Thé blanc']),
        (get_or_create(name='Thé mûr', slug='mur', is_origin=False), ['Thé mûr', 'Thé mur', 'Pu-erh', 'Puerh']),
        (get_or_create(name='Thé jaune', slug='jaune', is_origin=False), ['Thé jaune']),
        (get_or_create(name='Thé bleu', slug='bleu', is_origin=False), ['Thé bleu']),
        (get_or_create(name='Thé rouge', slug='rouge', is_origin=False), ['Thé rouge', 'Thé rouge sans théine',
                                                                          'sans théine']),
        (get_or_create(name='Thé fûmé', slug='fume', is_origin=False), ['Thé fûmé', 'Thé fumé']),
        (get_or_create(name='Thé au Jasmin', slug='jasmin', is_origin=False), ['Thé au jasmin', 'Jasmin']),
        (get_or_create(name='Infusion', slug='infusion', is_origin=False), ['Infusion', 'Infusion de fruits']),

        (get_or_create(name='Grand cru', slug='grand-cru', is_origin=False), ['Grand cru']),
        (get_or_create(name='Darjeeling', slug='darjeeling', is_origin=True), ['Darjeeling', 'Darjeeling de Printemps',
                                                                               'Darjeeling d\'Été']),
        (get_or_create(name='Assam', slug='assam', is_origin=True), ['Assam', 'Assam d\'Été']),
        (get_or_create(name='Ceylan', slug='ceylan', is_origin=True), ['Ceylan']),
        (get_or_create(name='Thé de Chine', slug='chine', is_origin=True), ['Thé de Chine', 'Chine']),
        (get_or_create(name='Thé du Japon', slug='japon', is_origin=True), ['Japon'])
    ]


@app.cli.group('import')
def import_group():
    pass


@import_group.command('mariage')
@click.option('--dry-run', is_flag=True, default=False)
def import_mariage_command(dry_run):
    click.echo('Starting import from Mariage Frères.')
    if dry_run:
        click.echo('Performing a dry run.')

    BASE_URL = 'http://www.mariagefreres.com'
    BASE_FR = BASE_URL + '/FR'
    HOMEPAGE = BASE_FR + '/accueil.html'

    def extract_tea_id_from_link(url):
        """Extracts the tea ID from an URL and returns a tuple containing the
        tea raw ID (like TC7001) and numeric ID (like 7001)."""
        tea_id = url.split('/')[-1].split('.')[0].split('-')[-1].upper()
        tea_id_numeric = int(tea_id.strip('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        return (tea_id, tea_id_numeric)

    titlecase.set_small_word_list(titlecase.SMALL + '|un|une|de|des|du|d|le|la|les|l|au|à|a|s')

    database.begin()

    mf_logo = save_distant_file('https://upload.wikimedia.org/wikipedia/commons/a/ad/Logo_seul.jpg')
    vendor, _ = TeaVendor.get_or_create(
        name='Mariage Frères',
        slug='mf',
        defaults={
            'description': 'Thé français depuis 1854',
            'link': BASE_URL,
            'logo': mf_logo
        }
    )

    s = get_crawling_session()

    used_slugs = [slug.slug for slug in Tea.select(Tea.slug).execute()]

    click.echo('\nRetrieving references...', nl=False)

    links = []
    teas_links = []
    teas_ids = []

    # We first try to retrieve tea pages references from the details pages
    # listed in the bottom of any page

    r = s.get(HOMEPAGE)
    if not r.ok:
        click.echo(' Failed (cannot retrieve homepage)')
        return

    soup = BeautifulSoup(r.text, 'html.parser')
    categories = soup.find(id='bas_centre').find_all(id='bas_centre_rep')[2].find_all(class_='bas_lien')

    for category in categories:
        link = category.find('a')
        if link:
            link_href = link.get('href')
            if link_href:
                links.append(link_href.replace('./', BASE_FR + '/'))

    for menu in [2, 3, 4, 5]:
        s_menu_anchor = soup.find(id='menu_' + str(menu))
        if s_menu_anchor:
            s_menu = s_menu_anchor.find(class_='s-menu_' + str(menu))
            if s_menu:
                links.extend([l.get('href').replace('./', BASE_FR + '/') for l in s_menu.findAll('a')
                              if l.get('href')])

    failed = []
    with click.progressbar(length=len(links) + 1, label='Retrieving references'.ljust(32)) as bar:
        raw_teas_links = []

        for link in links:
            r = s.get(link)
            if not r.ok:
                failed.append(link)
                continue

            soup = BeautifulSoup(r.text, 'html.parser')
            tea_links_here = soup.find_all('a', class_='Lien-Titre-Liste')
            for link in tea_links_here:
                link_href = link.get('href')
                if link_href:
                    link_href = link_href.replace('./', BASE_FR + '/')
                    if link_href not in raw_teas_links:
                        raw_teas_links.append(link_href)

            bar.update(1)

        # We now want to cleanup the links list.
        # There are duplicates, links to non-tea items, etc.
        # Tea pages have an ID in the URL beginning with a T.
        # For duplicates, we try to use the one with ID “T<number>” if available, else the first found.
        # We first group the teas by ID (filtering non-tea items on the fly) and then use the better one

        teas_by_id = {}

        for tea in raw_teas_links:
            tea_id, tea_id_numeric = extract_tea_id_from_link(tea)
            if not tea_id.startswith('T'):
                continue

            if tea_id_numeric not in teas_by_id:
                teas_by_id[tea_id_numeric] = {}

            teas_by_id[tea_id_numeric][tea_id] = tea

        for tea_numeric_id in teas_by_id:
            teas = teas_by_id[tea_numeric_id]
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

            teas_ids.append(best_id.strip('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
            teas_links.append(best_link)

        bar.update(1)

    click.echo('{} references found. {} fails.'.format(len(teas_links), len(failed)))
    if failed:
        click.echo('The following URLs errored:')
        for fail in failed:
            click.echo('→ {}'.format(fail))

    click.echo()

    click.echo('Flagging entries in database but not retrieved as deleted...', nl=False)
    Tea.update(deleted=datetime.datetime.now()).where((Tea.vendor_internal_id.not_in(teas_ids)) &
                                                      (Tea.vendor == vendor)).execute()
    click.echo(' Done.')
    click.echo()

    tea_types = get_tea_types()

    teas_to_insert = []
    types_to_insert = {}
    re_remove_non_numbers = re.compile('[^0-9.]')
    failed = []
    with click.progressbar(teas_links, label='Retrieving tea informations'.ljust(32)) as bar:
        for tea_link in bar:
            tea_id, tea_id_numeric = extract_tea_id_from_link(tea_link)
            try:
                r = s.get(tea_link)
                r.raise_for_status()
            except Exception:
                failed.append(tea_link)
                continue

            soup = BeautifulSoup(r.text, 'html.parser')

            # Retrives basic infos (name, descriptions...)

            name = soup.find('h1').get_text()\
                                  .replace('®', '').replace('©', '')\
                                  .replace('™', '').strip()

            name = titlecase.titlecase(name.title())

            description = soup.find('h2').get_text().strip()
            slug = '{}-{}'.format(tea_id_numeric, slugify(name))

            long_description = None

            long_description_element = soup.find(id='fiche_desc')
            if long_description_element:
                long_description = UnicodeDammit(
                    long_description_element.encode_contents())\
                    .unicode_markup.strip().replace('</br>', '')\
                    .strip('<br/>').strip()

            # Retrives tips

            tips_raw = None
            tips_mass = None
            tips_volume = None
            tips_temperature = None
            tips_duration = None

            tips_block = soup.find(id='fiche_conseil_prepa')

            if tips_block:
                tips_raw = tips_block.get_text()\
                    .replace('CONSEILS DE PRÉPARATION :', '')\
                    .strip()

                # We try to extract raw data.
                # Usual format: "2,5 g / 20 cl - 95°C - 5 min"
                # Conversion of '/' to '-' to cut the string, and
                # ',' to '.', to parse float numbers.
                tips_parts = tips_raw.replace('/', '-')\
                                     .replace(',', '.')\
                                     .lower()\
                                     .split(' - ')

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
                    image = save_distant_file(BASE_FR + '/' + image_tag.get('src'))

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

            # Updates the thing

            data = {
                'name': name,
                'vendor': vendor,
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

            updated = Tea.update(**data).where((Tea.vendor_internal_id == tea_id_numeric) & (Tea.vendor == vendor))\
                         .execute()

            has_to_add_tags = True
            if updated == 0:
                # We first check if this is really a new tea, or if the data
                # was not changed at all.
                new_tea = Tea.select().where((Tea.vendor_internal_id == tea_id_numeric) & (Tea.vendor == vendor))\
                             .count() == 0
                if new_tea:
                    # In case of an insertion, we add the slug and then check
                    # if the slug is unique
                    data['slug'] = slug
                    if data['slug'] in used_slugs:
                        suffix = 1
                        while True:
                            slug = data['slug'] + '-' + str(suffix)
                            if slug in used_slugs:
                                suffix += 1
                            else:
                                data['slug'] = slug
                                break
                    used_slugs.append(data['slug'])
                    teas_to_insert.append(data)
                    types_to_insert[tea_id_numeric] = types

                    has_to_add_tags = False

            if has_to_add_tags:
                this_tea = Tea.select(Tea.id).where((Tea.vendor_internal_id == tea_id_numeric) &
                                                    (Tea.vendor == vendor))
                TypeOfATea.delete().where(TypeOfATea.tea == this_tea).execute()
                if types:
                    TypeOfATea.insert_many([{'tea': this_tea, 'tea_type': tea_type} for tea_type in types]).execute()

    click.echo('{} fails.'.format(len(failed)))
    if failed:
        click.echo('The following URLs errored:')
        for fail in failed:
            click.echo('→ {}'.format(fail))

    click.echo()

    if teas_to_insert:
        click.echo('Inserting new records...', nl=False)
        Tea.insert_many(teas_to_insert).execute()

        # Insertion of types
        types_insert = []
        for tea in Tea.select(Tea.id, Tea.vendor_internal_id).where(Tea.vendor_internal_id <<
                                                                    list(types_to_insert.keys())):
            for tea_type in types_to_insert[tea.vendor_internal_id]:
                types_insert.append({'tea': tea, 'tea_type': tea_type})
        TypeOfATea.insert_many(types_insert).execute()

        click.echo(' Done.')
        click.echo()

    if dry_run:
        click.echo('It was a dry run, rollbacking changes...', nl=False)
        database.rollback()
    else:
        click.echo('Committing changes...', nl=False)
        database.commit()
    click.echo(' Done.')
