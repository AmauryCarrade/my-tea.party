'use strict';

window.getCookie = function(name)
{
	var match = document.cookie.match(new RegExp(name + '=([^;]+)'));
	if (match) return match[1];
};

(function()
{
	if (!window.localStorage) return;

	var cookies_tea_lists = getCookie(mtp_config['cookies']['lists']);
	var cookies_active_list = getCookie(mtp_config['cookies']['active_list']);

	if (cookies_tea_lists) cookies_tea_lists = cookies_tea_lists.split('|');
	else                   cookies_tea_lists = [];

	var ls_tea_lists = localStorage.getItem(mtp_config['cookies']['lists']);
	var ls_active_list = localStorage.getItem(mtp_config['cookies']['active_list']);

	if (ls_tea_lists) ls_tea_lists = JSON.parse(ls_tea_lists);
	if (ls_active_list) ls_active_list = JSON.parse(ls_active_list);

	// We check if cookies and local storage are in sync
	// Priority goes to local storage

	// If there is nothing at all, well.
	if (!ls_tea_lists && !ls_active_list && !cookies_tea_lists && !cookies_active_list)
	{
		return;
	}

	// No local storage (or partial) -> sync from cookies.
	if (!ls_tea_lists || !ls_active_list)
	{
		localStorage.setItem(mtp_config['cookies']['lists'], JSON.stringify(cookies_tea_lists));
		localStorage.setItem(mtp_config['cookies']['active_list'], JSON.stringify(cookies_active_list));
	}

	// Else, if there is something in the local storage and no cookies, or contents differ, we sync from the local storage.
	else
	{
		var sync_active_from_ls = false;
		var sync_lists_from_ls = false;

		if (!cookies_active_list) sync_active_from_ls = true;
		if (!cookies_tea_lists) sync_lists_from_ls = true;

		if (!sync_active_from_ls && cookies_active_list.toLowerCase() != ls_active_list.toLowerCase())
			sync_active_from_ls = true;

		if (!sync_lists_from_ls && cookies_tea_lists.join().toLowerCase() != ls_tea_lists.join().toLowerCase())
			sync_lists_from_ls = true;

		if (sync_lists_from_ls)
			document.cookie = mtp_config['cookies']['lists'] + '=' + ls_tea_lists.join('|');

		if (sync_active_from_ls)
			document.cookie = mtp_config['cookies']['active_list'] + '=' + ls_active_list;

		if (sync_lists_from_ls || sync_active_from_ls)
			window.location.reload(true);
	}
})();
