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
        "rect": [
            100.0,
            100.0,
            420.0,
            200.0
        ],
        "boxes": [
            {
                "box": {
                    "id": "obj-1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 2,
                    "outlettype": [
                        "",
                        ""
                    ],
                    "patching_rect": [
                        20.0,
                        20.0,
                        80.0,
                        22.0
                    ],
                    "text": "patcherargs"
                }
            },
            {
                "box": {
                    "id": "obj-2",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [
                        20.0,
                        60.0,
                        370.0,
                        22.0
                    ],
                    "text": "v8 bachmcp.bpatcher.replace.js bachmcp.bpatcher.generator 288 365"
                }
            },
            {
                "box": {
                    "id": "obj-3",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [
                        20.0,
                        100.0,
                        380.0,
                        47.0
                    ],
                    "linecount": 3,
                    "text": "[bachmcp.generator t1] becomes [bpatcher @name bachmcp.bpatcher.generator @args t1]: typed arguments go to @args (bachmcp.bpatcher.replace.js)."
                }
            },
            {
                "box": {
                    "comment": "Max lists a patcher as an object only if it has an inlet or an outlet",
                    "id": "obj-4",
                    "index": 1,
                    "maxclass": "inlet",
                    "numinlets": 0,
                    "numoutlets": 1,
                    "outlettype": [
                        ""
                    ],
                    "patching_rect": [
                        340.0,
                        20.0,
                        30.0,
                        30.0
                    ]
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [
                        "obj-2",
                        0
                    ],
                    "source": [
                        "obj-1",
                        0
                    ]
                }
            }
        ]
    }
}
