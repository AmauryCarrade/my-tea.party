from flask import render_template

from .lists import get_teas_in_favorites_list, get_tea_lists_from_request, get_last_viewed_list_key
from ..model import TeaVendor
from ..teaparty import app


@app.route('/')
def homepage():
    return render_template(
        'index.html',
        favorites_list_teas=get_teas_in_favorites_list(),
        lists_teas=get_tea_lists_from_request(),
        last_viewed_list_key=get_last_viewed_list_key(),
        vendors=TeaVendor.select().order_by(TeaVendor.order)
    )


@app.route('/about')
def about():
    return render_template('about.html', vendors=TeaVendor.select().order_by(TeaVendor.order))
