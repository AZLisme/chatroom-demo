all:
	@echo a experimental online chat room.
	@echo try targets: install compile run

install:
	npm install
	pip install -r requirements.txt

compile:
	npm run dist

run:
	python main.py