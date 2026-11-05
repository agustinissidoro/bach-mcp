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
                    "text": "js helpstarter bachmcp.prompt"
                }
            },
            {
                "box": {
                    "border": 0,
                    "filename": "helpname.js",
                    "id": "obj-2",
                    "ignoreclick": 1,
                    "jsarguments": [
                        "bachmcp.prompt"
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
                                        "bachmcp.prompt"
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
                                    "text": "Click it and type. Enter sends, Shift+Enter is a new line. After sending, the text stays dimmed: click it again to edit.",
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
                                    "id": "obj-3",
                                    "patching_rect": [
                                        30.0,
                                        150.0,
                                        420.0,
                                        140.0
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
                                    "text": "print prompt",
                                    "id": "obj-4",
                                    "patching_rect": [
                                        30.0,
                                        305.0,
                                        98.4,
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
                                    "text": "The whole text leaves as one symbol, whatever it contains, so an instance gets it as one prompt. Connect it to any bachmcp.generator, transformer or selector.",
                                    "linecount": 2,
                                    "id": "obj-5",
                                    "patching_rect": [
                                        30.0,
                                        340.0,
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
                                    "text": "Keys: arrows (Alt: by word, Cmd: line start or end), Shift+arrows select, Cmd+A / C / X / V / Z, Escape leaves the box. Double-click selects a word.",
                                    "linecount": 2,
                                    "id": "obj-6",
                                    "patching_rect": [
                                        30.0,
                                        395.0,
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
                                        "obj-4",
                                        0
                                    ],
                                    "source": [
                                        "obj-3",
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
                                        "bachmcp.prompt"
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
                                    "text": "send what is typed",
                                    "id": "obj-3",
                                    "patching_rect": [
                                        320.0,
                                        125.0,
                                        700.0,
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
                                    "text": "set a scale that turns around",
                                    "id": "obj-4",
                                    "patching_rect": [
                                        30.0,
                                        155.0,
                                        232.39999999999998,
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
                                    "text": "replace the text, without sending",
                                    "id": "obj-5",
                                    "patching_rect": [
                                        320.0,
                                        155.0,
                                        700.0,
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
                                    "text": "append and comes back",
                                    "id": "obj-6",
                                    "patching_rect": [
                                        30.0,
                                        185.0,
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
                                    "text": "add to the end",
                                    "id": "obj-7",
                                    "patching_rect": [
                                        320.0,
                                        185.0,
                                        700.0,
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
                                    "id": "obj-8",
                                    "patching_rect": [
                                        30.0,
                                        215.0,
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
                                    "text": "erase the text",
                                    "id": "obj-9",
                                    "patching_rect": [
                                        320.0,
                                        215.0,
                                        700.0,
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
                                    "text": "paste",
                                    "id": "obj-10",
                                    "patching_rect": [
                                        30.0,
                                        245.0,
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
                                    "text": "paste the clipboard at the caret",
                                    "id": "obj-11",
                                    "patching_rect": [
                                        320.0,
                                        245.0,
                                        700.0,
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
                                    "text": "autoheight 1",
                                    "id": "obj-12",
                                    "patching_rect": [
                                        30.0,
                                        275.0,
                                        103.19999999999999,
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
                                    "text": "grow with the text, up to maxheight, then scroll",
                                    "id": "obj-13",
                                    "patching_rect": [
                                        320.0,
                                        275.0,
                                        700.0,
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
                                    "text": "prepend_prompt_label 0",
                                    "id": "obj-14",
                                    "patching_rect": [
                                        30.0,
                                        305.0,
                                        179.2,
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
                                    "text": "0: the text alone. 1 (default): prompt <text>",
                                    "id": "obj-15",
                                    "patching_rect": [
                                        320.0,
                                        305.0,
                                        700.0,
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
                                    "text": "placeholder \"What should it play?\"",
                                    "id": "obj-16",
                                    "patching_rect": [
                                        30.0,
                                        335.0,
                                        270.4,
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
                                    "text": "shown while empty",
                                    "id": "obj-17",
                                    "patching_rect": [
                                        320.0,
                                        335.0,
                                        700.0,
                                        21.0
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
                                    "id": "obj-18",
                                    "patching_rect": [
                                        30.0,
                                        375.0,
                                        420.0,
                                        120.0
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
                                    "text": "print prompt",
                                    "id": "obj-19",
                                    "patching_rect": [
                                        30.0,
                                        510.0,
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
