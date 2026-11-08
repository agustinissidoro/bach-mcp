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
        "rect": [ 420.0, 101.0, 1100.0, 853.0 ],
        "boxes": [
            {
                "box": {
                    "id": "obj-2",
                    "linecount": 3,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 239.0, 408.0, 622.0, 47.0 ],
                    "text": "You can combine both uses, bachmcp.chat and bachmcp.prompt, depending on your workflow and vibe ;)\nA full history will be kept in your playground in the /prompts folder, so the chat is constantly updated even if you prompt using the bachmcp.prompt object "
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
                    "patching_rect": [ 239.0, 461.0, 420.0, 140.0 ],
                    "prompt_sent": 0,
                    "prompt_text": ""
                }
            },
            {
                "box": {
                    "id": "obj-26",
                    "linecount": 4,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 329.0, 208.0, 153.0, 60.0 ],
                    "text": "The same interface exists as an object in Max, which features its own window and that is cooler ;)"
                }
            },
            {
                "box": {
                    "id": "obj-25",
                    "linecount": 5,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 130.0, 201.0, 150.0, 74.0 ],
                    "text": "bachmcp.server initiates the chat-api, which is accesible through any web browser in your OS. Send \"open\" to see."
                }
            },
            {
                "box": {
                    "id": "obj-23",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 17.0, 228.0, 103.0, 20.0 ],
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
                    "patching_rect": [ 329.0, 274.0, 35.0, 22.0 ],
                    "text": "open"
                }
            },
            {
                "box": {
                    "id": "obj-19",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 329.0, 310.0, 230.0, 22.0 ],
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
                    "patching_rect": [ 88.0, 258.0, 35.0, 22.0 ],
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
                    "patching_rect": [ 17.0, 257.0, 24.0, 24.0 ]
                }
            },
            {
                "box": {
                    "id": "obj-4",
                    "maxclass": "newobj",
                    "numinlets": 1,
                    "numoutlets": 3,
                    "outlettype": [ "", "dictionary", "" ],
                    "patching_rect": [ 17.0, 310.0, 133.0, 22.0 ],
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
                    "patching_rect": [ 8.0, 25.0, 622.0, 114.0 ],
                    "text": "If you feel more like chatting with LLMs...\n\nbachmcp features a chat API of its own. Using it has certain advantages for the workflow, such as history keeping, automatic handling of active instance, etc.\n\nbachmcp.chat can leverage both, Claude and Local modes. If using Claude, the conversations in the Claude Desktop or Claude Code app won't show here. On the contrary, it is possible to use bachmcp.chat with Claude's models and its answers will be properly routed/echoed back in the chat (but not the other way round!)."
                }
            }
        ],
        "lines": [
            {
                "patchline": {
                    "destination": [ "obj-19", 0 ],
                    "source": [ "obj-21", 0 ]
                }
            },
            {
                "patchline": {
                    "destination": [ "obj-4", 0 ],
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
        "autosave": 0
    }
}