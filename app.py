"""Start myguro: flask --app app run --debug

The app itself is the myguro package (myguro/__init__.py: create_app).
"""

from myguro import create_app

app = create_app()
