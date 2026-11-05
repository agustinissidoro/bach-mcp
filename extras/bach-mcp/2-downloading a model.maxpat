{
    "patcher": {
        "fileversion": 1,
        "appversion": {
            "major": 9,
            "minor": 2,
            "revision": 0,
            "architecture": "x64",
            "modernui": 1
        },
        "classnamespace": "box",
        "rect": [ 431.0, 161.0, 937.0, 780.0 ],
        "boxes": [
            {
                "box": {
                    "id": "obj-23",
                    "linecount": 3,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 568.0, 238.0, 277.0, 47.0 ],
                    "text": "to download a model from the catalog, use \"download [name]\". You can get the name using model_catalog (without the size!)"
                }
            },
            {
                "box": {
                    "id": "obj-22",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 403.0, 251.0, 156.0, 22.0 ],
                    "text": "download qwen3.8-27b-4bit"
                }
            },
            {
                "box": {
                    "id": "obj-20",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "bang" ],
                    "patching_rect": [ 300.0, 209.0, 58.0, 22.0 ],
                    "text": "loadbang"
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-16",
                    "linecount": 6,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 18.0, 32.0, 832.0, 87.0 ],
                    "text": "models are placed in /models folder.\nYou can download models using bachmcp.server, but you can also download your own or simply pass a full path to an existing model outside the /model folder\nThe local mode of bachmcp.server needs to be initialised with a @model [name or path] argument. Passing the model after initialisation is not possible.\nAcceptable formats are GGUF and MLX."
                }
            },
            {
                "box": {
                    "id": "obj-10",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 300.0, 251.0, 87.0, 22.0 ],
                    "text": "model_catalog"
                }
            },
            {
                "box": {
                    "id": "obj-7",
                    "linecount": 10,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 18.0, 170.0, 277.0, 141.0 ],
                    "text": "model_catalog will print models available in /models/catalog.toml\n\nThese are just illustrative examples, but we recommend getting the 27b model or bigger.\n\nThe catalog.toml is just a utility to download and load models easier. You can add your own entries to the catalog to load your model by name without passing a full path. "
                }
            },
            {
                "box": {
                    "id": "obj-6",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 547.0, 389.0, 32.0, 22.0 ],
                    "text": "print"
                }
            },
            {
                "box": {
                    "id": "obj-1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "dictionary", "" ],
                    "patching_rect": [ 300.0, 333.0, 266.0, 22.0 ],
                    "text": "bachmcp.server local @model qwen3.8-27b-4bit"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "source": [ "obj-1", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-1", 0 ],
                    "source": [ "obj-10", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-10", 0 ],
                    "source": [ "obj-20", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-1", 0 ],
                    "midpoints": [ 412.5, 319.0, 309.5, 319.0 ],
                    "source": [ "obj-22", 0 ]
                }
            }
        ],
        "autosave": 0
    }
}