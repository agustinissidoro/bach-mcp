"""Helpers around Bach, not its work: they answer people and Max, and fetch what Bach needs.

    status.py     what Bach tells Max about itself over UDP: bach status, settings,
                  models, catalog, download_model ... answered with server lines
    download.py   models into models/: by a name from models/catalog.toml, a Hugging Face
                  repo or a link; with progress, for the terminal and for Max

Used by the doors and the command line. Imports config.py and bridge/.
"""
