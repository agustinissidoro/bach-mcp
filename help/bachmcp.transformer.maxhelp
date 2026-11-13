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
            406.0,
            231.0,
            1069.0,
            853.0
        ],
        "showrootpatcherontab": 0,
        "autosave": 0,
        "boxes": [
            {
                "box": {
                    "id": "obj-1",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [
                        ""
                    ],
                    "patching_rect": [
                        10.0,
                        300.0,
                        209.0,
                        22.0
                    ],
                    "saved_object_attributes": {
                        "filename": "helpstarter",
                        "parameter_enable": 0
                    },
                    "text": "js helpstarter bachmcp.transformer"
                }
            },
            {
                "box": {
                    "border": 0,
                    "filename": "helpname.js",
                    "id": "obj-2",
                    "ignoreclick": 1,
                    "jsarguments": [
                        "bachmcp.transformer"
                    ],
                    "maxclass": "jsui",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [
                        ""
                    ],
                    "parameter_enable": 0,
                    "patching_rect": [
                        10.0,
                        10.0,
                        300.0,
                        57.6
                    ]
                }
            },
            {
                "box": {
                    "id": "obj-3",
                    "maxclass": "newobj",
                    "numinlets": 0,
                    "numoutlets": 0,
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
                            406.0,
                            257.0,
                            1069.0,
                            827.0
                        ],
                        "showontab": 1,
                        "boxes": [
                            {
                                "box": {
                                    "border": 0,
                                    "filename": "helpdetails.js",
                                    "ignoreclick": 1,
                                    "jsarguments": [
                                        "bachmcp.transformer"
                                    ],
                                    "maxclass": "jsui",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "parameter_enable": 0,
                                    "id": "obj-1",
                                    "patching_rect": [
                                        10.0,
                                        10.0,
                                        1040.0,
                                        100.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "Type [bachmcp.transformer <name>] in a box and it replaces itself with this bpatcher, ready to connect.",
                                    "id": "obj-2",
                                    "patching_rect": [
                                        10.0,
                                        118.0,
                                        1040.0,
                                        21.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "Needs a bachmcp.server running in any open patch: it says where the playground is, and answers prompts.",
                                    "id": "obj-3",
                                    "patching_rect": [
                                        10.0,
                                        145.0,
                                        1040.0,
                                        21.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "1. Start a bachmcp.server, then type here and press Enter. The model, local or Claude, writes the algorithm and it loads by itself.",
                                    "linecount": 2,
                                    "id": "obj-4",
                                    "patching_rect": [
                                        500.0,
                                        170.0,
                                        540.0,
                                        36.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "color": [
                                        1.0,
                                        1.0,
                                        1.0,
                                        1.0
                                    ],
                                    "fontface": 0,
                                    "fontname": "Arial",
                                    "maxclass": "bachmcp.prompt",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "id": "obj-5",
                                    "patching_rect": [
                                        500.0,
                                        220.0,
                                        330.0,
                                        80.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "message",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "text": "clear, addchord [0 [6000 500 100]], addchord [500 [6400 500 100]], addchord [1000 [6700 500 100]], addchord [1500 [7200 500 100]]",
                                    "id": "obj-6",
                                    "patching_rect": [
                                        30.0,
                                        180.0,
                                        440.0,
                                        52.0
                                    ],
                                    "linecount": 3
                                }
                            },
                            {
                                "box": {
                                    "bwcompatibility": 80300,
                                    "defaultnoteslots": [
                                        "null"
                                    ],
                                    "fontface": 0,
                                    "fontname": "Arial",
                                    "fontsize": 12.0,
                                    "loop": [
                                        0.0,
                                        1000.0
                                    ],
                                    "maxclass": "bach.roll",
                                    "numinlets": 6,
                                    "numoutlets": 8,
                                    "numvoices": 1,
                                    "out": "nnnnnnn",
                                    "outlettype": [
                                        "",
                                        "",
                                        "",
                                        "",
                                        "",
                                        "",
                                        "",
                                        "bang"
                                    ],
                                    "pitcheditrange": [
                                        "null"
                                    ],
                                    "stafflines": [
                                        5
                                    ],
                                    "textcolor": [
                                        0.0,
                                        0.0,
                                        0.0,
                                        1.0
                                    ],
                                    "versionnumber": 80300,
                                    "voicenames": [
                                        "[",
                                        "]"
                                    ],
                                    "voicespacing": [
                                        0.0,
                                        17.0
                                    ],
                                    "id": "obj-7",
                                    "patching_rect": [
                                        30.0,
                                        245.0,
                                        420.0,
                                        118.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "args": [
                                        "help_transformer",
                                        "transformer"
                                    ],
                                    "bgmode": 0,
                                    "border": 0,
                                    "clickthrough": 0,
                                    "enablehscroll": 0,
                                    "enablevscroll": 0,
                                    "lockeddragscroll": 0,
                                    "lockedsize": 0,
                                    "maxclass": "bpatcher",
                                    "name": "bachmcp.bpatcher.algorithm.maxpat",
                                    "numinlets": 1,
                                    "numoutlets": 3,
                                    "offset": [
                                        0.0,
                                        0.0
                                    ],
                                    "outlettype": [
                                        "",
                                        "bang",
                                        ""
                                    ],
                                    "viewvisibility": 1,
                                    "id": "obj-8",
                                    "patching_rect": [
                                        500.0,
                                        310.0,
                                        288.0,
                                        365.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "connect it to the roll both ways: the roll's first outlet to its inlet, its outlet to the roll's first inlet",
                                    "linecount": 2,
                                    "id": "obj-9",
                                    "patching_rect": [
                                        30.0,
                                        375.0,
                                        440.0,
                                        36.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "Everything bachmcp.algorithm takes also works here: see its reference page.",
                                    "id": "obj-10",
                                    "patching_rect": [
                                        500.0,
                                        685.0,
                                        540.0,
                                        21.0
                                    ]
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-7",
                                        0
                                    ],
                                    "source": [
                                        "obj-6",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-8",
                                        0
                                    ],
                                    "source": [
                                        "obj-7",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-8",
                                        0
                                    ],
                                    "source": [
                                        "obj-5",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-7",
                                        0
                                    ],
                                    "source": [
                                        "obj-8",
                                        0
                                    ]
                                }
                            }
                        ]
                    },
                    "patching_rect": [
                        10.0,
                        205.0,
                        80.0,
                        22.0
                    ],
                    "text": "p basic",
                    "varname": "basic_tab"
                }
            },
            {
                "box": {
                    "id": "obj-4",
                    "maxclass": "newobj",
                    "numinlets": 0,
                    "numoutlets": 0,
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
                            0.0,
                            26.0,
                            1069.0,
                            827.0
                        ],
                        "showontab": 1,
                        "boxes": [
                            {
                                "box": {
                                    "border": 0,
                                    "filename": "helpdetails.js",
                                    "ignoreclick": 1,
                                    "jsarguments": [
                                        "bachmcp.transformer"
                                    ],
                                    "maxclass": "jsui",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "parameter_enable": 0,
                                    "id": "obj-1",
                                    "patching_rect": [
                                        10.0,
                                        10.0,
                                        1040.0,
                                        100.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "An algorithm is a JavaScript file: its parameters, then function transform(source, p).",
                                    "id": "obj-2",
                                    "patching_rect": [
                                        10.0,
                                        125.0,
                                        900.0,
                                        21.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 12.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "const params = {\n  shift: { type: \"slider\", range: [-1200, 1200], value: 700, unit: \"mc\" },\n};\n\nfunction transform(source, p) {\n  const out = copy(source);\n  eachNote(out, (n) => { n.pitch += p.shift; });\n  return out;\n}",
                                    "fontname": "Menlo",
                                    "linecount": 9,
                                    "id": "obj-3",
                                    "patching_rect": [
                                        10.0,
                                        155.0,
                                        640.0,
                                        141.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "Types: slider, range, toggle, menu, seed, curve, list. Pitches in midicents, times in ms.",
                                    "id": "obj-4",
                                    "patching_rect": [
                                        10.0,
                                        305.0,
                                        900.0,
                                        21.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "Library in scope: javascript/algorithmic_core_library (bachmcp.lib.index.js lists it).",
                                    "id": "obj-5",
                                    "patching_rect": [
                                        10.0,
                                        330.0,
                                        900.0,
                                        21.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "File: <playground>/algorithms/<instance name>.js. Saving the file reloads it.",
                                    "id": "obj-6",
                                    "patching_rect": [
                                        10.0,
                                        355.0,
                                        900.0,
                                        21.0
                                    ]
                                }
                            }
                        ],
                        "lines": []
                    },
                    "patching_rect": [
                        150.0,
                        205.0,
                        152.0,
                        22.0
                    ],
                    "text": "p own algorithms"
                }
            },
            {
                "box": {
                    "id": "obj-5",
                    "maxclass": "newobj",
                    "numinlets": 0,
                    "numoutlets": 0,
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
                            0.0,
                            26.0,
                            1069.0,
                            827.0
                        ],
                        "showontab": 1,
                        "boxes": [],
                        "lines": []
                    },
                    "patching_rect": [
                        290.0,
                        205.0,
                        48.0,
                        22.0
                    ],
                    "text": "p ?",
                    "varname": "q_tab"
                }
            }
        ],
        "lines": []
    }
}
