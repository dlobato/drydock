OPENSPEC ?= openspec

.PHONY: spec-check spec-status

spec-check:
	$(OPENSPEC) validate --all --strict --no-interactive

spec-status:
	$(OPENSPEC) list
