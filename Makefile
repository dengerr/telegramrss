start:
	uv run main.py
update:
	uv run go.py update >> $(shell date +%Y-%m-%d).md
