OPENSPEC ?= openspec
PYTHON ?= python3
export ANSIBLE_CONFIG := $(CURDIR)/ansible.cfg
export ANSIBLE_COLLECTIONS_PATH := $(CURDIR)/.collections
export ANSIBLE_LOCAL_TEMP := $(CURDIR)/.ansible/tmp

.PHONY: spec-check spec-status example-deps example-build

spec-check:
	$(OPENSPEC) validate --all --strict --no-interactive

spec-status:
	$(OPENSPEC) list

example-deps:
	$(PYTHON) -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt
	.venv/bin/ansible-galaxy collection install -r collection-requirements.yml -p .collections

example-build:
	.venv/bin/ansible-playbook examples/evpn-symmetric-irb/build.yml
