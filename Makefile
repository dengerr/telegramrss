new_epub:
	uv run go.py subs.txt
	uv run to_epub.py subs.txt
start:
	uv run main.py
update:
	uv run go.py update >> $(shell date +%Y-%m-%d).md
