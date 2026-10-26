"""The local model: running it and talking to it. Only the local chat uses this; Claude brings its own.

    backends.py   starts and stops the model server: mlx (mlx_lm.server) or gguf (llama-server)
    client.py     the one client: a streaming chat request with tools, in the OpenAI format

Imports only config.py.
"""
