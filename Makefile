
PYCODESTYLE=pycodestyle
PEP8_ARG=
# --ignore=E501,E221,E241,E502,W503

PYLINT=pylint
PYLINT_ARG=--max-nested-blocks=10 --max-branches=20

all: pylint pycodestyle

FILES=find-duplicates.py

pylint:
	${PYLINT} ${PYLINT_ARG} ${FILES}

pep8: pycodestyle

pycodestyle:
	${PYCODESTYLE} ${PEP8_ARG} ${FILES}
