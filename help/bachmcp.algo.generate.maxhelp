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
                    "text": "js helpstarter bachmcp.algo.generate"
                }
            },
            {
                "box": {
                    "border": 0,
                    "filename": "helpname.js",
                    "id": "obj-2",
                    "ignoreclick": 1,
                    "jsarguments": [
                        "bachmcp.algo.generate"
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
                                        "bachmcp.algo.generate"
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
                                    "text": "Needs a bachmcp.server running in any open patch: it says where the playground is, and answers prompts.",
                                    "id": "obj-2",
                                    "patching_rect": [
                                        10.0,
                                        118.0,
                                        1000.0,
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
                                    "id": "obj-3",
                                    "patching_rect": [
                                        500.0,
                                        145.0,
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
                                    "id": "obj-4",
                                    "patching_rect": [
                                        500.0,
                                        195.0,
                                        330.0,
                                        90.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "Or write the file yourself: <playground>/algorithms/<instance name>.js. Saving it reloads it. 'open' shows it.",
                                    "linecount": 2,
                                    "id": "obj-5",
                                    "patching_rect": [
                                        500.0,
                                        295.0,
                                        540.0,
                                        36.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 3,
                                    "outlettype": [
                                        "dictionary",
                                        "",
                                        ""
                                    ],
                                    "text": "bachmcp.algo.generate help_generator",
                                    "id": "obj-6",
                                    "patching_rect": [
                                        30.0,
                                        300.0,
                                        271.2,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "text": "bachmcp.translate @from json @to llll",
                                    "id": "obj-7",
                                    "patching_rect": [
                                        30.0,
                                        355.0,
                                        278.40000000000003,
                                        23.0
                                    ]
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
                                    "id": "obj-8",
                                    "patching_rect": [
                                        30.0,
                                        410.0,
                                        420.0,
                                        118.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "border": 0,
                                    "embed": 0,
                                    "filename": "bachmcp.gui.params.v8ui.js",
                                    "maxclass": "v8ui",
                                    "numinlets": 1,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "parameter_enable": 0,
                                    "textfile": {
                                        "filename": "bachmcp.gui.params.v8ui.js",
                                        "flags": 0,
                                        "embed": 0,
                                        "autowatch": 1
                                    },
                                    "id": "obj-9",
                                    "patching_rect": [
                                        500.0,
                                        350.0,
                                        289.0,
                                        388.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "score out as a dictionary, through bachmcp.translate, into the roll",
                                    "linecount": 2,
                                    "id": "obj-10",
                                    "patching_rect": [
                                        30.0,
                                        535.0,
                                        440.0,
                                        36.0
                                    ]
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-6",
                                        0
                                    ],
                                    "source": [
                                        "obj-4",
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
                                        "obj-9",
                                        0
                                    ],
                                    "source": [
                                        "obj-6",
                                        1
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-6",
                                        0
                                    ],
                                    "source": [
                                        "obj-9",
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
                                        "bachmcp.algo.generate"
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
                                    "maxclass": "message",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "text": "bang",
                                    "id": "obj-2",
                                    "patching_rect": [
                                        30.0,
                                        125.0,
                                        42.4,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "run with the current parameters",
                                    "id": "obj-3",
                                    "patching_rect": [
                                        240.0,
                                        125.0,
                                        780.0,
                                        21.0
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
                                    "text": "write_to_playground",
                                    "id": "obj-4",
                                    "patching_rect": [
                                        30.0,
                                        155.0,
                                        156.4,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "write the last score to <playground>/scores/<name>.json",
                                    "id": "obj-5",
                                    "patching_rect": [
                                        240.0,
                                        155.0,
                                        780.0,
                                        21.0
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
                                    "text": "open",
                                    "id": "obj-6",
                                    "patching_rect": [
                                        30.0,
                                        185.0,
                                        42.4,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "open the algorithm's code",
                                    "id": "obj-7",
                                    "patching_rect": [
                                        240.0,
                                        185.0,
                                        780.0,
                                        21.0
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
                                    "text": "snap 1",
                                    "id": "obj-8",
                                    "patching_rect": [
                                        30.0,
                                        215.0,
                                        57.599999999999994,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "output pitches: 0 semitones, 1 quarter tones, 3 free",
                                    "id": "obj-9",
                                    "patching_rect": [
                                        240.0,
                                        215.0,
                                        780.0,
                                        21.0
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
                                    "text": "bypass 1",
                                    "id": "obj-10",
                                    "patching_rect": [
                                        30.0,
                                        245.0,
                                        72.8,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "1: runs do nothing, and a score in goes straight out",
                                    "id": "obj-11",
                                    "patching_rect": [
                                        240.0,
                                        245.0,
                                        780.0,
                                        21.0
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
                                    "text": "repeat",
                                    "id": "obj-12",
                                    "patching_rect": [
                                        30.0,
                                        275.0,
                                        57.599999999999994,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "the last output again",
                                    "id": "obj-13",
                                    "patching_rect": [
                                        240.0,
                                        275.0,
                                        780.0,
                                        21.0
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
                                    "text": "verbose 1",
                                    "id": "obj-14",
                                    "patching_rect": [
                                        30.0,
                                        305.0,
                                        80.39999999999999,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "say in the Max console what happens",
                                    "id": "obj-15",
                                    "patching_rect": [
                                        240.0,
                                        305.0,
                                        780.0,
                                        21.0
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
                                    "text": "auto_dump 0",
                                    "id": "obj-16",
                                    "patching_rect": [
                                        30.0,
                                        335.0,
                                        95.6,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "0: only bang runs it. 1 (default): every parameter change does",
                                    "id": "obj-17",
                                    "patching_rect": [
                                        240.0,
                                        335.0,
                                        780.0,
                                        21.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 3,
                                    "outlettype": [
                                        "dictionary",
                                        "",
                                        ""
                                    ],
                                    "text": "bachmcp.algo.generate help_generator",
                                    "id": "obj-18",
                                    "patching_rect": [
                                        30.0,
                                        375.0,
                                        271.2,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "text": "print score",
                                    "id": "obj-19",
                                    "patching_rect": [
                                        30.0,
                                        435.0,
                                        91.2,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "text": "print panel",
                                    "id": "obj-20",
                                    "patching_rect": [
                                        160.0,
                                        435.0,
                                        91.2,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "outlettype": [],
                                    "text": "print status",
                                    "id": "obj-21",
                                    "patching_rect": [
                                        290.0,
                                        435.0,
                                        98.4,
                                        23.0
                                    ]
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-18",
                                        0
                                    ],
                                    "source": [
                                        "obj-2",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-18",
                                        0
                                    ],
                                    "source": [
                                        "obj-4",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-18",
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
                                        "obj-18",
                                        0
                                    ],
                                    "source": [
                                        "obj-8",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-18",
                                        0
                                    ],
                                    "source": [
                                        "obj-10",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-18",
                                        0
                                    ],
                                    "source": [
                                        "obj-12",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-18",
                                        0
                                    ],
                                    "source": [
                                        "obj-14",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-18",
                                        0
                                    ],
                                    "source": [
                                        "obj-16",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-19",
                                        0
                                    ],
                                    "source": [
                                        "obj-18",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-20",
                                        0
                                    ],
                                    "source": [
                                        "obj-18",
                                        1
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-21",
                                        0
                                    ],
                                    "source": [
                                        "obj-18",
                                        2
                                    ]
                                }
                            }
                        ]
                    },
                    "patching_rect": [
                        150.0,
                        205.0,
                        104.0,
                        22.0
                    ],
                    "text": "p messages"
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
                        "boxes": [
                            {
                                "box": {
                                    "border": 0,
                                    "filename": "helpdetails.js",
                                    "ignoreclick": 1,
                                    "jsarguments": [
                                        "bachmcp.algo.generate"
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
                                    "text": "An algorithm is a JavaScript file: its parameters, then function produce(p).",
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
                                    "text": "const params = {\n  times: { type: \"slider\", range: [1, 64], value: 16 },\n  seed:  { type: \"seed\", value: 1 },\n};\n\nfunction produce(p) {\n  const s = score();\n  const v = s.voice(\"Flute\");\n  const r = rng(\"pitch\");\n  for (let i = 0; i < p.times; i++) v.note(i * 250, r.int(6000, 8400), 250);\n  return s;\n}",
                                    "fontname": "Menlo",
                                    "linecount": 12,
                                    "id": "obj-3",
                                    "patching_rect": [
                                        10.0,
                                        155.0,
                                        640.0,
                                        186.0
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
                                        350.0,
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
                                        375.0,
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
                                        400.0,
                                        900.0,
                                        21.0
                                    ]
                                }
                            }
                        ],
                        "lines": []
                    },
                    "patching_rect": [
                        290.0,
                        205.0,
                        152.0,
                        22.0
                    ],
                    "text": "p own algorithms"
                }
            },
            {
                "box": {
                    "id": "obj-6",
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
                        430.0,
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
