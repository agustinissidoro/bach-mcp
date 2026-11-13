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
                    "text": "js helpstarter bachmcp.gui.params"
                }
            },
            {
                "box": {
                    "border": 0,
                    "filename": "helpname.js",
                    "id": "obj-2",
                    "ignoreclick": 1,
                    "jsarguments": [
                        "bachmcp.gui.params"
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
                                        "bachmcp.gui.params"
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
                                    "text": "Connect a runner's panel outlet to it, and its outlet back to the runner. It builds itself from the algorithm the runner loads.",
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
                                    "maxclass": "newobj",
                                    "numinlets": 1,
                                    "numoutlets": 5,
                                    "outlettype": [
                                        "dictionary",
                                        "",
                                        "",
                                        "bang",
                                        ""
                                    ],
                                    "text": "bachmcp.algorithm help_params generator",
                                    "id": "obj-4",
                                    "patching_rect": [
                                        30.0,
                                        180.0,
                                        249.6,
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
                                    "id": "obj-5",
                                    "patching_rect": [
                                        30.0,
                                        225.0,
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
                                    "text": "Options: drags land on round values (alt lets one through), reset all, bypass, repeat, and the runner's source or selection.",
                                    "linecount": 2,
                                    "id": "obj-6",
                                    "patching_rect": [
                                        400.0,
                                        225.0,
                                        620.0,
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
                                    "text": "Parameters: one card each. Double-click a control: back to its declared value. Click a pitch's value: name, midicents or MIDI.",
                                    "linecount": 2,
                                    "id": "obj-7",
                                    "patching_rect": [
                                        400.0,
                                        270.0,
                                        620.0,
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
                                    "text": "It is saved with the patch. Give it a scripting name to store presets with pattr and pattrstorage.",
                                    "linecount": 2,
                                    "id": "obj-8",
                                    "patching_rect": [
                                        400.0,
                                        315.0,
                                        620.0,
                                        36.0
                                    ]
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-5",
                                        0
                                    ],
                                    "source": [
                                        "obj-4",
                                        2
                                    ]
                                }
                            },
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-4",
                                        0
                                    ],
                                    "source": [
                                        "obj-5",
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
                                        "bachmcp.gui.params"
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
                                    "text": "reset",
                                    "id": "obj-2",
                                    "patching_rect": [
                                        30.0,
                                        125.0,
                                        50.0,
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
                                    "text": "every parameter back to its declared value",
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
                                    "text": "bang",
                                    "id": "obj-4",
                                    "patching_rect": [
                                        30.0,
                                        155.0,
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
                                    "text": "send every value",
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
                                    "text": "clear",
                                    "id": "obj-6",
                                    "patching_rect": [
                                        30.0,
                                        185.0,
                                        50.0,
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
                                    "text": "forget the parameters",
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
                                    "text": "autosize 0",
                                    "id": "obj-8",
                                    "patching_rect": [
                                        30.0,
                                        215.0,
                                        88.0,
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
                                    "text": "0: keep its size. 1 (default): resize to the content",
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
                                    "text": "set_name my_panel",
                                    "id": "obj-10",
                                    "patching_rect": [
                                        30.0,
                                        245.0,
                                        141.2,
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
                                    "text": "the name drawn while no algorithm is loaded",
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
                                    "id": "obj-12",
                                    "patching_rect": [
                                        30.0,
                                        285.0,
                                        289.0,
                                        388.0
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
                                    "text": "print to_runner",
                                    "id": "obj-13",
                                    "patching_rect": [
                                        30.0,
                                        685.0,
                                        120.0,
                                        23.0
                                    ]
                                }
                            }
                        ],
                        "lines": [
                            {
                                "patchline": {
                                    "destination": [
                                        "obj-12",
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
                                        "obj-12",
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
                                        "obj-12",
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
                                        "obj-12",
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
                                        "obj-12",
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
                                        "obj-13",
                                        0
                                    ],
                                    "source": [
                                        "obj-12",
                                        0
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
