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
        "rect": [ 34.0, 92.0, 1852.0, 954.0 ],
        "boxes": [
            {
                "box": {
                    "id": "obj-30",
                    "linecount": 2,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 919.0, 1005.5, 900.0, 33.0 ],
                    "text": "To edit a profile, simply edit the .json file: add or delete the names of already existing skills. You can also create your own profile: copy the file, change its name and edit the skills list."
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-29",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 919.0, 979.5, 603.0, 20.0 ],
                    "text": "Profiles"
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-28",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 919.0, 532.5, 603.0, 20.0 ],
                    "text": "Skills."
                }
            },
            {
                "box": {
                    "id": "obj-27",
                    "linecount": 31,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 919.0, 558.5, 854.0, 422.0 ],
                    "text": "To write a skill, take a look at the already existing files. Try to be concise and provide examples. Use markdown, like titles, to make the information easy to read. A trick is also using a powerful LLM to write your skills: give the information, attach the existing bachmcp files for context and ask it to structure your information as a skill as well.\n\nSkill files have markers. They make a part of the skill file available ONLY to a specific type of object, so not every other object gets it. This is handy to keep things clean and focused: bachmcp.score doesn't need to know how bachmcp.algorithm~ writes gen~ code. If no marker is used, the skill is available for every object using that skill.\n\nOpening marker, on a line of its own:\n\n<!-- [type] -->\n\nClosing marker:\n\n<!-- /[type] -->\n\nThe types are not object names. They are: score (bachmcp.score); algo (bachmcp.algorithm, any type) or one of its types: generator, transformer, selector; gen (bachmcp.algorithm~) or one of its types: synth, fx. Several types can share a marker (<!-- transformer selector -->), and a part can sit inside another (a synth part inside a gen part). A part left open is closed at the end of its file. A second pair, <!-- verbose --> and <!-- quiet --> (both closed by <!-- /verbose -->), chooses how much the model says after its work, following the verbose setting.\n\nExample:\n\n<!-- score -->\n\n- Before the call, write the principle in two or three sentences, then how\n  many chords each voice has. The score ends there: write exactly that many.\n- Then get every pitch from the pitch tools, all in one round (several calls\n  at once, whole lists in each), and copy their answers into the score.\n\n<!-- /score -->"
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-26",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 919.0, 507.0, 603.0, 20.0 ],
                    "text": "Writing and editing skills and profiles."
                }
            },
            {
                "box": {
                    "id": "obj-25",
                    "linecount": 11,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 919.0, 346.5, 903.0, 154.0 ],
                    "text": "You can create your own profiles or modify the existing ones to include your own skills. You can pass a profile using @profile to a bachmcp.server (it becomes global) or to single instances of bachmcp.algorithm, bachmcp.score or bachmcp.algorithm~.\n\nTwo more important things about profiles and skills.\n\n1) In the same object, profiles and skills add up: if you use a profile and also pass skills, both are used. For example, \"@profile minimal-algorithmic-composer @skills my-noteheads\", where my-noteheads is a skill file of your own in /skills.\n\n2) An instance's own choice replaces the global one: it does not add to it. If bachmcp.server uses \"@profile minimal-algorithmic-composer\" and a bachmcp.algorithm~ sets \"@profile minimal-electronic-composer\" (which, by the way, is the case by default), that bachmcp.algorithm~ reads only its own choice. An instance set to global (@profile global @skills global, both by default) reads the server's choice."
                }
            },
            {
                "box": {
                    "id": "obj-24",
                    "linecount": 3,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 917.0, 42.0, 767.0, 47.0 ],
                    "text": "But there's also one cooler thing: profiles. Profiles are just a collection of skills for easy prototyping and experimenting. Profiles are also saved in your playground in /skills/profiles. By default, two profiles are created with your playground: minimal-algorithmic-composer and minimal-electronic-composer."
                }
            },
            {
                "box": {
                    "autofit": 1,
                    "forceaspect": 1,
                    "id": "obj-22",
                    "maxclass": "fpic",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "jit_matrix" ],
                    "patching_rect": [ 917.0, 98.44542772861357, 356.0, 65.10914454277287 ],
                    "pic": "/Users/agustin/Desktop/Capture d’écran 2026-11-11 à 23.32.48.png"
                }
            },
            {
                "box": {
                    "id": "obj-21",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 919.0, 177.5, 352.0, 20.0 ],
                    "text": "A profile is just a .json file with a skill list.  "
                }
            },
            {
                "box": {
                    "autofit": 1,
                    "forceaspect": 1,
                    "id": "obj-19",
                    "maxclass": "fpic",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "jit_matrix" ],
                    "patching_rect": [ 917.0, 207.5, 356.0, 125.01672240802675 ],
                    "pic": "/Users/agustin/Desktop/Capture d’écran 2026-11-11 à 23.31.23.png"
                }
            },
            {
                "box": {
                    "id": "obj-17",
                    "maxclass": "live.line",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 892.0, 42.0, 5.0, 996.5 ]
                }
            },
            {
                "box": {
                    "autofit": 1,
                    "forceaspect": 1,
                    "id": "obj-14",
                    "maxclass": "fpic",
                    "numinlets": 1,
                    "numoutlets": 1,
                    "outlettype": [ "jit_matrix" ],
                    "patching_rect": [ 15.0, 822.5, 372.0, 81.14093959731544 ],
                    "pic": "/Users/agustin/Desktop/Capture d’écran 2026-11-11 à 23.30.03.png"
                }
            },
            {
                "box": {
                    "id": "obj-12",
                    "linecount": 9,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 912.5, 858.0, 127.0 ],
                    "text": "bachmcp manages skills in a specific way. Not every skill is passed with every prompt. To be as concise as possible and take as little of the context window as possible, bachmcp compiles the skills you chose into one file, and then each object keeps only the parts marked for its type (see markers). The compiled file is written in your playground: skills/.compiled.md, or skills/.compiled/<instance>.md for an object with its own choice, with an estimate of its tokens at the top. Open it to see what the model reads. This not only means that skills in bachmcp are dynamic, but that they are a crucial part of the creative process: everyone using the software might want something slightly different out of the models.\n\nYou can create your own skill files and test them. This is quite easy: save the file in your playground's /skills folder, then pass its name (without .md and without a path) with the @skills attribute. If you set it in bachmcp.server, those skills will be used as default for every object. If you set it in a single instance of bachmcp.algorithm, bachmcp.score or bachmcp.algorithm~, it will only affect that instance's prompts."
                }
            },
            {
                "box": {
                    "id": "obj-11",
                    "linecount": 4,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 749.5, 858.0, 60.0 ],
                    "text": "Skill files live in your playground in /skills. By default, there are 2 core skill files, one for symbolic algorithmic composition (core-algorithmic) and another one for electronic composition (core-electronic), since they require quite different tasks. They are copied from the base files of the package when the playground is set (a bachmcp.server does it when it starts), and only if they are missing: your edits are never overwritten. You can edit them. If you mess something up, delete them and the next time the playground is set they will be copied again."
                }
            },
            {
                "box": {
                    "id": "obj-10",
                    "maxclass": "live.line",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 699.5, 858.0, 11.0 ]
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-9",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 716.5, 603.0, 20.0 ],
                    "text": "How does this work in bachmcp?"
                }
            },
            {
                "box": {
                    "fontface": 0,
                    "id": "obj-8",
                    "linecount": 17,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 439.5, 836.0, 234.0 ],
                    "text": "A RAG system (retrieval-augmented generation) is useful for enhancing the context of a model in specific knowledge areas. For example, a model might not hold much specific information about the cello, but it certainly has a vague idea about it. A RAG system can help it perform better in this area by injecting information as context. But, again, this is not teaching the model. The degree to which the information you pass will be taken into account depends both on the model and on the quality of your RAG system.\n\nThe contents injected via a RAG system are also passed as a prompt (which is, actually, the only way to engage with an LLM), so they also use your context window.\n\nThe difference with a skill: a skill is always there, chosen beforehand, and tells the model how to work. A RAG is fetched for each request, only when a search finds something relevant, and tells the model what to know. Sometimes models hesitate about specific information, for example the range of a viola or how to mark a harmonic on a violin. A RAG can support that information easily. bachmcp uses a small RAG for instruments: ranges, registers and techniques of the strings, the woodwinds and the piano.\n\nA RAG can be structured in many ways, since it's written information. A common practice is to do files per topic in folders, for easy and intuitive indexing. The search also varies: most RAG systems search by meaning (embeddings), so \"the low string instrument\" can find the cello. bachmcp keeps it simple and searches by keyword: when your message names an instrument (\"cello\", \"alto flute\"), its file and its family's file are added to that message, once, the first time it is named. "
                }
            },
            {
                "box": {
                    "fontface": 0,
                    "id": "obj-7",
                    "linecount": 12,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 250.0, 860.0, 167.0 ],
                    "text": "A skill is nothing else than a curated prompt that is passed to the model before the actual content of your prompt. A model keeps no memory between requests: the whole conversation, skill included, is sent again at every prompt. In bachmcp, the skill is passed by bachmcp itself. You don't see it in the chat, but you can read it in your playground (see below).\n\nA skill is actually a text file (most commonly a .md file) with written explanations about how and what the model should do in certain situations. But a skill file is not \"teaching\" a model, it is rather \"instructing\" it: how to answer, what tools to call, what to look for, what to give as an output, etc. A good practice is to include examples.\n\nSomething important to have in mind, again, is that a skill file is sent as a prompt every time, and this impacts the context window: so it's not free. It is very tempting to write a huge skill file that would instruct the model what to do in every situation, but this would eat up your context window (even more if you're on a local model with little memory). The good side is: nothing is permanent. A bad skill can make the model worse, but editing or deleting it brings everything back. There's a lot of artistry in what to include in a skill file."
                }
            },
            {
                "box": {
                    "id": "obj-6",
                    "linecount": 3,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 191.5, 858.0, 47.0 ],
                    "text": "LLMs have become powerful agentic tools because they have also been trained for that: to follow instructions and to call tools. A program around the model (here, bachmcp) runs the loop: the model calls a tool, reads the result, decides the next call. Following instructions and calling tools in a loop is what makes them agentic."
                }
            },
            {
                "box": {
                    "id": "obj-5",
                    "linecount": 4,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 121.5, 858.0, 60.0 ],
                    "text": "There are still other ways to make a model act as if it knew something it wasn't trained on (or was poorly trained on), or to perform better at something it is not quite good at yet. One is fine-tuning, and the easiest way is training a small LoRA: a set of small extra matrices added beside the model's weights (the original weights stay untouched) that favour a certain kind of output. LoRAs are common in image generation and work for LLMs too: a small LLM can be fine-tuned on a Mac with MLX. Without any training at all, Skills and RAG are probably the most used options."
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-4",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 13.0, 606.0, 20.0 ],
                    "text": "Bitter news:"
                }
            },
            {
                "box": {
                    "fontface": 1,
                    "id": "obj-3",
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 95.5, 586.0, 20.0 ],
                    "text": "Sweet news:"
                }
            },
            {
                "box": {
                    "id": "obj-2",
                    "linecount": 3,
                    "maxclass": "comment",
                    "numinlets": 1,
                    "numoutlets": 0,
                    "patching_rect": [ 15.0, 40.0, 860.0, 47.0 ],
                    "text": "Strictly speaking, there's only one way to teach a model something: training. Training adjusts a model's weights, the billions of numbers it computes with, so that it predicts text better: what it \"knows\" is a side effect of that. Training a Large Language Model (LLM) from scratch is completely out of reach for 99.999% of the world population."
                }
            }
        ],
        "lines": [],
        "autosave": 0
    }
}