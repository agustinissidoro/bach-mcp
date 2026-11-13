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
        "bglocked": 1,
        "boxes": [
            {
                "box": {
                    "id": "obj-5",
                    "maxclass": "preset",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "preset", "int", "preset", "int", "" ],
                    "patching_rect": [ 255.0, 732.0, 100.0, 40.0 ],
                    "preset_data": [
                        {
                            "number": 1,
                            "data": [ 5, "obj-1", "bachmcp.prompt", "set", "don't forget about me" ]
                        },
                        {
                            "number": 2,
                            "data": [ 5, "obj-1", "bachmcp.prompt", "set", "remember me too!" ]
                        }
                    ]
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-32",
                    "linecount": 2,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1190.0, 168.0, 229.0, 33.0 ],
                    "text": "I WANT TO TALK TO THE MANAGER:\nLLM CHAT STYLE"
                }
            },
            {
                "box": {
                    "id": "obj-28",
                    "linecount": 4,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 682.0, 740.0, 188.0, 60.0 ],
                    "text": "The bachmcp.prompt object is just a utility to type easier. It already prepends the prompt message."
                }
            },
            {
                "box": {
                    "id": "obj-27",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "", "", "", "", "" ],
                    "patching_rect": [ 255.0, 970.0, 247.0, 22.0 ],
                    "text": "bachmcp.algorithm dont-prompt-him selector"
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-24",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 255.0, 699.0, 457.0, 20.0 ],
                    "text": "COMFORTABLE STYLE: I LIKE MAX, BUT LET ME SCROLL AND TYPE EASIER"
                }
            },
            {
                "box": {
                    "id": "obj-22",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 702.0, 305.0, 245.0, 20.0 ],
                    "text": "This is exactly the same, only without the UI."
                }
            },
            {
                "box": {
                    "id": "obj-18",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 702.0, 192.0, 281.0, 22.0 ],
                    "text": "an algorithm to select chords with major 5ths inside"
                }
            },
            {
                "box": {
                    "id": "obj-20",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 702.0, 232.0, 93.0, 22.0 ],
                    "text": "prepend prompt"
                }
            },
            {
                "box": {
                    "id": "obj-17",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 5,
                    "outlettype": [ "", "", "", "", "" ],
                    "patching_rect": [ 702.0, 269.0, 247.0, 22.0 ],
                    "text": "bachmcp.algorithm dont-prompt-him selector"
                }
            },
            {
                "box": {
                    "id": "obj-16",
                    "linecount": 2,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 344.0, 226.0, 224.0, 33.0 ],
                    "text": "just call the prompt function and use the prompt as an argument"
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-15",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 490.0, 155.0, 229.0, 20.0 ],
                    "text": "THE BADASS WAY, 100% MAX STYLE"
                }
            },
            {
                "box": {
                    "id": "obj-14",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 245.0, 192.0, 281.0, 22.0 ],
                    "text": "an algorithm to select chords with major 5ths inside"
                }
            },
            {
                "box": {
                    "id": "obj-12",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 245.0, 232.0, 93.0, 22.0 ],
                    "text": "prepend prompt"
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-8",
                    "linecount": 5,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 14.0, 18.0, 487.0, 74.0 ],
                    "text": "There are several ways to interface a prompt with bachmcp objects\n\n\n\n(...although in the end all of them are the same)"
                }
            },
            {
                "box": {
                    "id": "obj-2",
                    "linecount": 3,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1087.0, 436.0, 622.0, 47.0 ],
                    "text": "You can combine all uses, messages, bachmcp.chat and bachmcp.prompt, depending on your workflow and vibe ;)\nA full history will be kept in your playground in the /prompts folder, so the chat is constantly updated even if you prompt using the bachmcp.prompt object "
                }
            },
            {
                "box": {
                    "color": [ 1.0, 1.0, 1.0, 1.0 ],
                    "fontface": 0,
                    "fontname": "Arial",
                    "id": "obj-1",
                    "maxclass": "bachmcp.prompt",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 255.0, 795.0, 420.0, 140.0 ],
                    "prompt_sent": 0,
                    "prompt_text": "remember me too!"
                }
            },
            {
                "box": {
                    "id": "obj-25",
                    "linecount": 5,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 14.0, 232.0, 150.0, 74.0 ],
                    "text": "bachmcp.server initiates the chat-api, which is accesible through any web browser in your OS. Send \"open\" to see."
                }
            },
            {
                "box": {
                    "id": "obj-23",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 14.0, 119.0, 103.0, 20.0 ],
                    "text": "1) start the server"
                }
            },
            {
                "box": {
                    "id": "obj-21",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 1092.0, 348.0, 35.0, 22.0 ],
                    "text": "open"
                }
            },
            {
                "box": {
                    "id": "obj-19",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1092.0, 384.0, 230.0, 22.0 ],
                    "text": "bachmcp.chat @floating 0 @auto_open 0"
                }
            },
            {
                "box": {
                    "id": "obj-6",
                    "maxclass": "message",
                    "numinlets": 2,
                    "numoutlets": 1,
                    "outlettype": [ "" ],
                    "patching_rect": [ 90.0, 149.0, 35.0, 22.0 ],
                    "text": "open"
                }
            },
            {
                "box": {
                    "id": "obj-7",
                    "maxclass": "toggle",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "int" ],
                    "parameter_enable": 0,
                    "patching_rect": [ 14.0, 148.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-4",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "dictionary", "" ],
                    "patching_rect": [ 14.0, 201.0, 133.0, 22.0 ],
                    "text": "bachmcp.server claude"
                }
            },
            {
                "box": {
                    "id": "obj-3",
                    "linecount": 8,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1092.0, 223.0, 622.0, 114.0 ],
                    "text": "If you feel more like chatting with LLMs...\n\nbachmcp features a chat API of its own. Using it has certain advantages for the workflow, such as history keeping, automatic handling of active instance, etc.\n\nbachmcp.chat can leverage both, Claude and Local modes. If using Claude, the conversations in the Claude Desktop or Claude Code app won't show here. On the contrary, it is possible to use bachmcp.chat with Claude's models and its answers will be properly routed/echoed back in the chat (but not the other way round!)."
                }
            },
            {
                "box": {
                    "args": [ "prompt-me", "selector" ],
                    "bgmode": 0,
                    "border": 0,
                    "clickthrough": 0,
                    "enablehscroll": 0,
                    "enablevscroll": 0,
                    "id": "obj-11",
                    "lockeddragscroll": 0,
                    "lockedsize": 0,
                    "maxclass": "bpatcher",
                    "name": "bachmcp.bpatcher.algorithm.maxpat",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "offset": [ 0.0, 0.0 ],
                    "outlettype": [ "", "", "" ],
                    "patching_rect": [ 245.0, 269.0, 288.0, 365.0 ],
                    "viewvisibility": 1
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "bgcolor": [ 0.7254901960784313, 0.7254901960784313, 0.7254901960784313, 1.0 ],
                    "id": "obj-29",
                    "maxclass": "panel",
                    "mode": 0,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 215.0, 672.0, 684.0, 323.0 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "bgcolor": [ 0.7254901960784313, 0.7254901960784313, 0.7254901960784313, 1.0 ],
                    "id": "obj-30",
                    "maxclass": "panel",
                    "mode": 0,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 215.0, 140.0, 834.0, 519.0 ],
                    "proportion": 0.5
                }
            },
            {
                "box": {
                    "angle": 270.0,
                    "bgcolor": [ 0.7254901960784313, 0.7254901960784313, 0.7254901960784313, 1.0 ],
                    "id": "obj-31",
                    "maxclass": "panel",
                    "mode": 0,
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 1063.0, 140.0, 666.0, 519.0 ],
                    "proportion": 0.5
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-27", 0 ],
                    "source": [ "obj-1", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-11", 0 ],
                    "source": [ "obj-12", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-12", 0 ],
                    "source": [ "obj-14", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-20", 0 ],
                    "source": [ "obj-18", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-17", 0 ],
                    "source": [ "obj-20", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-19", 0 ],
                    "source": [ "obj-21", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-1", 0 ],
                    "source": [ "obj-5", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-4", 0 ],
                    "midpoints": [ 99.5, 183.1328125, 23.5, 183.1328125 ],
                    "source": [ "obj-6", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-4", 0 ],
                    "source": [ "obj-7", 0 ]
                }
            }
        ],
        "autosave": 0,
        "patchlinecolor": [ 0.592156862745098, 0.592156862745098, 0.592156862745098, 1.0 ]
    }
}