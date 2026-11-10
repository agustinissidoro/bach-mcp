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
        "rect": [ 34.0, 92.0, 1531.0, 954.0 ],
        "boxes": [
            {
                "box": {
                    "id": "obj-9",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1093.0, 349.0, 35.0, 22.0 ],
                    "text": "open"
                }
            },
            {
                "box": {
                    "data": {
                        "clips": [
                            {
                                "absolutepath": "eroica.aiff",
                                "filename": "eroica.aiff",
                                "filekind": "audiofile",
                                "id": "u331001290",
                                "loop": 1,
                                "content_state": {
                                    "loop": 1
                                }
                            }
                        ]
                    },
                    "id": "obj-4",
                    "maxclass": "playlist~",
                    "mode": "basic",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "signal", "signal", "signal", "", "dictionary" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1414.0, 321.0, 150.0, 30.0 ],
                    "quality": "basic",
                    "saved_attribute_attributes": {
                        "candicane2": {
                            "expression": ""
                        },
                        "candicane3": {
                            "expression": ""
                        },
                        "candicane4": {
                            "expression": ""
                        },
                        "candicane5": {
                            "expression": ""
                        },
                        "candicane6": {
                            "expression": ""
                        },
                        "candicane7": {
                            "expression": ""
                        },
                        "candicane8": {
                            "expression": ""
                        }
                    }
                }
            },
            {
                "box": {
                    "id": "obj-15",
                    "lastchannelcount": 0,
                    "maxclass": "live.gain~",
                    "numinlets": 2,
                    "numoutlets": 5,
                    "outlettype": [ "signal", "signal", "", "float", "list" ],
                    "parameter_enable": 1,
                    "patching_rect": [ 1155.0, 434.0, 48.0, 136.0 ],
                    "saved_attribute_attributes": {
                        "valueof": {
                            "parameter_longname": "live.gain~",
                            "parameter_mmax": 6.0,
                            "parameter_mmin": -70.0,
                            "parameter_modmode": 3,
                            "parameter_shortname": "live.gain~",
                            "parameter_type": 0,
                            "parameter_unitstyle": 4
                        }
                    },
                    "varname": "live.gain~"
                }
            },
            {
                "box": {
                    "color": [ 1.0, 1.0, 1.0, 1.0 ],
                    "fontface": 0,
                    "fontname": "Arial",
                    "id": "obj-14",
                    "maxclass": "bachmcp.prompt",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1155.0, 161.0, 420.0, 140.0 ],
                    "prompt_sent": 1,
                    "prompt_text": "generate a spectral delay with fft with at least 5 bands of control"
                }
            },
            {
                "box": {
                    "embed": 0,
                    "embedstate": [
                        [ "restore", "{\"title\":\"spectral-delay\",\"description\":\"FFT spectral delay: six bands set echo time and feedback across the spectrum.\",\"path\":\"Macintosh HD:/Users/agustin/Documents/GitHub/bach-mcp/playground/gen/spectral-delay.json\",\"type\":\"\",\"params\":[{\"name\":\"time1\",\"type\":\"slider\",\"range\":[10,1300],\"step\":1,\"unit\":\"ms\",\"options\":null,\"value\":93,\"default\":600,\"kind\":\"time\",\"grid\":10,\"display\":\"\"},{\"name\":\"time2\",\"type\":\"slider\",\"range\":[10,1300],\"step\":1,\"unit\":\"ms\",\"options\":null,\"value\":101,\"default\":450,\"kind\":\"time\",\"grid\":10,\"display\":\"\"},{\"name\":\"time3\",\"type\":\"slider\",\"range\":[10,1300],\"step\":1,\"unit\":\"ms\",\"options\":null,\"value\":300,\"default\":300,\"kind\":\"time\",\"grid\":10,\"display\":\"\"},{\"name\":\"time4\",\"type\":\"slider\",\"range\":[10,1300],\"step\":1,\"unit\":\"ms\",\"options\":null,\"value\":200,\"default\":200,\"kind\":\"time\",\"grid\":10,\"display\":\"\"},{\"name\":\"time5\",\"type\":\"slider\",\"range\":[10,1300],\"step\":1,\"unit\":\"ms\",\"options\":null,\"value\":350,\"default\":350,\"kind\":\"time\",\"grid\":10,\"display\":\"\"},{\"name\":\"time6\",\"type\":\"slider\",\"range\":[10,1300],\"step\":1,\"unit\":\"ms\",\"options\":null,\"value\":800,\"default\":800,\"kind\":\"time\",\"grid\":10,\"display\":\"\"},{\"name\":\"feedback1\",\"type\":\"slider\",\"range\":[0,0.95],\"step\":0.01,\"unit\":\"\",\"options\":null,\"value\":0.4,\"default\":0.4,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"feedback2\",\"type\":\"slider\",\"range\":[0,0.95],\"step\":0.01,\"unit\":\"\",\"options\":null,\"value\":0.5,\"default\":0.5,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"feedback3\",\"type\":\"slider\",\"range\":[0,0.95],\"step\":0.01,\"unit\":\"\",\"options\":null,\"value\":0.8,\"default\":0.45,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"feedback4\",\"type\":\"slider\",\"range\":[0,0.95],\"step\":0.01,\"unit\":\"\",\"options\":null,\"value\":0.75,\"default\":0.55,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"feedback5\",\"type\":\"slider\",\"range\":[0,0.95],\"step\":0.01,\"unit\":\"\",\"options\":null,\"value\":0.6,\"default\":0.6,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"feedback6\",\"type\":\"slider\",\"range\":[0,0.95],\"step\":0.01,\"unit\":\"\",\"options\":null,\"value\":0.61,\"default\":0.7,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"wet\",\"type\":\"slider\",\"range\":[0,1],\"step\":0.01,\"unit\":\"\",\"options\":null,\"value\":0.55,\"default\":0.5,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"}],\"snap\":true,\"sourceMode\":\"nondestructive\",\"involutive\":false,\"selectionOnly\":true,\"bypass\":false,\"withinSelection\":false,\"pitchSnap\":3,\"timeSnap\":0}" ]
                    ],
                    "filename": "bachmcp.gui.params.v8ui.js",
                    "id": "obj-13",
                    "maxclass": "v8ui",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 1258.0, 428.0, 329.0, 818.0 ],
                    "presentation": 1,
                    "presentation_rect": [ 0.0, 0.0, 64.0, 64.0 ],
                    "textfile": {
                        "filename": "bachmcp.gui.params.v8ui.js",
                        "flags": 0,
                        "embed": 0,
                        "autowatch": 1
                    }
                }
            },
            {
                "box": {
                    "id": "obj-8",
                    "maxclass": "newobj",
                    "numinlets": 2,
                    "numoutlets": 3,
                    "outlettype": [ "signal", "", "" ],
                    "patching_rect": [ 1155.0, 357.0, 181.0, 22.0 ],
                    "text": "bachmcp.audio spectral-delay fx"
                }
            },
            {
                "box": {
                    "id": "obj-7",
                    "maxclass": "ezdac~",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "patching_rect": [ 1155.0, 630.0, 45.0, 45.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-6",
                    "maxclass": "dict.view",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 195.5, 416.0, 228.0, 199.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-3",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 69.0, 256.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-1",
                    "linecount": 3,
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "dictionary", "" ],
                    "patching_rect": [ 69.0, 317.0, 272.0, 49.0 ],
                    "text": "bachmcp.server claude @profile minimal-electronic-composer @model opus @effort medium"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "source": [ "obj-1", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-8", 0 ],
                    "source": [ "obj-13", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-8", 0 ],
                    "source": [ "obj-14", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-7", 1 ],
                    "source": [ "obj-15", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-7", 0 ],
                    "source": [ "obj-15", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-1", 0 ],
                    "source": [ "obj-3", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-8", 1 ],
                    "source": [ "obj-4", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-13", 0 ],
                    "source": [ "obj-8", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-15", 1 ],
                    "order": 0,
                    "source": [ "obj-8", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-15", 0 ],
                    "order": 1,
                    "source": [ "obj-8", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-8", 0 ],
                    "source": [ "obj-9", 0 ]
                }
            }
        ],
        "parameters": {
            "obj-15": [ "live.gain~", "live.gain~", 0 ],
            "parameterbanks": {
                "0": {
                    "index": 0,
                    "name": "",
                    "parameters": [ "-", "-", "-", "-", "-", "-", "-", "-" ],
                    "buttons": [ "-", "-", "-", "-", "-", "-", "-", "-" ]
                }
            },
            "inherited_shortname": 1
        },
        "autosave": 0
    }
}