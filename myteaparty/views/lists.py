import random
import uuid

from datetime import datetime, timedelta
from flask import jsonify, request, redirect, url_for
from playhouse.flask_utils import get_object_or_404

from ..model import Tea, TeaList, TeaListItem
from ..teaparty import app
from ..utils import after_request


_cookies_properties = {'expires': datetime.now() + timedelta(days=366*84), 'max_age': int(timedelta(days=366*84).total_seconds())}


def create_tea_list(name=None):
	'''
	Creates a new teas list, with the provided name or a default one.
	'''
	return TeaList.create(
		name=name or app.config['LISTS_DEFAULT_NAME'],
		cookie_key=str(uuid.uuid4().hex).upper().replace('-', ''),
		share_key=random.randint(100000, 999999),
		creator_ip=request.remote_addr
	)

def add_to_list(tea_list, tea):
	'''
	Adds a tea to a list. Returns the new list item model instance.
	'''
	item, _ = TeaListItem.get_or_create(
		tea=tea,
		tea_list=tea_list,
		defaults={'is_empty': False}
	)

	return item

def remove_from_list(tea_list, tea):
	'''
	Removes a tea from a list.
	'''
	TeaListItem.delete().where((TeaListItem.tea_list == tea_list) & (TeaListItem.tea == tea)).execute()

def set_empty_in_list(tea_list, tea, empty=None):
	'''
	Marks a tea as empty in a list.

	empty: if None, toggles the value. Else (True/False) sets the given value.
	'''
	try:
		item = TeaListItem.get(tea_list=tea_list, tea=tea)
	except TeaListItem.DoesNotExist:
		return

	empty_value = empty
	if empty is None:
		empty_value = not item.is_empty

	item.is_empty = empty_value
	item.save()

def set_active_list(response, active_list):
	'''
	Sets the cookies to refer the active list.
	'''
	response.set_cookie(app.config['COOKIE_ACTIVE_LIST'], active_list.cookie_key, **_cookies_properties)
	add_to_registered_lists(response, active_list)

def add_to_registered_lists(response, tea_list):
	registered_lists = [i for i in request.cookies.get(app.config['COOKIE_LISTS'], '').split('|') if i]
	if tea_list.cookie_key not in registered_lists:
		registered_lists.append(tea_list.cookie_key)
		response.set_cookie(app.config['COOKIE_LISTS'], '|'.join(registered_lists), **_cookies_properties)

def get_tea_list_from_request(create=True):
	active_list_id = request.cookies.get(app.config['COOKIE_ACTIVE_LIST'])
	active_list = None

	if active_list_id:
		try:
			active_list = TeaList.get(TeaList.cookie_key == active_list_id)
		except TeaList.DoesNotExist:
			active_list = None

	if not active_list and create:
		active_list = create_tea_list()

		@after_request
		def set_active_cookie(response):
			set_active_list(response, active_list)

	return active_list

def is_tea_in_active_list(tea):
	# This is checked on every tea page, so if there is no list,
	# we don't want to create one. Just to check if it's in the list
	# if it exists.
	active_list = get_tea_list_from_request(create=False)
	if not active_list:
		return False

	return (TeaListItem.select()
		               .where((TeaListItem.tea_list == active_list) & (TeaListItem.tea == tea))
		               .exists())

def get_teas_in_active_list():
	active_list = get_tea_list_from_request(create=False)
	if not active_list:
		return []

	return (TeaListItem.select()
			   .join(TeaList)
			   .join(Tea, on=Tea.id == TeaListItem.tea)
			   .where(TeaList.id == active_list.id)
	)


def _handle_response(tea):
	'''
	Handles the response of an API call for tea lists endpoints.
	'''
	if request.method == 'GET':
		return redirect(request.args.get('next') if 'next' in request.args else url_for('tea', tea_vendor=tea.vendor.slug, tea_slug=tea.slug))
	else:
		return jsonify({'result': 'ok'})


@app.route('/lists/active', methods=['PUT'])
@app.route('/lists/active/add')
def add_tea_to_list():
	tea = get_object_or_404(Tea, Tea.id == request.args.get('tea_id', type=int))
	add_to_list(get_tea_list_from_request(), tea)

	return _handle_response(tea)

@app.route('/lists/active', methods=['DELETE'])
@app.route('/lists/active/remove')
def remove_tea_from_list():
	tea = get_object_or_404(Tea, Tea.id == request.args.get('tea_id', type=int))
	remove_from_list(get_tea_list_from_request(), tea)

	return _handle_response(tea)

@app.route('/lists/active/toggle_empty')
def toggle_empty_tea_in_list():
	tea = get_object_or_404(Tea, Tea.id == request.args.get('tea_id', type=int))
	set_empty_in_list(get_tea_list_from_request(), tea)

	return _handle_response(tea)
