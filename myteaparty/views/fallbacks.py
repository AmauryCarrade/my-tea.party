from flask import redirect, url_for, abort, render_template

from .search import search_for_tea
from ..teaparty import app


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


@app.errorhandler(404)
def page_not_found(e):
    return render_template('errors/404.html'), 404
