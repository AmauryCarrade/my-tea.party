import click
import datetime
import importlib
import os
import pkgutil
import requests
import re
import titlecase

from bs4 import BeautifulSoup, UnicodeDammit
from itertools import cycle, islice, groupby
from path import Path
from slugify import slugify

from .teaparty import app
from .model import Tea, TeaType, TypeOfATea, TeaVendor, database
from .model import get_or_create as get_or_create_model
from .utils import save_distant_file, generate_thumbnails, get_external_filename, is_post_processed_file

import myteaparty.tea_vendors as vendors


class TeaVendorImporter(object):
    def __init__(self, session, retries=3):
        self.session = session
        self.retries = retries

        self._cached_tea_types = None

    def get_tea_types(self):
        """
        Returns a list of tuples containing as first argument, the tea type
        instance, and as second, a list of names to be found in the pages
        to ckeck if the tea is this type.
        """
        def get_or_create(*args, **kwargs):
            return get_or_create_model(TeaType, *args, **kwargs)[0]

        return [
            (get_or_create(name='Thé noir', slug='noir', is_origin=False), ['Thé noir', 'Black Tea']),
            (get_or_create(name='Thé vert', slug='vert', is_origin=False), ['Thé vert', 'Green Tea']),
            (get_or_create(name='Thé blanc', slug='blanc', is_origin=False), ['Thé blanc']),
            (get_or_create(name='Thé mûr', slug='mur', is_origin=False), ['Thé mûr', 'Thé mur',
                                                                          'Pu-erh', 'Puerh', 'Pu Erh']),
            (get_or_create(name='Thé Oolong', slug='oolong', is_origin=False), ['Oolong']),
            (get_or_create(name='Thé jaune', slug='jaune', is_origin=False), ['Thé jaune']),
            (get_or_create(name='Thé bleu', slug='bleu', is_origin=False), ['Thé bleu']),
            (get_or_create(name='Thé rouge', slug='rouge', is_origin=False), ['Thé rouge', 'Thé rouge sans théine',
                                                                              'sans théine', 'Rooibos']),
            (get_or_create(name='Thé fûmé', slug='fume', is_origin=False), ['Thé fûmé', 'Thé fumé']),
            (get_or_create(name='Thé au Jasmin', slug='jasmin', is_origin=False), ['Thé au jasmin', 'Jasmin', 'Jasmine']),
            (get_or_create(name='Infusion', slug='infusion', is_origin=False), ['Infusion', 'Infusion de fruits']),

            (get_or_create(name='Grand cru', slug='grand-cru', is_origin=False), ['Grand cru']),
            (get_or_create(name='Darjeeling', slug='darjeeling', is_origin=True), ['Darjeeling']),
            (get_or_create(name='Assam', slug='assam', is_origin=True), ['Assam', 'Assam d\'Été']),
            (get_or_create(name='Ceylan', slug='ceylan', is_origin=True), ['Ceylan']),
            (get_or_create(name='Thé de Chine', slug='chine', is_origin=True), ['Chine']),
            (get_or_create(name='Thé du Japon', slug='japon', is_origin=True), ['Japon'])
        ]

    def _get(self, url, **kwargs):
        """
        Loads an URL using the class' session. Retries a few times (according
        to self.retries) and then gives up, printing an error message and
        returning None.

        :param url: The URL to load (using a GET request).
        :param **kwargs: Optional arguments that ``request`` takes.
        :return: The requests.Response object, or None if the request failed
                 too many times.
        """
        last_exception = None
        for _ in range(self.retries):
            try:
                r = self.session.get(url, **kwargs)
                r.raise_for_status()
                return r
            except requests.RequestException as e:
                last_exception = e
        click.echo('Unable to get « {} », giving up after {} retries.\n{}'
                        .format(url, self.retries, last_exception), err=True)
        return None

    def _retrieve_teas_types(self, *haystacks):
        """
        Lookups in all string haystacks given for keywords retrieved from
        self.get_tea_types(), and returns a list of types found.
        """
        if not self._cached_tea_types:
            self._cached_tea_types = self.get_tea_types()

        types = []
        haystacks = [haystack.lower() for haystack in haystacks]
        for tea_type, keywords in self._cached_tea_types:
            keywords_lower = [w.lower() for w in keywords]
            if tea_type not in types and any(keyword in haystack for keyword in keywords_lower
                                                                 for haystack in haystacks):
                types.append(tea_type)

        return types

    def get_vendor(self):
        """
        Returns an instance of the TeaVendor for this vendor.
        This method is called multiple times; it's result should be cached.

        :return: TeaVendor
        """
        pass

    def prepare_references(self):
        """
        This is called first, before the references crawling.
        It should prepare the crawl (e.g. list pages to analyze) and
        return a number of steps used by the retrieve_references
        method below, for an optimized UI.

        :return: The number of steps of the retrieve_references method,
                 or None if nothing has been retrieved.
        """
        pass

    def retrieve_references(self):
        """
        Retrieves the references. Yields each time a step (defined in the previous
        method) is achieved (e.g. one page analyzed).
        """
        pass

    def analyze_references(self):
        """
        Analyses and if needed cleanup the references.

        :return: a tuple with the number of references found, and a list
                 of errored references (strings)
        """
        pass

    def crawl_teas(self):
        """
        Crawl the teas themselves. Yields for each tea retrieved a tuple with a dict
        containing the keys in the Tea model, and a list with the tags of this tea
        (instances of the TypeOfATea, see self.get_tea_types()).
        """
        pass

    def get_crawl_errors(self):
        """
        Returns a list of crawling errors (e.g. URL not crawled because
        of network error or 404).

        :return: List of errors.
        """
        pass

    def get_retrieved_internal_ids(self):
        """
        Returns the retrieved teas internal IDs from the vendor (the
        one returned as vendor_internal_id in crawl_teas).
        This is used to ckeck for deleted teas and mark them as such.

        This is called after crawl_teas.

        :return: a list containing the retrieved teas internal IDs.
        """
        pass


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


