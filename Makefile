styles:
	sass --scss -t compressed myteaparty/static/assets/sass/myteaparty.scss > myteaparty/static/assets/css/myteaparty.min.css

watch:
	sass --scss -t compressed --watch myteaparty/static/assets/sass/myteaparty.scss:myteaparty/static/assets/css/myteaparty.min.css

run:
	FLASK_APP=myteaparty/__init__.py FLASK_DEBUG=1 flask run
