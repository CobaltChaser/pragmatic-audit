.PHONY: test audit

test:
	python3 -m unittest discover -s tests

audit:
	python3 -m pragmatic_audit . --ci --fail-on high
