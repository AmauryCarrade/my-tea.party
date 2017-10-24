from flask import render_template

from .lists import get_teas_in_active_list
from ..model import TeaVendor
from ..teaparty import app


@app.route('/')
def homepage():
    return render_template(
        'index.html',
        active_list_teas=get_teas_in_active_list(),
        vendors=TeaVendor.select().order_by(TeaVendor.order)
    )


@app.route('/about')
def about():
    return render_template('about.html', vendors=TeaVendor.select().order_by(TeaVendor.order))
