import math

from flask import request, render_template
from peewee import SQL, fn
from playhouse.flask_utils import get_object_or_404

from .model import Tea, TeaVendor, TeaType, TypeOfATea
from .teaparty import app


@app.route('/')
def homepage():
    return render_template('index.html')


@app.route('/<tea_vendor>/<tea_slug>')
def tea(tea_vendor, tea_slug):
    tea = get_object_or_404(Tea.select().join(TeaVendor),
                            Tea.slug == tea_slug.strip().lower(),
                            TeaVendor.slug == tea_vendor.strip().lower())

    tea_types = (TeaType.select(TeaType.name, TeaType.slug)
                 .join(TypeOfATea)
                 .where(TypeOfATea.tea == tea)
                 .execute())

    print(tea_types)
    return render_template('tea.html', tea=tea, tea_types=tea_types)


def search_for_tea(search_query, paginate_by=0, page=1):
    """
    Searchs for teas using the given query and returns a peewee query
    with the results.

    If paginate_by and page are given (and positive), paginates the
    results and returns a tuple with the peewee query and the pages
    count. If search_query evaluates to False, returns [] instead of
    a peewee query.
    """
    if not search_query:
        return [] if paginate_by <= 0 else [], 0

    teas = (Tea
            .select(
                Tea.name,
                Tea.slug,
                Tea.description,
                Tea.illustration,
                Tea.tips_raw,
                Tea.tips_mass,
                Tea.tips_volume,
                Tea.tips_duration,
                Tea.tips_temperature,
                TeaVendor.name.alias('vendor_name'),
                TeaVendor.slug.alias('vendor_slug'),
                (
                    fn.IF(Tea.name.contains(search_query), app.config['SEARCH_WEIGHTS']['name'], 0)
                    + fn.IF(Tea.description.contains(search_query), app.config['SEARCH_WEIGHTS']['desc'], 0)
                    + fn.IF(Tea.long_description.contains(search_query), app.config['SEARCH_WEIGHTS']['ldesc'], 0)
                ).alias('relevance'))
            .join(TeaVendor)
            .having(SQL('relevance') != 0)
            .order_by(SQL('relevance DESC')))

    if paginate_by > 0:
        count = (Tea.select()
                    .where(Tea.name.contains(search_query) |
                           Tea.description.contains(search_query) |
                           Tea.long_description.contains(search_query))
                    .count())

        pages_count = int(math.ceil(float(count) / paginate_by))
        teas = teas.paginate(page, paginate_by)

    return teas if paginate_by <= 0 else (teas, pages_count)


@app.route('/search')
def search():
    search_query = request.args.get('q')
    page = request.args.get('page')

    page = int(page) if page and page.isdigit() else 1
    page = page if page >= 1 else 1

    teas, pages_count = search_for_tea(search_query, paginate_by=app.config['ITEMS_PER_PAGE'], page=page)

    return render_template('search.html', search_query=search_query, teas=teas, pagination={
        'page': page,
        'pages': pages_count
    })
