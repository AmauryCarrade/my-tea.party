import math

from flask import request, render_template, redirect, url_for, abort
from peewee import SQL, fn

from ..model import Tea, TeaVendor
from ..teaparty import app


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
                      fn.IF(Tea.vendor_internal_id == word, app.config['SEARCH_WEIGHTS']['vendor_code'], 0) +
                      fn.IF(Tea.description.contains(word), app.config['SEARCH_WEIGHTS']['desc'], 0) +
                      fn.IF(Tea.long_description.contains(word), app.config['SEARCH_WEIGHTS']['ldesc'], 0))
        where_clause &= (Tea.name.contains(word) |
                         Tea.vendor_internal_id == word |
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
