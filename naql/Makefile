.PHONY: setup run test lint eval

setup:
	pip install -e ".[dev]"

run:
	streamlit run app/main.py

test:
	pytest tests/unit -q

lint:
	ruff check naql_core app tests eval
	ruff format --check naql_core app tests eval
	mypy naql_core

eval:
	python eval/run_eval.py
