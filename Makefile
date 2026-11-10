OPENSPEC ?= openspec
PYTHON ?= python3
export ANSIBLE_CONFIG := $(CURDIR)/ansible.cfg
export ANSIBLE_COLLECTIONS_PATH := $(CURDIR)/.collections
export ANSIBLE_LOCAL_TEMP := $(CURDIR)/.ansible/tmp

.PHONY: spec-check spec-status example-deps example-build example-bundle example-bundle-test

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

example-bundle:
	.venv/bin/ansible-playbook examples/evpn-symmetric-irb/build.yml -e @examples/evpn-symmetric-irb/containerlab.yml
	.venv/bin/python examples/evpn-symmetric-irb/bundle.py

example-bundle-test: example-bundle
	.venv/bin/python -m unittest discover -s examples/evpn-symmetric-irb -p 'test_*.py' -v
