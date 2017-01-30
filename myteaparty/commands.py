import click
import datetime
import requests
import re
import titlecase

from bs4 import BeautifulSoup, UnicodeDammit
from flask import g
from slugify import slugify

from .teaparty import *


def get_crawling_session():
    """
    Returns a crawling session with user agent and other global options to
    use to crawl websites.

    :return: requests.Session
    """
    s = requests.Session()
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:52.0) '
                      'Gecko/20100101 Firefox/52.0 (compatible; '
                      'MyTeaPartyCrawler/0.1-experiment; '
                      '+https://amaury.carrade.eu/contact)'
    })

    return s


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

    titlecase.set_small_word_list(titlecase.SMALL
                                  + '|un|une|de|des|du|d|le|la|les|au|à|a')

    database.begin()

    mf_logo = save_distant_file('https://upload.wikimedia.org/wikipedia/'
                                'commons/a/ad/Logo_seul.jpg')
    vendor, _ = TeaVendor.get_or_create(
        name='Mariage Frères',
        slug='mariage-freres',
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
    categories = soup.find(id='bas_centre').find_all(id='bas_centre_rep')[2]\
                     .find_all(class_='bas_lien')

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
                links.extend([l.get('href').replace('./', BASE_FR + '/')
                              for l in s_menu.findAll('a')
                              if l.get('href') is not None])

    failed = []
    with click.progressbar(length=len(links) + 1,
                           label='Retrieving references'.ljust(32)) as bar:
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
        # For duplicates, we try to use the one with ID “T<number>” if
        # available, else the first found.
        # We first group the teas by ID (filtering non-tea items on the
        # fly) and then use the better one

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

    click.echo('{} references found. {} fails.'.format(len(teas_links),
                                                       len(failed)))
    if failed:
        click.echo('The following URLs errored:')
        for fail in failed:
            click.echo('→ {}'.format(fail))

    click.echo()

    click.echo('Flagging entries in database but not retrieved as '
               'deleted...', nl=False)
    Tea.update(deleted=datetime.datetime.now())\
        .where((Tea.vendor_internal_id.not_in(teas_ids)) &
               (Tea.vendor == vendor))\
        .execute()
    click.echo(' Done.')
    click.echo()

    teas_to_insert = []
    re_remove_non_numbers = re.compile('[^0-9.]')
    failed = []
    with click.progressbar(teas_links, label='Retrieving tea '
                                             'informations'.ljust(32))\
            as bar:
        for tea_link in bar:
            tea_id, tea_id_numeric = extract_tea_id_from_link(tea_link)
            try:
                r = s.get(tea_link)
                r.raise_for_status()
            except Exception:
                failed.append(tea_link)
                continue

            soup = BeautifulSoup(r.text, 'html.parser')

            name = soup.find('h1').get_text()\
                                  .replace('®', '').replace('©', '')\
                                  .replace('™', '').strip()

            name = titlecase.titlecase(name.title())

            description = soup.find('h2').get_text().strip()
            slug = '{}-{}'.format(tea_id_numeric, slugify(name))

            long_description = None

            long_descr_elmnt = soup.find(id='fiche_desc')
            if long_descr_elmnt:
                long_description = UnicodeDammit(
                    soup.find(id='fiche_desc').encode_contents())\
                    .unicode_markup.strip().replace('</br>', '')\
                    .strip('<br/>').strip()

            tips_raw = None
            tips_mass = None
            tips_volume = None
            tips_temperature = None
            tips_duration = None

            image = None

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
                    tip_num = float(re_remove_non_numbers.sub('', tips_part))
                    if 'cl' in tips_part:
                        tips_volume = int(tip_num)
                    elif 'c' in tips_part:
                        tips_temperature = int(tip_num)
                    elif 'g' in tips_part:
                        tips_mass = int(tip_num * 1000)
                    elif 'min' in tips_part:
                        tips_duration = int(tip_num * 60)
            else:
                # Maybe another tips format found on some specific pages
                tips_block = soup.find(id='fiche_suggestion')
                if tips_block:
                    tips_raw = tips_block.get_text()\
                        .replace('CONSEILS DE PRÉPARATION :', '').strip()

            image_block = soup.find(id='A9', class_='valignmiddle')
            if image_block:
                image_tag = image_block.find('img')
                if image_tag and image_tag.get('src'):
                    image = save_distant_file(BASE_FR + '/'
                                                      + image_tag.get('src'))

            # Update the thing
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
                'link': tea_link
            }

            query = Tea.update(**data)\
                       .where((Tea.vendor_internal_id == tea_id_numeric)
                              & (Tea.vendor == vendor))
            updated = query.execute()

            if updated == 0:
                # We first check if this is really a new tea, or if the data
                # was not changed at all.
                new_tea = Tea.select()\
                             .where((Tea.vendor_internal_id == tea_id_numeric)
                                    & (Tea.vendor == vendor)).count() == 0
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

    click.echo('{} fails.'.format(len(failed)))
    if failed:
        click.echo('The following URLs errored:')
        for fail in failed:
            click.echo('→ {}'.format(fail))

    click.echo()

    if teas_to_insert:
        click.echo('Inserting new records...', nl=False)
        Tea.insert_many(teas_to_insert).execute()
        click.echo(' Done.')

    click.echo()
    if dry_run:
        click.echo('It was a dry run, rollbacking changes...', nl=False)
        database.rollback()
    else:
        click.echo('Committing changes...', nl=False)
        database.commit()
    click.echo(' Done.')
