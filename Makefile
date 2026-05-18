PY        ?= python3
KICKSTART := ./kickstart.py

PREFIX    ?= /usr
DESTDIR   ?=
APPNAME   := amigaos-kickstart-builder
APPDIR    := $(DESTDIR)$(PREFIX)/share/$(APPNAME)
BINDIR    := $(DESTDIR)$(PREFIX)/bin

.PHONY: help lint format test build-all install clean

help:
	@echo 'Targets:'
	@echo '  lint       - ruff check .'
	@echo '  format     - ruff format .'
	@echo '  test       - pytest (unit tests of the Python code)'
	@echo '  build-all  - build every profile x every target (./kickstart.py -q)'
	@echo '  install    - install to $(PREFIX) (honours DESTDIR for rpm builds)'
	@echo '  clean      - remove out/ and workdir_*/'

lint:
	ruff check .

format:
	ruff format .

test:
	pytest

build-all:
	$(PY) $(KICKSTART) -q

install:
	install -d $(APPDIR) $(BINDIR)
	cp -r kickstart $(APPDIR)/
	install -m 0755 kickstart.py $(APPDIR)/
	cp -r templates $(APPDIR)/
	cp -r config $(APPDIR)/
	find $(APPDIR) -type d -name __pycache__ -exec rm -rf {} +
	printf '#!/bin/sh\nexec %s %s/kickstart.py "$$@"\n' \
	    "$(PY)" "$(PREFIX)/share/$(APPNAME)" > $(BINDIR)/kickstart
	chmod 0755 $(BINDIR)/kickstart

clean:
	rm -rf out workdir_*
