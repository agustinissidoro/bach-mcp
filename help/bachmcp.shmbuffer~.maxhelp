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
   333.0,
   92.0,
   1068.0,
   853.0
  ],
  "showrootpatcherontab": 0,
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
      220.0,
      22.0
     ],
     "saved_object_attributes": {
      "filename": "helpstarter",
      "parameter_enable": 0
     },
     "text": "js helpstarter bachmcp.shmbuffer~"
    }
   },
   {
    "box": {
     "id": "obj-2",
     "maxclass": "jsui",
     "filename": "helpname.js",
     "jsarguments": [
      "bachmcp.shmbuffer~"
     ],
     "border": 0,
     "ignoreclick": 1,
     "numinlets": 1,
     "numoutlets": 1,
     "outlettype": [
      ""
     ],
     "parameter_enable": 0,
     "patching_rect": [
      10.0,
      10.0,
      400.0,
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
     "patching_rect": [
      10.0,
      205.0,
      58.1,
      22.0
     ],
     "text": "p basic",
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
       1068.0,
       827.0
      ],
      "showontab": 1,
      "boxes": [
       {
        "box": {
         "maxclass": "jsui",
         "filename": "helpdetails.js",
         "jsarguments": [
          "bachmcp.shmbuffer~"
         ],
         "border": 0,
         "ignoreclick": 1,
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "parameter_enable": 0,
         "patching_rect": [
          10.0,
          10.0,
          620.0,
          76.0
         ],
         "id": "obj-1"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          100,
          1000.0,
          35.5
         ],
         "text": "The samples live in shared memory (/bachmcp.<name>): Python reads and writes that very memory (ShmBuffer in py/bach_mcp/utilities/shmbuffer.py), with no file written and nothing sent. No audio here: bang puts the memory into a buffer~, which plays and shows it.",
         "id": "obj-2"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          150,
          700.0,
          21.0
         ],
         "text": "1. Fill the memory from a sound file or a buffer~: source.",
         "id": "obj-3"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          178,
          121.1,
          23.0
         ],
         "text": "source jongly.aif",
         "id": "obj-4"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          170,
          178,
          133.7,
          23.0
         ],
         "text": "source drumLoop.aif",
         "id": "obj-5"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          325,
          178,
          133.7,
          23.0
         ],
         "text": "source cherokee.aif",
         "id": "obj-6"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          214,
          900.0,
          21.0
         ],
         "text": "2. bang: the memory into a buffer~ (with no @target, one the object makes); its name goes out the left outlet.",
         "id": "obj-7"
        }
       },
       {
        "box": {
         "maxclass": "button",
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          30,
          242,
          24.0,
          24.0
         ],
         "id": "obj-8"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          75,
          242,
          39.2,
          23.0
         ],
         "text": "info",
         "id": "obj-9"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          125,
          242,
          45.5,
          23.0
         ],
         "text": "clear",
         "id": "obj-10"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          30,
          285,
          190.0,
          23.0
         ],
         "text": "bachmcp.shmbuffer~ shmhelp",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          330,
          50.0,
          23.0
         ],
         "text": "set $1",
         "id": "obj-12"
        }
       },
       {
        "box": {
         "maxclass": "waveform~",
         "numinlets": 5,
         "numoutlets": 6,
         "outlettype": [
          "float",
          "float",
          "float",
          "float",
          "list",
          ""
         ],
         "patching_rect": [
          30,
          365,
          420.0,
          120.0
         ],
         "id": "obj-13"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          470,
          330,
          122.8,
          23.0
         ],
         "text": "print shmbuffer~",
         "id": "obj-14"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          470,
          365,
          420.0,
          50.0
         ],
         "text": "right outlet: bang when source, target, bang, size, sizeinsamps or clear is done; info: name, shm, frames, channels, sr, ms, serial; written <path>",
         "id": "obj-15"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          470,
          425,
          420.0,
          35.5
         ],
         "text": "left outlet: the name of the buffer~ just written (the target, or the object's own)",
         "id": "obj-16"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          505,
          1000.0,
          35.5
         ],
         "text": "Arguments: <name> [ms] [channels]. The name is at most 22 characters. The memory is removed when the object that made it is freed; other objects and programs under the same name share it.",
         "id": "obj-17"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-11",
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
          "obj-11",
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
          "obj-11",
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
          "obj-11",
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
          "obj-11",
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
          "obj-11",
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
          "obj-12",
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
          "obj-13",
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
          "obj-14",
          0
         ],
         "source": [
          "obj-11",
          1
         ]
        }
       }
      ]
     },
     "varname": "basic_tab"
    }
   },
   {
    "box": {
     "id": "obj-4",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      98.1,
      205.0,
      70.7,
      22.0
     ],
     "text": "p buffers",
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
       1068.0,
       827.0
      ],
      "showontab": 1,
      "boxes": [
       {
        "box": {
         "maxclass": "jsui",
         "filename": "helpdetails.js",
         "jsarguments": [
          "bachmcp.shmbuffer~"
         ],
         "border": 0,
         "ignoreclick": 1,
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "parameter_enable": 0,
         "patching_rect": [
          10.0,
          10.0,
          620.0,
          76.0
         ],
         "id": "obj-1"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          100,
          1000.0,
          35.5
         ],
         "text": "@source: where the samples come from, a buffer~ (a buffer~ of that name wins) or a sound file (any format macOS reads: absolute, Disk:/..., or a name in Max's search path). The memory takes its format: frames, channels, sample rate. As a message, source also reads it now.",
         "id": "obj-2"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          165,
          1000.0,
          35.5
         ],
         "text": "@target: the buffer~ bang writes into, resized to fit the memory. As a message, target also writes now. target alone: no target, bang writes the object's own buffer~ again.",
         "id": "obj-3"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          620,
          215,
          220.0,
          23.0
         ],
         "text": "buffer~ shmhelp-a drumLoop.aif",
         "outlettype": [
          "float",
          "bang"
         ],
         "id": "obj-4"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          620,
          250,
          130.0,
          23.0
         ],
         "text": "buffer~ shmhelp-b",
         "outlettype": [
          "float",
          "bang"
         ],
         "id": "obj-5"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          850,
          215,
          200.0,
          21.0
         ],
         "text": "a source",
         "id": "obj-6"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          850,
          250,
          200.0,
          21.0
         ],
         "text": "a target",
         "id": "obj-7"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          215,
          114.8,
          23.0
         ],
         "text": "source shmhelp-a",
         "id": "obj-8"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          170,
          215,
          114.8,
          23.0
         ],
         "text": "source anton.aif",
         "id": "obj-9"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          250,
          114.8,
          23.0
         ],
         "text": "target shmhelp-b",
         "id": "obj-10"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          170,
          250,
          51.8,
          23.0
         ],
         "text": "target",
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "button",
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          30,
          285,
          24.0,
          24.0
         ],
         "id": "obj-12"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          60,
          285,
          300.0,
          21.0
         ],
         "text": "bang: to the target (or the own buffer~)",
         "id": "obj-13"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          30,
          325,
          437.8,
          23.0
         ],
         "text": "bachmcp.shmbuffer~ shmhelp-io @source jongly.aif @target shmhelp-b",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-14"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          370,
          50.0,
          23.0
         ],
         "text": "set $1",
         "id": "obj-15"
        }
       },
       {
        "box": {
         "maxclass": "waveform~",
         "numinlets": 5,
         "numoutlets": 6,
         "outlettype": [
          "float",
          "float",
          "float",
          "float",
          "list",
          ""
         ],
         "patching_rect": [
          30,
          405,
          420.0,
          120.0
         ],
         "id": "obj-16"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          470,
          370,
          122.8,
          23.0
         ],
         "text": "print shmbuffer~",
         "id": "obj-17"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 1,
         "patching_rect": [
          620,
          290,
          160.6,
          23.0
         ],
         "text": "loadmess set shmhelp-b",
         "outlettype": [
          ""
         ],
         "id": "obj-18"
        }
       },
       {
        "box": {
         "maxclass": "waveform~",
         "numinlets": 5,
         "numoutlets": 6,
         "outlettype": [
          "float",
          "float",
          "float",
          "float",
          "list",
          ""
         ],
         "patching_rect": [
          620,
          325,
          420.0,
          120.0
         ],
         "id": "obj-19"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          620,
          450,
          420.0,
          35.5
         ],
         "text": "shmhelp-b, the target. @source is read once the patcher is loaded, so its buffer~ may come later in the patch.",
         "id": "obj-20"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-14",
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
          "obj-14",
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
          "obj-14",
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
          "obj-14",
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
          "obj-14",
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
          "obj-15",
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
          "obj-16",
          0
         ],
         "source": [
          "obj-15",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-17",
          0
         ],
         "source": [
          "obj-14",
          1
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
     }
    }
   },
   {
    "box": {
     "id": "obj-5",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      198.8,
      205.0,
      51.8,
      22.0
     ],
     "text": "p size",
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
       1068.0,
       827.0
      ],
      "showontab": 1,
      "boxes": [
       {
        "box": {
         "maxclass": "jsui",
         "filename": "helpdetails.js",
         "jsarguments": [
          "bachmcp.shmbuffer~"
         ],
         "border": 0,
         "ignoreclick": 1,
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "parameter_enable": 0,
         "patching_rect": [
          10.0,
          10.0,
          620.0,
          76.0
         ],
         "id": "obj-1"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          100,
          1000.0,
          50.0
         ],
         "text": "With a size (arguments, size, sizeinsamps) the object makes a new, silent memory, replacing what was under the name. With a name only, it joins the memory a program already made, or makes an empty one. macOS can't resize a shared memory: a new size is a new memory under the same name, and Python follows it by itself.",
         "id": "obj-2"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          170,
          70.7,
          23.0
         ],
         "text": "size 1000",
         "id": "obj-3"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          200,
          170,
          300.0,
          21.0
         ],
         "text": "1000 ms, the channels as they were",
         "id": "obj-4"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          200,
          77.0,
          23.0
         ],
         "text": "size 250 4",
         "id": "obj-5"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          200,
          200,
          300.0,
          21.0
         ],
         "text": "250 ms, 4 channels",
         "id": "obj-6"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          230,
          133.7,
          23.0
         ],
         "text": "sizeinsamps 48000 1",
         "id": "obj-7"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          200,
          230,
          300.0,
          21.0
         ],
         "text": "in frames",
         "id": "obj-8"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          260,
          64.4,
          23.0
         ],
         "text": "sr 48000",
         "id": "obj-9"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          200,
          260,
          300.0,
          21.0
         ],
         "text": "the sample rate written in the memory",
         "id": "obj-10"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          290,
          45.5,
          23.0
         ],
         "text": "clear",
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          200,
          290,
          300.0,
          21.0
         ],
         "text": "silence",
         "id": "obj-12"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          320,
          39.2,
          23.0
         ],
         "text": "info",
         "id": "obj-13"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          30,
          365,
          255.1,
          23.0
         ],
         "text": "bachmcp.shmbuffer~ shmhelp-size 500 2",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-14"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          30,
          410,
          122.8,
          23.0
         ],
         "text": "print shmbuffer~",
         "id": "obj-15"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          450,
          1000.0,
          21.0
         ],
         "text": "Each of these tells the other program (in Python: ShmBuffer.wait() returns). Messages run in the main thread.",
         "id": "obj-16"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-14",
          0
         ],
         "source": [
          "obj-3",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-14",
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
          "obj-14",
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
          "obj-14",
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
          "obj-14",
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
          "obj-14",
          0
         ],
         "source": [
          "obj-13",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-15",
          0
         ],
         "source": [
          "obj-14",
          1
         ]
        }
       }
      ]
     }
    }
   },
   {
    "box": {
     "id": "obj-6",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      280.6,
      205.0,
      64.4,
      22.0
     ],
     "text": "p python",
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
       1068.0,
       827.0
      ],
      "showontab": 1,
      "boxes": [
       {
        "box": {
         "maxclass": "jsui",
         "filename": "helpdetails.js",
         "jsarguments": [
          "bachmcp.shmbuffer~"
         ],
         "border": 0,
         "ignoreclick": 1,
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "parameter_enable": 0,
         "patching_rect": [
          10.0,
          10.0,
          620.0,
          76.0
         ],
         "id": "obj-1"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          100,
          1000.0,
          50.0
         ],
         "text": "Python works on the same samples. Start the example (examples/python/shmbuffers.py) with bachmcp.python, then call its functions: each one changes the memory and says so (touch()). With @notify 1 the object then writes its buffer~ by itself, as for bang; with 0, the next bang does. Either way the console says python written <name>.",
         "id": "obj-2"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          175,
          221.9,
          23.0
         ],
         "text": "run examples/python/shmbuffers.py",
         "id": "obj-3"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          175,
          270.0,
          21.0
         ],
         "text": "start the script (relative to @folder)",
         "id": "obj-4"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          205,
          165.2,
          23.0
         ],
         "text": "call gain shmhelp-py 0.5",
         "id": "obj-5"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          205,
          270.0,
          21.0
         ],
         "text": "the samples times 0.5, in place",
         "id": "obj-6"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          235,
          152.6,
          23.0
         ],
         "text": "call gain shmhelp-py 2",
         "id": "obj-7"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          265,
          158.9,
          23.0
         ],
         "text": "call reverse shmhelp-py",
         "id": "obj-8"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          265,
          270.0,
          21.0
         ],
         "text": "backwards",
         "id": "obj-9"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          295,
          196.7,
          23.0
         ],
         "text": "call sine shmhelp-py 440 1000",
         "id": "obj-10"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          295,
          270.0,
          21.0
         ],
         "text": "a sine, 1000 ms: a new size",
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          325,
          140.0,
          23.0
         ],
         "text": "call info shmhelp-py",
         "id": "obj-12"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          325,
          270.0,
          21.0
         ],
         "text": "frames, channels, sr, serial",
         "id": "obj-13"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          355,
          146.3,
          23.0
         ],
         "text": "call watch shmhelp-py",
         "id": "obj-14"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          355,
          270.0,
          21.0
         ],
         "text": "Python waits for Max: changed ...",
         "id": "obj-15"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          385,
          32.9,
          23.0
         ],
         "text": "eof",
         "id": "obj-16"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          385,
          270.0,
          21.0
         ],
         "text": "end the script",
         "id": "obj-17"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 3,
         "patching_rect": [
          30,
          427,
          355.9,
          23.0
         ],
         "text": "bachmcp.python @python ../.venv/bin/python @folder ..",
         "outlettype": [
          "",
          "",
          ""
         ],
         "id": "obj-18"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          30,
          470,
          110.2,
          23.0
         ],
         "text": "print messages",
         "id": "obj-19"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          185,
          470,
          78.7,
          23.0
         ],
         "text": "print log",
         "id": "obj-20"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          340,
          470,
          97.6,
          23.0
         ],
         "text": "print status",
         "id": "obj-21"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          600,
          175,
          121.1,
          23.0
         ],
         "text": "source jongly.aif",
         "id": "obj-22"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          740,
          175,
          64.4,
          23.0
         ],
         "text": "size 300",
         "id": "obj-23"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          820,
          175,
          45.5,
          23.0
         ],
         "text": "clear",
         "id": "obj-24"
        }
       },
       {
        "box": {
         "maxclass": "toggle",
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          "int"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          600,
          210,
          24.0,
          24.0
         ],
         "id": "obj-25"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          635,
          210,
          70.0,
          23.0
         ],
         "text": "notify $1",
         "id": "obj-26"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          600,
          255,
          387.4,
          23.0
         ],
         "text": "bachmcp.shmbuffer~ shmhelp-py @source jongly.aif @notify 1",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-27"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          600,
          300,
          50.0,
          23.0
         ],
         "text": "set $1",
         "id": "obj-28"
        }
       },
       {
        "box": {
         "maxclass": "waveform~",
         "numinlets": 5,
         "numoutlets": 6,
         "outlettype": [
          "float",
          "float",
          "float",
          "float",
          "list",
          ""
         ],
         "patching_rect": [
          600,
          335,
          420.0,
          120.0
         ],
         "id": "obj-29"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          670,
          300,
          122.8,
          23.0
         ],
         "text": "print shmbuffer~",
         "id": "obj-30"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          600,
          465,
          440.0,
          50.0
         ],
         "text": "After call watch, a source, size or clear here comes back from Python as changed shmhelp-py <serial> <frames> <channels>: Max says so whenever it changes the memory.",
         "id": "obj-31"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          515,
          1000.0,
          35.5
         ],
         "text": "In Python:  buf = ShmBuffer(\"shmhelp-py\");  buf.array  (float32, frames x channels, Max's own samples);  buf.touch();  buf.write(samples, sr);  buf.wait().  No lock: two programs writing at once get a mix of both.",
         "id": "obj-32"
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
          "obj-3",
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
          "obj-5",
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
          "obj-7",
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
       },
       {
        "patchline": {
         "destination": [
          "obj-26",
          0
         ],
         "source": [
          "obj-25",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-27",
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
          "obj-27",
          0
         ],
         "source": [
          "obj-23",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-27",
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
          "obj-27",
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
          "obj-28",
          0
         ],
         "source": [
          "obj-27",
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
          "obj-27",
          1
         ]
        }
       }
      ]
     }
    }
   },
   {
    "box": {
     "id": "obj-7",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      375.0,
      205.0,
      58.1,
      22.0
     ],
     "text": "p files",
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
       1068.0,
       827.0
      ],
      "showontab": 1,
      "boxes": [
       {
        "box": {
         "maxclass": "jsui",
         "filename": "helpdetails.js",
         "jsarguments": [
          "bachmcp.shmbuffer~"
         ],
         "border": 0,
         "ignoreclick": 1,
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "parameter_enable": 0,
         "patching_rect": [
          10.0,
          10.0,
          620.0,
          76.0
         ],
         "id": "obj-1"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          100,
          1000.0,
          35.5
         ],
         "text": "write [file]: the memory into a sound file, as buffer~ does. The format comes from the extension (.wav .aif .caf .flac; none: .wav); no file: a save dialog; a bare name goes next to the patcher. writewave, writeaiff, writeflac, writecaf choose the format. Then written <path> out the right outlet.",
         "id": "obj-2"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          170,
          45.5,
          23.0
         ],
         "text": "write",
         "id": "obj-3"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          85.5,
          170,
          70.7,
          23.0
         ],
         "text": "writewave",
         "id": "obj-4"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          166.2,
          170,
          70.7,
          23.0
         ],
         "text": "writeaiff",
         "id": "obj-5"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          246.89999999999998,
          170,
          70.7,
          23.0
         ],
         "text": "writeflac",
         "id": "obj-6"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          327.59999999999997,
          170,
          64.4,
          23.0
         ],
         "text": "writecaf",
         "id": "obj-7"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          210,
          800.0,
          21.0
         ],
         "text": "@samptype: the sample type of written files: int16, int24 (default), int32, float32.",
         "id": "obj-8"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          238,
          102.2,
          23.0
         ],
         "text": "samptype int16",
         "id": "obj-9"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          142.2,
          238,
          102.2,
          23.0
         ],
         "text": "samptype int24",
         "id": "obj-10"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          254.39999999999998,
          238,
          102.2,
          23.0
         ],
         "text": "samptype int32",
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          366.59999999999997,
          238,
          114.8,
          23.0
         ],
         "text": "samptype float32",
         "id": "obj-12"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          30,
          285,
          349.6,
          23.0
         ],
         "text": "bachmcp.shmbuffer~ shmhelp-file @source cherokee.aif",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-13"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          30,
          330,
          122.8,
          23.0
         ],
         "text": "print shmbuffer~",
         "id": "obj-14"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-13",
          0
         ],
         "source": [
          "obj-3",
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
          "obj-4",
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
          "obj-5",
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
          "obj-6",
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
          "obj-7",
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
          "obj-9",
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
          "obj-11",
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
       },
       {
        "patchline": {
         "destination": [
          "obj-14",
          0
         ],
         "source": [
          "obj-13",
          1
         ]
        }
       }
      ]
     }
    }
   },
   {
    "box": {
     "id": "obj-8",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      463.1,
      205.0,
      51.8,
      22.0
     ],
     "text": "p name",
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
       1068.0,
       827.0
      ],
      "showontab": 1,
      "boxes": [
       {
        "box": {
         "maxclass": "jsui",
         "filename": "helpdetails.js",
         "jsarguments": [
          "bachmcp.shmbuffer~"
         ],
         "border": 0,
         "ignoreclick": 1,
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "parameter_enable": 0,
         "patching_rect": [
          10.0,
          10.0,
          620.0,
          76.0
         ],
         "id": "obj-1"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          10,
          100,
          1000.0,
          35.5
         ],
         "text": "set_name <name> (or name): the object goes to another memory. One already there: it joins it. None: its samples come along to the new name, and the old memory is removed if this object made it.",
         "id": "obj-2"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          160,
          133.7,
          23.0
         ],
         "text": "set_name shmhelp-n2",
         "id": "obj-3"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          200,
          160,
          400.0,
          21.0
         ],
         "text": "joins the memory of the object on the right",
         "id": "obj-4"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          190,
          133.7,
          23.0
         ],
         "text": "set_name shmhelp-n3",
         "id": "obj-5"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          200,
          190,
          400.0,
          21.0
         ],
         "text": "nothing there: the samples come along",
         "id": "obj-6"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          220,
          133.7,
          23.0
         ],
         "text": "set_name shmhelp-n1",
         "id": "obj-7"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          250,
          39.2,
          23.0
         ],
         "text": "info",
         "id": "obj-8"
        }
       },
       {
        "box": {
         "maxclass": "button",
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          90,
          250,
          24.0,
          24.0
         ],
         "id": "obj-9"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          30,
          290,
          324.4,
          23.0
         ],
         "text": "bachmcp.shmbuffer~ shmhelp-n1 @source jongly.aif",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-10"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          30,
          330,
          50.0,
          23.0
         ],
         "text": "set $1",
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "waveform~",
         "numinlets": 5,
         "numoutlets": 6,
         "outlettype": [
          "float",
          "float",
          "float",
          "float",
          "list",
          ""
         ],
         "patching_rect": [
          30,
          365,
          420.0,
          120.0
         ],
         "id": "obj-12"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          330,
          330,
          122.8,
          23.0
         ],
         "text": "print shmbuffer~",
         "id": "obj-13"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          620,
          290,
          337.0,
          23.0
         ],
         "text": "bachmcp.shmbuffer~ shmhelp-n2 @source cherokee.aif",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-14"
        }
       },
       {
        "box": {
         "maxclass": "button",
         "numinlets": 1,
         "numoutlets": 1,
         "outlettype": [
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          620,
          250,
          24.0,
          24.0
         ],
         "id": "obj-15"
        }
       },
       {
        "box": {
         "maxclass": "message",
         "fontsize": 13.0,
         "numinlets": 2,
         "numoutlets": 1,
         "outlettype": [
          ""
         ],
         "patching_rect": [
          620,
          330,
          50.0,
          23.0
         ],
         "text": "set $1",
         "id": "obj-16"
        }
       },
       {
        "box": {
         "maxclass": "waveform~",
         "numinlets": 5,
         "numoutlets": 6,
         "outlettype": [
          "float",
          "float",
          "float",
          "float",
          "list",
          ""
         ],
         "patching_rect": [
          620,
          365,
          420.0,
          120.0
         ],
         "id": "obj-17"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-10",
          0
         ],
         "source": [
          "obj-3",
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
          "obj-5",
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
          "obj-7",
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
          "obj-8",
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
          "obj-11",
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
          "obj-12",
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
          "obj-13",
          0
         ],
         "source": [
          "obj-10",
          1
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-14",
          0
         ],
         "source": [
          "obj-15",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-16",
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
          "obj-17",
          0
         ],
         "source": [
          "obj-16",
          0
         ]
        }
       }
      ]
     }
    }
   },
   {
    "box": {
     "id": "obj-9",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      544.9,
      205.0,
      32.9,
      22.0
     ],
     "text": "p ?",
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
       1068.0,
       827.0
      ],
      "showontab": 1,
      "boxes": [],
      "lines": []
     },
     "varname": "q_tab"
    }
   }
  ],
  "lines": [],
  "autosave": 0
 }
}