def roundrobin(*iterables):
    """
    roundrobin('ABC', 'D', 'EF') --> A D E B F C
    """
    # Recipe credited to George Sakkis
    pending = len(iterables)
    nexts = cycle(iter(it).__next__ for it in iterables)
    while pending:
        try:
            for next in nexts:
                yield next()
        except StopIteration:
            pending -= 1
            nexts = cycle(islice(nexts, pending))


@app.cli.command('import')
@click.option('--dry-run', is_flag=True, default=False, help='If specified, the database will not be altered.')
@click.argument('importer', nargs=-1)
def import_command(dry_run, importer):
    """
    Imports teas from the specified vendors.
    ”all” is a special value to import from all existing vendors at once.
    """
    importers_names = [name for _, name, _ in pkgutil.iter_modules([os.path.dirname(vendors.__file__)])]
    importers_active = []
    importers = importer

    if 'all' in importers:
        click.echo(f'Using all importers on request: {", ".join(importers_names)}.')
        importers_active.extend(importers_names)
    else:
        importers_active.extend([importer for importer in importers if importer in importers_names])
        skipped = [importer for importer in importers if importer not in importers_names]
        if skipped:
            click.echo(f'Skipping the following importers (not found): {", ".join(skipped)}', err=True)

    if not importers_active:
        if not importers:
            click.echo(f'No imported specified. Valid importers: {", ".join(importers_names)}.'.format(', '.join(importers_names)), err=True)
        else:
            click.echo('No valid importer selected. Exiting.', err=True)
        click.echo('Use --help for help.', err=True)
        return

    importers_instances = [importlib.import_module('.' + importer, package=vendors.__name__)
                                    .Importer(get_crawling_session()) for importer in importers_active]

    click.echo(click.style('\nStarting import from {}...'.format(
                                ', '.join([imp.get_vendor().name for imp in importers_instances])), bold=True))
    if dry_run:
        click.echo('Performing a dry run.')

    database.begin()

    titlecase.set_small_word_list(titlecase.SMALL + '|un|une|de|des|du|d|le|la|les|l|au|à|a|s')
    used_slugs = Tea.select(Tea.slug, TeaVendor.name).join(TeaVendor).order_by(TeaVendor.name).execute()
    used_slugs = {vendor:[slug.slug for slug in vendor_slugs] for vendor, vendor_slugs
                                                              in groupby(used_slugs, key=lambda r: r.vendor.name)}

    click.echo('\nRetrieving references...', nl=False)

    references_steps = 0
    for imp in importers_instances:
        steps = imp.prepare_references()
        if steps is None:
            click.echo(f'\nReferences pre-collection failed for {imp.__class__.__name__}', err=True)
        else:
            references_steps += steps

    with click.progressbar(length=references_steps + 1, label='Retrieving references'.ljust(32)) as bar:
        for _ in roundrobin(*[imp.retrieve_references() for imp in importers_instances]):
            bar.update(1)

        references_count = 0
        references_errors = []

        for imp in importers_instances:
            found, errors = imp.analyze_references()
            references_count += found
            references_errors += errors

        bar.update(1)

    click.echo(f'{references_count} references found. {len(references_errors)} fails.')
    if references_errors:
        click.echo('The following errored:', err=True)
        for error in references_errors:
            click.echo(f'→ {error}', err=True)

    click.echo()

    types_to_insert = {}
    teas_to_insert = []

    with click.progressbar(length=references_count, label='Retrieving tea informations'.ljust(32)) as bar:
        for data, types in roundrobin(*[imp.crawl_teas() for imp in importers_instances]):
            if data is None:
                bar.update(1)
                continue

            vendor = data['vendor']

            data['name'] = titlecase.titlecase(data['name'].title())
            data['deleted'] = None  # If a previously-deleted tea is retrieved, it is no longer deleted,
                                    # and unmarked as such in our database.

            # If an illustration cannot be retrieved, the key is
            # removed so the old one is kept in case of an update.
            # (If this is an insertion, the default value is None
            # anyway.)
            # To remove a previously saved illustration, set this to
            # an empty string.
            if data['illustration'] is None:
                del data['illustration']

            updated = (Tea.update(**data)
                          .where((Tea.vendor_internal_id == str(data['vendor_internal_id'])) &
                                 (Tea.vendor == vendor))
                          .execute())

            has_to_add_tags = True
            if updated == 0:
                # We first check if this is really a new tea, or if the data
                # was not changed at all.
                new_tea = (Tea.select()
                              .where((Tea.vendor_internal_id == str(data['vendor_internal_id'])) &
                                     (Tea.vendor == vendor))
                              .count() == 0)
                if new_tea:
                    # In case of an insertion, we add the slug and then check
                    # if the slug is unique
                    if vendor.name not in used_slugs:
                        used_slugs[vendor.name] = []

                    data['slug'] = slugify(data['name'])
                    if data['slug'] in used_slugs[vendor.name]:
                        suffix = 1
                        while True:
                            slug = data['slug'] + '-' + str(suffix)
                            if slug in used_slugs[vendor.name]:
                                suffix += 1
                            else:
                                data['slug'] = slug
                                break
                    used_slugs[vendor.name].append(data['slug'])

                    teas_to_insert.append(data)
                    if vendor.name not in types_to_insert:
                        types_to_insert[vendor.name] = {}
                    types_to_insert[vendor.name][str(data['vendor_internal_id'])] = types

                    has_to_add_tags = False

            if has_to_add_tags:
                this_tea = Tea.select(Tea.id).where((Tea.vendor_internal_id == str(data['vendor_internal_id'])) &
                                                    (Tea.vendor == vendor))
                TypeOfATea.delete().where(TypeOfATea.tea == this_tea).execute()
                if types:
                    TypeOfATea.insert_many([{'tea': this_tea, 'tea_type': tea_type} for tea_type in types]).execute()

            bar.update(1)

    failed = []
    for imp in importers_instances:
        failed.extend(imp.get_crawl_errors() or [])

    click.echo(f'{len(failed)} fails.')
    if failed:
        click.echo('The following errored:', err=True)
        for fail in failed:
            click.echo(f'→ {fail}', err=True)

    click.echo()

    if teas_to_insert:
        click.echo(f'Inserting {len(teas_to_insert)} new record{"s" if len(teas_to_insert) > 1 else ""}...', nl=False)

        # Because if teas are deleted we does not update the illustration to avoid a loss,
        # there is two categories of teas: ones with an 'illustration' key and one without.
        # We separate these two because the bulk insert requires all dicts to have the same
        # keys.
        teas_to_insert_with_illustration = [tea for tea in teas_to_insert if 'illustration' in tea]
        teas_to_insert_without_illustration = [tea for tea in teas_to_insert if 'illustration' not in tea]

        Tea.insert_many(teas_to_insert_with_illustration).execute()
        Tea.insert_many(teas_to_insert_without_illustration).execute()

        # Insertion of types
        types_insert = []
        for types_to_insert_vendor in types_to_insert:
            for tea in (Tea.select(Tea.id, Tea.vendor_internal_id)
                           .join(TeaVendor)
                           .where(Tea.vendor_internal_id << list(types_to_insert[types_to_insert_vendor].keys()) &
                                  TeaVendor.name == types_to_insert_vendor)):
                for tea_type in types_to_insert[types_to_insert_vendor][tea.vendor_internal_id]:
                    types_insert.append({'tea': tea, 'tea_type': tea_type})

        if types_insert:
            TypeOfATea.insert_many(types_insert).execute()

        click.echo(' Done.')
        click.echo()

    click.echo('Flagging entries in database but not retrieved as deleted...', nl=False)
    for imp in importers_instances:
        (Tea.update(deleted=datetime.datetime.now())
            .where((Tea.vendor_internal_id.not_in(imp.get_retrieved_internal_ids())) &
                   (Tea.vendor == imp.get_vendor())).execute())
    click.echo(' Done.')
    click.echo()

    if dry_run:
        click.echo('It was a dry run, rollbacking changes...', nl=False)
        database.rollback()
    else:
        click.echo('Committing changes...', nl=False)
        database.commit()
    click.echo(' Done.')


@app.cli.command('generate-thumbnails')
@click.option('--regenerate', is_flag=True, default=False, help='If specified, existing thumbnails will be re-genered')
@click.option('--directory', default=Path(app.root_path) / 'static' / app.config['STATIC_FILES_FOLDER'], show_default=True, help='The root directory where files are stored')
def generate_thumbnails_command(regenerate, directory):
    directory = Path(directory)
    if not directory.exists():
        click.echo('Directory does not exists. Exiting.', err=True)
        return

    formats = list(app.config['STATIC_FILES_FORMATS'].keys())
    formats += [format + '@2x' for format in formats]
    
    for file in directory.walkfiles():
        if is_post_processed_file(file):
            continue

        file_dir = file.dirname()
        files_all_ok = all([(file_dir / get_external_filename(file, file_format)).exists() for file_format in formats])
        
        if not files_all_ok or regenerate:
            click.echo(f'Generating thumbnails for {file.name}…{" [regenerated]" if regenerate else ""}')
            generate_thumbnails(file)

    click.echo('Done.')
