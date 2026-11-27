.PHONY: check lint test examples loc

PYTHON ?= python3
SRC := src/citecheck
LOC_LIMIT := 600

check: lint test examples loc

lint:
	$(PYTHON) -m py_compile $(SRC)/*.py tests/*.py examples/*.py
	@command -v ruff >/dev/null 2>&1 && ruff check $(SRC) tests examples || true

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

examples:
	PYTHONPATH=src $(PYTHON) examples/verify_rag_output.py
	PYTHONPATH=src $(PYTHON) -m citecheck examples/sample_payload.json --json

loc:
	@lines=$$(cat $(SRC)/*.py 2>/dev/null | wc -l | tr -d ' '); \
	if [ -z "$$lines" ]; then lines=0; fi; \
	echo "src/citecheck LOC: $$lines / $(LOC_LIMIT)"; \
	if [ "$$lines" -ge "$(LOC_LIMIT)" ]; then \
		echo "ERROR: core LOC $$lines exceeds limit $(LOC_LIMIT)"; \
		exit 1; \
	fi
