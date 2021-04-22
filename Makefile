.PHONY: update-deps
update-deps:
	pip install --upgrade pip-tools pip setuptools
	# add --generate-hashes to the next two lines if and when
	# installation of daf_butler allows it (though I doubt it will)
	pip-compile --upgrade --build-isolation --output-file requirements/main.txt requirements/main.in
	pip-compile --upgrade --build-isolation --output-file requirements/dev.txt requirements/dev.in

.PHONY: init
init:
	pip install --editable .
	pip install --upgrade -r requirements/main.txt -r requirements/dev.txt
	rm -rf .tox
	pip install --upgrade tox
	pre-commit install

.PHONY: update
update: update-deps init

.PHONY: run
run:
	adev runserver --app-factory create_app src/exposurelog/app.py
