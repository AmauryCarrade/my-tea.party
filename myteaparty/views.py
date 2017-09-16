import math

from flask import request, render_template, redirect, url_for, abort
from peewee import SQL, fn
from playhouse.flask_utils import get_object_or_404, PaginatedQuery

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
                 .where(TypeOfATea.tea == tea))

    return render_template('tea.html', tea=tea, tea_types=tea_types)


def search_for_tea(search_query, paginate_by=0, page=1):
    """
    Searchs for teas using the given query and returns a peewee query
    with the results.

    If paginate_by and page are given (and positive), paginates the
    results and returns a tuple with the peewee query, the total number
    of results and the pages count. If search_query evaluates to False,
    returns [] instead of a peewee query.
    """
    if not search_query:
        return [] if paginate_by <= 0 else [], 0, 0

    search_terms = search_query.split()

    relevance = SQL('0')
    where_clause = SQL('1')
    for word in search_terms:
        relevance += (fn.IF(Tea.name.contains(word), app.config['SEARCH_WEIGHTS']['name'], 0) +
                      fn.IF(Tea.description.contains(word), app.config['SEARCH_WEIGHTS']['desc'], 0) +
                      fn.IF(Tea.long_description.contains(word), app.config['SEARCH_WEIGHTS']['ldesc'], 0))
        where_clause &= (Tea.name.contains(word) |
                         Tea.description.contains(word) |
                         Tea.long_description.contains(word))

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
                relevance.alias('relevance'))
            .join(TeaVendor)
            .where(where_clause)
            .having(SQL('relevance') != 0)
            .order_by(SQL('relevance DESC')))

    if paginate_by > 0:
        count = Tea.select().where(where_clause).count()
        pages_count = int(math.ceil(float(count) / paginate_by))

        if page != 1 and page > pages_count:
            abort(404)

        teas = teas.paginate(page, paginate_by)

    return teas if paginate_by <= 0 else (teas, count, pages_count)

@app.route('/search')
def search():
    search_query = request.args.get('q')
    page = request.args.get('page')

    page = max(1, int(page) if page and page.isdigit() else 1)

    teas, count, pages_count = search_for_tea(search_query, paginate_by=app.config['ITEMS_PER_PAGE'], page=page)

    if count == 1:
        tea = teas.dicts()[0]
        return redirect(url_for('tea', tea_slug=tea['slug'], tea_vendor=tea['vendor_slug']), 302)

    return render_template('search.html', search_query=search_query, teas=teas, pagination={
        'page': page,
        'pages': pages_count
    })


@app.route('/type/<tea_type_slug>')
def by_type(tea_type_slug):
    tea_type = get_object_or_404(TeaType, TeaType.slug == tea_type_slug)
    types = TeaType.select().where(TeaType.is_origin == tea_type.is_origin)
    teas = PaginatedQuery(
            (Tea.select(Tea, TeaVendor)
                .join(TypeOfATea)
                .join(TeaType)
                .where(TypeOfATea.tea_type == tea_type)
                .switch(Tea)
                .join(TeaVendor)),
            paginate_by=app.config['ITEMS_PER_PAGE'],
            page_var='page',
            check_bounds=True
    )

    return render_template('tea_types.html', teas=teas, types=types, tea_type=tea_type, all=False, pagination={
        'page': teas.get_page(),
        'pages': teas.get_page_count()
    })

@app.route('/vendor', defaults={'vendor_slug': None})
@app.route('/vendors', defaults={'vendor_slug': None})
@app.route('/vendor/<vendor_slug>')
def by_vendor(vendor_slug):
    if vendor_slug is None:
        return redirect(url_for('by_vendor', vendor_slug=TeaVendor.select(TeaVendor.slug).order_by(TeaVendor.order).first().slug))

    vendor = get_object_or_404(TeaVendor, TeaVendor.slug == vendor_slug)
    vendors = TeaVendor.select().order_by(TeaVendor.order)
    teas = PaginatedQuery(
            (Tea.select(Tea, TeaVendor)
                .join(TeaVendor)
                .where(Tea.vendor == vendor)),
            paginate_by=app.config['ITEMS_PER_PAGE'],
            page_var='page',
            check_bounds=True
    )

    return render_template('tea_vendors.html', vendors=vendors, teas=teas, tea_vendor=vendor, pagination={
        'page': teas.get_page(),
        'pages': teas.get_page_count()
    })

@app.route('/teas')
def all_teas():
    types = TeaType.select().where(TeaType.is_origin == False)
    teas = PaginatedQuery(
            (Tea.select(Tea, TeaVendor).join(TeaVendor)),
            paginate_by=app.config['ITEMS_PER_PAGE'],
            page_var='page',
            check_bounds=True
    )

    return render_template('tea_types.html', teas=teas, types=types, tea_type=None, all=True, pagination={
        'page': teas.get_page(),
        'pages': teas.get_page_count()
    })


@app.route('/<search_fallback>')
def search_generic_fallback(search_fallback):
    teas, count, _ = search_for_tea(search_fallback, paginate_by=2)

    if count > 1:
        return redirect(url_for('search', q=search_fallback), 302)
    elif count == 1:
        tea = teas.dicts()[0]
        return redirect(url_for('tea', tea_slug=tea['slug'], tea_vendor=tea['vendor_slug']), 302)
    else:
        abort(404)
