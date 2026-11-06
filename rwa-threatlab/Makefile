.PHONY: install test demo report clean
install:
	python -m pip install -e ".[dev]"
test:
	python -m pytest -q
demo:
	python -m rwa_threatlab all --details
report:
	python -m rwa_threatlab all --out docs/results
clean:
	rm -rf .pytest_cache build dist *.egg-info docs/results
