from flask import render_template, redirect, url_for
from playhouse.flask_utils import get_object_or_404, PaginatedQuery

from .lists import is_tea_in_favorites_list, get_tea_lists_from_request, get_lists_containing_tea
from ..model import Tea, TeaVendor, TeaType, TypeOfATea
from ..teaparty import app


@app.route('/<tea_vendor>/<tea_slug>')
def tea(tea_vendor, tea_slug):
    tea = get_object_or_404(Tea.select().join(TeaVendor),
                            Tea.slug == tea_slug.strip().lower(),
                            TeaVendor.slug == tea_vendor.strip().lower())

    tea_types = (TeaType.select(TeaType.name, TeaType.slug)
                 .join(TypeOfATea)
                 .where(TypeOfATea.tea == tea)
                 .order_by(TeaType.is_origin, TeaType.order))

    tea_tips_short = ''
    if tea.tips_mass:
        if tea.tips_mass > 0:
            tea_tips_short += (str(tea.tips_mass / 1000).replace('.', ',') + 'g')
        else:
            tea_tips_short += str(-int(tea.tips_mass)) + ' sachets'
    if tea.tips_volume:
        tea_tips_short += f'{" dans " if tea.tips_mass else ""}{tea.tips_volume} cL'
    if tea.tips_temperature:
        tea_tips_short += f'{" d&rsquo;eau à " if tea_tips_short else ""}{tea.tips_temperature}°C'
    if tea.tips_duration:
        tea_tips_short += (f'{", pendant " if tea_tips_short else ""}{tea.tips_duration // 60}'
                           f' minute{"s" if tea.tips_duration >= 120 else ""}')
    if tea_tips_short:
        tea_tips_short += '.'

    tea_lists = get_tea_lists_from_request()

    return render_template(
        'tea.html',
        tea=tea,
        tea_tips_short=tea_tips_short,
        tea_types=tea_types,
        is_in_list=is_tea_in_favorites_list(tea),
        tea_lists=tea_lists,
        tea_lists_containing=[tea_list.id for tea_list in get_lists_containing_tea(tea_lists, tea)]
    )


@app.route('/teas')
def all_teas():
    types = TeaType.select().where(TeaType.is_origin == False).order_by(TeaType.order)  # noqa
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


@app.route('/type/<tea_type_slug>')
def by_type(tea_type_slug):
    tea_type = get_object_or_404(TeaType, TeaType.slug == tea_type_slug)
    types = TeaType.select().where(TeaType.is_origin == tea_type.is_origin).order_by(TeaType.order)
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
        return redirect(url_for('by_vendor',
                                vendor_slug=TeaVendor.select(TeaVendor.slug).order_by(TeaVendor.order).first().slug))

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
