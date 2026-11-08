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
                    "text": "js helpstarter bachmcp.algo.select"
                }
            },
            {
                "box": {
                    "border": 0,
                    "filename": "helpname.js",
                    "id": "obj-2",
                    "ignoreclick": 1,
                    "jsarguments": [
                        "bachmcp.algo.select"
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
                                        "bachmcp.algo.select"
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
                                        145.0,
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
                                        210.0,
                                        420.0,
                                        118.0
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
                                    "text": "bachmcp.translate @from llll @to json",
                                    "id": "obj-8",
                                    "patching_rect": [
                                        30.0,
                                        345.0,
                                        278.40000000000003,
                                        23.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 4,
                                    "outlettype": [
                                        "dictionary",
                                        "",
                                        "",
                                        ""
                                    ],
                                    "text": "bachmcp.algo.select help_selector",
                                    "id": "obj-9",
                                    "patching_rect": [
                                        30.0,
                                        395.0,
                                        249.6,
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
                                    "id": "obj-10",
                                    "patching_rect": [
                                        30.0,
                                        450.0,
                                        278.40000000000003,
                                        23.0
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
                                    "id": "obj-11",
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
                                    "id": "obj-12",
                                    "patching_rect": [
                                        30.0,
                                        530.0,
                                        420.0,
                                        118.0
                                    ]
                                }
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "the second outlet sends dump, clearselection and sel note to the first roll. The selected notes go to the second one.",
                                    "linecount": 2,
                                    "id": "obj-13",
                                    "patching_rect": [
                                        30.0,
                                        485.0,
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
                                        "obj-8",
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
                                        "obj-9",
                                        1
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-11",
                                        0
                                    ],
                                    "source": [
                                        "obj-9",
                                        2
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
                                        "obj-11",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-10",
                                        0
                                    ],
                                    "source": [
                                        "obj-9",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-12",
                                        0
                                    ],
                                    "source": [
                                        "obj-10",
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
                                        "bachmcp.algo.select"
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
                                    "maxclass": "message",
                                    "numinlets": 2,
                                    "numoutlets": 1,
                                    "outlettype": [
                                        ""
                                    ],
                                    "text": "source_mode 0",
                                    "id": "obj-18",
                                    "patching_rect": [
                                        30.0,
                                        365.0,
                                        110.8,
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
                                    "text": "0 destructive: every run asks the roll for its score",
                                    "id": "obj-19",
                                    "patching_rect": [
                                        240.0,
                                        365.0,
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
                                    "text": "capture",
                                    "id": "obj-20",
                                    "patching_rect": [
                                        30.0,
                                        395.0,
                                        118.39999999999999,
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
                                    "text": "the next score in becomes the source",
                                    "id": "obj-21",
                                    "patching_rect": [
                                        240.0,
                                        395.0,
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
                                    "text": "dump_selection_only 0",
                                    "id": "obj-22",
                                    "patching_rect": [
                                        30.0,
                                        425.0,
                                        171.6,
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
                                    "text": "left outlet: the whole source, flagged. 1 (default): only the selected notes",
                                    "id": "obj-23",
                                    "patching_rect": [
                                        240.0,
                                        425.0,
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
                                    "text": "dump_selection",
                                    "id": "obj-24",
                                    "patching_rect": [
                                        30.0,
                                        455.0,
                                        118.39999999999999,
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
                                    "text": "output the selected notes as a score",
                                    "id": "obj-25",
                                    "patching_rect": [
                                        240.0,
                                        455.0,
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
                                    "text": "clear_selection",
                                    "id": "obj-26",
                                    "patching_rect": [
                                        30.0,
                                        485.0,
                                        126.0,
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
                                    "text": "select nothing",
                                    "id": "obj-27",
                                    "patching_rect": [
                                        240.0,
                                        485.0,
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
                                    "numoutlets": 4,
                                    "outlettype": [
                                        "dictionary",
                                        "",
                                        "",
                                        ""
                                    ],
                                    "text": "bachmcp.algo.select help_selector",
                                    "id": "obj-28",
                                    "patching_rect": [
                                        30.0,
                                        525.0,
                                        249.6,
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
                                    "id": "obj-29",
                                    "patching_rect": [
                                        30.0,
                                        585.0,
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
                                    "text": "print to_roll",
                                    "id": "obj-30",
                                    "patching_rect": [
                                        160.0,
                                        585.0,
                                        105.60000000000001,
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
                                    "id": "obj-31",
                                    "patching_rect": [
                                        290.0,
                                        585.0,
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
                                    "id": "obj-32",
                                    "patching_rect": [
                                        420.0,
                                        585.0,
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
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
                                        "obj-28",
                                        0
                                    ],
                                    "source": [
                                        "obj-20",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-28",
                                        0
                                    ],
                                    "source": [
                                        "obj-22",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-28",
                                        0
                                    ],
                                    "source": [
                                        "obj-24",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-28",
                                        0
                                    ],
                                    "source": [
                                        "obj-26",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-29",
                                        0
                                    ],
                                    "source": [
                                        "obj-28",
                                        0
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-30",
                                        0
                                    ],
                                    "source": [
                                        "obj-28",
                                        1
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-31",
                                        0
                                    ],
                                    "source": [
                                        "obj-28",
                                        2
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-32",
                                        0
                                    ],
                                    "source": [
                                        "obj-28",
                                        3
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
                                        "bachmcp.algo.select"
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
                                    "text": "An algorithm is a JavaScript file: its parameters, then function select(source, p).",
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
                                    "text": "const params = {\n  above: { type: \"slider\", range: [3600, 9600], value: 6500, unit: \"mc\" },\n};\n\nfunction select(source, p) {\n  const notes = [];\n  eachNote(source, (n) => { if (n.pitch >= p.above) notes.push(n); });\n  return notes;\n}",
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
                            },
                            {
                                "box": {
                                    "fontsize": 13.0,
                                    "maxclass": "comment",
                                    "numinlets": 1,
                                    "numoutlets": 0,
                                    "text": "select returns the notes it picks: the note objects of source, or their addresses [voice, chord, note], 1-based.",
                                    "id": "obj-7",
                                    "patching_rect": [
                                        10.0,
                                        380.0,
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
