.PHONY: install
install:
	poetry install

.PHONY: compile
compile:
	poetry run flake8
	poetry run pyright
