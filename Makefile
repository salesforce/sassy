.PHONY: install
install:
	poetry install

.PHONY: compile
compile:
	poetry run flake8
	poetry run pyright

.PHONY: update
update:
	poetry update

.PHONY: serve
run:
	poetry run main serve
