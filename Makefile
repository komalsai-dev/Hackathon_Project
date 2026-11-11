.PHONY: setup generate validate test api clean

PYTHON ?= python

setup:
	$(PYTHON) -m pip install -r requirements.txt

generate:
	$(PYTHON) -m backend.generator.run --scale starter

generate-full:
	$(PYTHON) -m backend.generator.run --scale full

validate:
	$(PYTHON) -m backend.validation.validate

test:
	$(PYTHON) -m pytest backend/tests/ -v

api:
	$(PYTHON) -m backend.api.main

clean:
	$(PYTHON) -c "import shutil, os; [shutil.rmtree(p, ignore_errors=True) for p in ['data/output', 'data/ground_truth', '.pytest_cache', '__pycache__']]"
