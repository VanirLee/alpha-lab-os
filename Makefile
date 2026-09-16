PYTHON ?= python3

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -v

doctor:
	PYTHONPATH=src $(PYTHON) -m alpha_lab_os doctor

demo:
	PYTHONPATH=src $(PYTHON) -m alpha_lab_os demo --db data/demo.db --html artifacts/demo.html

collect-dry-run:
	PYTHONPATH=src $(PYTHON) -m alpha_lab_os collect --config configs/universe.json --db data/alpha_lab.db --dry-run
