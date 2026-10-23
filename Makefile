.PHONY: test audit self-audit

test:
	python3 -m unittest discover -s tests -v

audit:
	python3 -m pragmatic_audit . --ci --fail-on high

self-audit:
	./scripts/self_audit.sh
