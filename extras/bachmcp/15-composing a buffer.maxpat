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
        "rect": [ 34.0, 95.0, 1444.0, 853.0 ],
        "boxes": [
            {
                "box": {
                    "id": "obj-17",
                    "maxclass": "ezdac~",
                    "numinlets": 2,
                    "numoutlets": 0,
                    "patching_rect": [ 336.0, 907.0, 45.0, 45.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-16",
                    "lastchannelcount": 0,
                    "maxclass": "live.gain~",
                    "numinlets": 2,
                    "numoutlets": 5,
                    "outlettype": [ "signal", "signal", "", "float", "list" ],
                    "parameter_enable": 1,
                    "patching_rect": [ 336.0, 753.0, 48.0, 136.0 ],
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
                    "id": "obj-15",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "signal", "signal", "bang" ],
                    "patching_rect": [ 336.0, 701.0, 77.0, 22.0 ],
                    "text": "play~ toto 2"
                }
            },
            {
                "box": {
                    "id": "obj-14",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 887.0, 308.0, 217.0, 22.0 ],
                    "text": "done 0"
                }
            },
            {
                "box": {
                    "id": "obj-11",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 382.0, 598.0, 293.0, 22.0 ]
                }
            },
            {
                "box": {
                    "embed": 0,
                    "embedstate": [
                        [ "restore", "{\"title\":\"hello-sound\",\"description\":\"One voice becomes a crowd: copies of a single speaker enter one by one and drift apart in body, pitch, time and space.\",\"path\":\"Macintosh HD:/Users/agustin/Documents/GitHub/bach-mcp/playground/recipes/hello-sound.json\",\"type\":\"\",\"params\":[{\"name\":\"clones\",\"type\":\"slider\",\"range\":[4,64],\"step\":1,\"unit\":\"\",\"description\":\"How many copies of the speaker the crowd grows to.\",\"options\":null,\"value\":19,\"default\":32,\"kind\":\"\",\"grid\":1,\"display\":\"\"},{\"name\":\"length_ms\",\"type\":\"slider\",\"range\":[5000,30000],\"step\":1,\"unit\":\"ms\",\"description\":\"How long the voice takes to become a crowd.\",\"options\":null,\"value\":16000,\"default\":16000,\"kind\":\"time\",\"grid\":200,\"display\":\"\"},{\"name\":\"divergence\",\"type\":\"slider\",\"range\":[0,1],\"step\":0,\"unit\":\"\",\"description\":\"How far the copies drift from the original: 0 a tight unison choir of one person, 1 a crowd of strangers of every size and pitch, out of step.\",\"options\":null,\"value\":0.57,\"default\":0.6,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"arrival\",\"type\":\"slider\",\"range\":[0,1],\"step\":0,\"unit\":\"\",\"description\":\"How the copies arrive: low they flood in early, high the speaker stays alone a long time and the crowd forms late.\",\"options\":null,\"value\":0.5,\"default\":0.5,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"width\",\"type\":\"slider\",\"range\":[0,1],\"step\":0,\"unit\":\"\",\"description\":\"How wide the crowd spreads in stereo.\",\"options\":null,\"value\":0.9,\"default\":0.9,\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"variation\",\"type\":\"slider\",\"range\":[1,16],\"step\":1,\"unit\":\"\",\"description\":\"Another speaker, other copies.\",\"options\":null,\"value\":1,\"default\":1,\"kind\":\"\",\"grid\":1,\"display\":\"\"},{\"name\":\"seed\",\"type\":\"slider\",\"range\":[0,999],\"step\":1,\"unit\":\"\",\"options\":null,\"value\":0,\"default\":0,\"kind\":\"\",\"grid\":1,\"display\":\"\"}],\"snap\":true,\"sourceMode\":\"nondestructive\",\"involutive\":false,\"selectionOnly\":true,\"bypass\":false,\"autoDump\":true,\"mute\":false,\"withinSelection\":false,\"pitchSnap\":3,\"timeSnap\":0}" ]
                    ],
                    "filename": "bachmcp.gui.params.v8ui.js",
                    "id": "obj-6",
                    "maxclass": "v8ui",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 747.0, 357.0, 321.0, 604.0 ],
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
                    "id": "obj-12",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1389.0, 410.0, 150.0, 20.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-9",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1094.0, 135.0, 100.0, 22.0 ],
                    "text": "set hello-sound.1"
                }
            },
            {
                "box": {
                    "buffername": "hello-sound.1",
                    "id": "obj-5",
                    "maxclass": "waveform~",
                    "numinlets": 5,
                    "numoutlets": 6,
                    "outlettype": [ "float", "float", "float", "float", "list", "" ],
                    "patching_rect": [ 1094.0, 177.0, 256.0, 64.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-2",
                    "maxclass": "dict.view",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 168.0, 301.0, 242.0, 230.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-10",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 158.0, 185.0, 35.0, 22.0 ],
                    "text": "open"
                }
            },
            {
                "box": {
                    "color": [ 1.0, 1.0, 1.0, 1.0 ],
                    "fontface": 0,
                    "fontname": "Arial",
                    "id": "obj-8",
                    "maxclass": "bachmcp.prompt",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 656.0, 145.0, 420.0, 140.0 ],
                    "prompt_sent": 1,
                    "prompt_text": "a sound with a lot of layers, like a crowd"
                }
            },
            {
                "box": {
                    "id": "obj-4",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 656.0, 314.0, 200.0, 22.0 ],
                    "text": "bachmcp.soundrender~ hello-sound"
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
                    "patching_rect": [ 75.0, 180.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-1",
                    "linecount": 2,
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "dictionary", "" ],
                    "patching_rect": [ 75.0, 236.0, 205.0, 35.0 ],
                    "text": "bachmcp.server claude @model opus @effort medium"
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-2", 0 ],
                    "source": [ "obj-1", 1 ]
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
                    "destination": [ "obj-16", 1 ],
                    "source": [ "obj-15", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-16", 0 ],
                    "source": [ "obj-15", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-17", 1 ],
                    "source": [ "obj-16", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-17", 0 ],
                    "source": [ "obj-16", 0 ]
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
                    "destination": [ "obj-11", 1 ],
                    "source": [ "obj-4", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-14", 1 ],
                    "source": [ "obj-4", 2 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-6", 0 ],
                    "source": [ "obj-4", 1 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-4", 0 ],
                    "midpoints": [ 756.5, 968.171875, 627.5390625, 968.171875, 627.5390625, 301.8359375, 665.5, 301.8359375 ],
                    "source": [ "obj-6", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-4", 0 ],
                    "source": [ "obj-8", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-5", 0 ],
                    "source": [ "obj-9", 0 ]
                }
            }
        ],
        "parameters": {
            "obj-16": [ "live.gain~", "live.gain~", 0 ],
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