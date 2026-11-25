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
     "text": "js helpstarter bachmcp.pshmbuffer~"
    }
   },
   {
    "box": {
     "id": "obj-2",
     "maxclass": "jsui",
     "filename": "helpname.js",
     "jsarguments": [
      "bachmcp.pshmbuffer~"
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
          "bachmcp.pshmbuffer~"
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
         "text": "A polybuffer~ of shared memories. <name>.1, <name>.2 ... are buffer~s in Max (groove~ pshmhelp.2 plays the second) and memories Python reads and writes (PShmBuffer(\"pshmhelp\")[2]). A small index memory under the name itself says how many; <name> alone is not a buffer~, as with polybuffer~.",
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
         "text": "Arguments: <name> [count] [ms] [channels]: here 3 silent memories of 1000 ms, 1 channel. With a name only, the object joins memories a program already made, or starts with none.",
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
          215,
          121.1,
          23.0
         ],
         "text": "load 1 jongly.aif",
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
          161.1,
          215,
          133.7,
          23.0
         ],
         "text": "load 2 drumLoop.aif",
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
          304.79999999999995,
          215,
          133.7,
          23.0
         ],
         "text": "load 3 cherokee.aif",
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
          448.49999999999994,
          215,
          114.8,
          23.0
         ],
         "text": "load 4 anton.aif",
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
          600,
          215,
          440.0,
          35.5
         ],
         "text": "load <n> <file|buffer~>: memory n becomes it; n = count + 1 adds one",
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
          30,
          255,
          24.0,
          24.0
         ],
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
          58,
          255,
          230.0,
          21.0
         ],
         "text": "write every memory to its buffer~",
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
          300,
          255,
          24.0,
          23.0
         ],
         "text": "2",
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
          328,
          255,
          200.0,
          21.0
         ],
         "text": "write memory 2 only",
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
          530,
          255,
          64.4,
          23.0
         ],
         "text": "getcount",
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
          604.4,
          255,
          39.2,
          23.0
         ],
         "text": "info",
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
          653.6,
          255,
          51.8,
          23.0
         ],
         "text": "info 2",
         "id": "obj-15"
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
          300,
          255.1,
          23.0
         ],
         "text": "bachmcp.pshmbuffer~ pshmhelp 3 1000 1",
         "outlettype": [
          "",
          ""
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
          30,
          340,
          103.9,
          23.0
         ],
         "text": "print written",
         "id": "obj-17"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          260,
          340,
          130.0,
          23.0
         ],
         "text": "print pshmbuffer~",
         "id": "obj-18"
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
          300,
          560.0,
          50.0
         ],
         "text": "left outlet: <name> <count> after a write (the target's name when there is one)\nright outlet: bang when done; count <n>; info: name, shm, count, serial (memory n: name, shm, frames, channels, sr, ms, serial); written ...",
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
          85,
          385,
          300.0,
          21.0
         ],
         "text": "show pshmhelp.<n>",
         "id": "obj-20"
        }
       },
       {
        "box": {
         "maxclass": "number",
         "fontsize": 13.0,
         "minimum": 1,
         "numinlets": 1,
         "numoutlets": 2,
         "outlettype": [
          "",
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          30,
          385,
          50.0,
          23.0
         ],
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
          30,
          417,
          108.5,
          23.0
         ],
         "text": "set pshmhelp.$1",
         "id": "obj-22"
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
          449,
          420.0,
          120.0
         ],
         "buffername": "pshmhelp.1",
         "id": "obj-23"
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
          590,
          1000.0,
          35.5
         ],
         "text": "The buffer~s <name>.<n> exist as soon as their memories do. A [buffer~ pshmhelp.3] elsewhere in a patch is used, not duplicated. The name is at most 17 characters; up to 9999 memories.",
         "id": "obj-24"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-16",
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
          "obj-16",
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
          "obj-16",
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
          "obj-16",
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
          "obj-16",
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
          "obj-16",
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
          "obj-16",
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
          "obj-16",
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
          1
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-22",
          0
         ],
         "source": [
          "obj-21",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-23",
          0
         ],
         "source": [
          "obj-22",
          0
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
     "text": "p members",
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
          "bachmcp.pshmbuffer~"
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
          21.0
         ],
         "text": "Memories are added at the end and only the last can be removed, as Python does (PShmBuffer.append, pop).",
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
          145,
          108.5,
          23.0
         ],
         "text": "appendempty 500",
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
          145,
          320.0,
          21.0
         ],
         "text": "one more, silent: <ms> [channels]",
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
          175,
          127.4,
          23.0
         ],
         "text": "appendempty 1000 2",
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
          30,
          205,
          133.7,
          23.0
         ],
         "text": "append pshmhelp-src",
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
          200,
          205,
          320.0,
          21.0
         ],
         "text": "one more, a copy of this buffer~",
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
          235,
          51.8,
          23.0
         ],
         "text": "remove",
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
          200,
          235,
          320.0,
          21.0
         ],
         "text": "remove the last",
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
          265,
          45.5,
          23.0
         ],
         "text": "clear",
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
          200,
          265,
          320.0,
          21.0
         ],
         "text": "remove every memory",
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
          295,
          64.4,
          23.0
         ],
         "text": "getcount",
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
          200,
          295,
          320.0,
          21.0
         ],
         "text": "count <n> out the right outlet",
         "id": "obj-13"
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
          325,
          24.0,
          24.0
         ],
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
          58,
          325,
          560.0,
          21.0
         ],
         "text": "readfolder <folder> (or loadfolder): each sound file, by name, added at the end",
         "id": "obj-15"
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
          357,
          116.5,
          23.0
         ],
         "text": "opendialog fold",
         "outlettype": [
          "",
          "bang"
         ],
         "id": "obj-16"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 1,
         "patching_rect": [
          30,
          389,
          135.4,
          23.0
         ],
         "text": "prepend readfolder",
         "outlettype": [
          ""
         ],
         "id": "obj-17"
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
          430,
          223.6,
          23.0
         ],
         "text": "bachmcp.pshmbuffer~ pshmhelp-set",
         "outlettype": [
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
          103.9,
          23.0
         ],
         "text": "print written",
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
          260,
          470,
          130.0,
          23.0
         ],
         "text": "print pshmbuffer~",
         "id": "obj-20"
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
          145,
          240.0,
          23.0
         ],
         "text": "buffer~ pshmhelp-src cherokee.aif",
         "outlettype": [
          "float",
          "bang"
         ],
         "id": "obj-21"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          675,
          190,
          300.0,
          21.0
         ],
         "text": "show pshmhelp-set.<n>",
         "id": "obj-22"
        }
       },
       {
        "box": {
         "maxclass": "number",
         "fontsize": 13.0,
         "minimum": 1,
         "numinlets": 1,
         "numoutlets": 2,
         "outlettype": [
          "",
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          620,
          190,
          50.0,
          23.0
         ],
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
          620,
          222,
          133.7,
          23.0
         ],
         "text": "set pshmhelp-set.$1",
         "id": "obj-24"
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
          254,
          420.0,
          120.0
         ],
         "buffername": "pshmhelp-set.1",
         "id": "obj-25"
        }
       }
      ],
      "lines": [
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
       },
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
          "obj-17",
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
          "obj-24",
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
          "obj-25",
          0
         ],
         "source": [
          "obj-24",
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
          "bachmcp.pshmbuffer~"
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
         "text": "@source: where the memories come from, looked up in this order: a polybuffer~ (buffers <source>.1, <source>.2 ...: as many memories, with their formats), a buffer~ (one memory, a copy), a folder (one per sound file, sorted by name), a sound file (one). As a message, source also reads now.",
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
          620,
          175,
          121.1,
          23.0
         ],
         "text": "append jongly.aif",
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
          751.1,
          175,
          133.7,
          23.0
         ],
         "text": "append drumLoop.aif",
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
          894.8,
          175,
          45.5,
          23.0
         ],
         "text": "clear",
         "id": "obj-5"
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
          210,
          180.0,
          23.0
         ],
         "text": "polybuffer~ pshmhelp-poly",
         "outlettype": [
          "",
          "bang"
         ],
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
          175,
          140.0,
          23.0
         ],
         "text": "source pshmhelp-poly",
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
          180.0,
          175,
          133.7,
          23.0
         ],
         "text": "source cherokee.aif",
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
          30,
          210,
          24.0,
          24.0
         ],
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
          58,
          210,
          300.0,
          21.0
         ],
         "text": "source <folder>",
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
          240,
          116.5,
          23.0
         ],
         "text": "opendialog fold",
         "outlettype": [
          "",
          "bang"
         ],
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 1,
         "patching_rect": [
          30,
          272,
          110.2,
          23.0
         ],
         "text": "prepend source",
         "outlettype": [
          ""
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
          10,
          315,
          1000.0,
          35.5
         ],
         "text": "@target: a polybuffer~ the memories go to instead of the object's own buffer~s. It must already hold as many buffers (appendempty): the object can't add buffers to another polybuffer~. target alone: its own again.",
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
          620,
          365,
          108.5,
          23.0
         ],
         "text": "appendempty 100",
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
          750,
          365,
          45.5,
          23.0
         ],
         "text": "clear",
         "id": "obj-15"
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
          400,
          180.0,
          23.0
         ],
         "text": "polybuffer~ pshmhelp-out",
         "outlettype": [
          "",
          "bang"
         ],
         "id": "obj-16"
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
          365,
          133.7,
          23.0
         ],
         "text": "target pshmhelp-out",
         "id": "obj-17"
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
          200,
          365,
          51.8,
          23.0
         ],
         "text": "target",
         "id": "obj-18"
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
          270,
          365,
          24.0,
          24.0
         ],
         "id": "obj-19"
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
          410,
          217.3,
          23.0
         ],
         "text": "bachmcp.pshmbuffer~ pshmhelp-io",
         "outlettype": [
          "",
          ""
         ],
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
          30,
          450,
          103.9,
          23.0
         ],
         "text": "print written",
         "id": "obj-21"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          260,
          450,
          130.0,
          23.0
         ],
         "text": "print pshmbuffer~",
         "id": "obj-22"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          85,
          495,
          300.0,
          21.0
         ],
         "text": "show pshmhelp-io.<n>",
         "id": "obj-23"
        }
       },
       {
        "box": {
         "maxclass": "number",
         "fontsize": 13.0,
         "minimum": 1,
         "numinlets": 1,
         "numoutlets": 2,
         "outlettype": [
          "",
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          30,
          495,
          50.0,
          23.0
         ],
         "id": "obj-24"
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
          527,
          127.4,
          23.0
         ],
         "text": "set pshmhelp-io.$1",
         "id": "obj-25"
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
          559,
          420.0,
          120.0
         ],
         "buffername": "pshmhelp-io.1",
         "id": "obj-26"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          675,
          495,
          300.0,
          21.0
         ],
         "text": "show pshmhelp-out.<n>",
         "id": "obj-27"
        }
       },
       {
        "box": {
         "maxclass": "number",
         "fontsize": 13.0,
         "minimum": 1,
         "numinlets": 1,
         "numoutlets": 2,
         "outlettype": [
          "",
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          620,
          495,
          50.0,
          23.0
         ],
         "id": "obj-28"
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
          527,
          133.7,
          23.0
         ],
         "text": "set pshmhelp-out.$1",
         "id": "obj-29"
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
          559,
          420.0,
          120.0
         ],
         "buffername": "pshmhelp-out.1",
         "id": "obj-30"
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
          "obj-3",
          0
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
          "obj-4",
          0
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
          "obj-11",
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
          "obj-20",
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
          "obj-20",
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
          "obj-20",
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
          "obj-20",
          0
         ],
         "source": [
          "obj-17",
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
          "obj-19",
          0
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
          "obj-20",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-22",
          0
         ],
         "source": [
          "obj-20",
          1
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-25",
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
          "obj-29",
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
     "id": "obj-6",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      299.5,
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
          "bachmcp.pshmbuffer~"
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
         "text": "Python may add memories, remove the last one, resize or rewrite any; the object follows on the next message, and at once with @notify 1 (it then writes only the memories that changed, and makes buffer~ <name>.<n> for new ones). The example is examples/python/shmbuffers.py.",
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
          221.9,
          23.0
         ],
         "text": "call poly_add pshmhelp-py 330 500",
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
         "text": "one more: a sine",
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
          221.9,
          23.0
         ],
         "text": "call poly_add pshmhelp-py 660 250",
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
          215.6,
          23.0
         ],
         "text": "call poly_gain pshmhelp-py 1 0.5",
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
         "text": "memory 1 times 0.5",
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
          171.5,
          23.0
         ],
         "text": "call poly_pop pshmhelp-py",
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
         "text": "remove the last",
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
          184.1,
          23.0
         ],
         "text": "call poly_count pshmhelp-py",
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
          355,
          184.1,
          23.0
         ],
         "text": "call poly_watch pshmhelp-py",
         "id": "obj-13"
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
         "text": "Python waits for Max: poly_changed ...",
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
          385,
          32.9,
          23.0
         ],
         "text": "eof",
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
          330,
          385,
          270.0,
          21.0
         ],
         "text": "end the script",
         "id": "obj-16"
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
         "id": "obj-17"
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
          185,
          470,
          78.7,
          23.0
         ],
         "text": "print log",
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
          340,
          470,
          97.6,
          23.0
         ],
         "text": "print status",
         "id": "obj-20"
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
          175,
          108.5,
          23.0
         ],
         "text": "appendempty 300",
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
          745,
          175,
          51.8,
          23.0
         ],
         "text": "remove",
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
          810,
          175,
          45.5,
          23.0
         ],
         "text": "clear",
         "id": "obj-23"
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
          870,
          175,
          24.0,
          24.0
         ],
         "id": "obj-24"
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
          280.3,
          23.0
         ],
         "text": "bachmcp.pshmbuffer~ pshmhelp-py @notify 1",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-25"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          620,
          255,
          103.9,
          23.0
         ],
         "text": "print written",
         "id": "obj-26"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          760,
          255,
          130.0,
          23.0
         ],
         "text": "print pshmbuffer~",
         "id": "obj-27"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          675,
          295,
          300.0,
          21.0
         ],
         "text": "show pshmhelp-py.<n>",
         "id": "obj-28"
        }
       },
       {
        "box": {
         "maxclass": "number",
         "fontsize": 13.0,
         "minimum": 1,
         "numinlets": 1,
         "numoutlets": 2,
         "outlettype": [
          "",
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          620,
          295,
          50.0,
          23.0
         ],
         "id": "obj-29"
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
          327,
          127.4,
          23.0
         ],
         "text": "set pshmhelp-py.$1",
         "id": "obj-30"
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
          359,
          420.0,
          120.0
         ],
         "buffername": "pshmhelp-py.1",
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
         "text": "In Python:  poly = PShmBuffer(\"pshmhelp-py\");  len(poly);  poly[2].array;  poly[2].touch();  poly.append(samples, sr=48000);  poly.pop();  poly.wait().  poly[2] is the same memory as ShmBuffer(\"pshmhelp-py.2\").",
         "id": "obj-32"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-17",
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
          "obj-17",
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
          "obj-17",
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
          "obj-17",
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
          "obj-17",
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
          "obj-17",
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
          "obj-17",
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
          "obj-17",
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
          "obj-18",
          0
         ],
         "source": [
          "obj-17",
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
          "obj-17",
          1
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
          "obj-17",
          2
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-25",
          0
         ],
         "source": [
          "obj-21",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-25",
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
          "obj-25",
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
          "obj-25",
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
          "obj-25",
          1
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
          "obj-29",
          0
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
          "obj-30",
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
     "id": "obj-7",
     "maxclass": "newobj",
     "numinlets": 0,
     "numoutlets": 0,
     "patching_rect": [
      393.9,
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
          "bachmcp.pshmbuffer~"
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
         "text": "write <n> [file]: memory n into a sound file, as buffer~ does: the format from the extension (.wav .aif .caf .flac; none: .wav); no file: a save dialog; a bare name goes next to the patcher. writewave, writeaiff, writeflac, writecaf choose the format. Then written <n> <path> out the right outlet.",
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
          58.1,
          23.0
         ],
         "text": "write 1",
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
          98.1,
          170,
          83.3,
          23.0
         ],
         "text": "writeaiff 2",
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
          191.39999999999998,
          170,
          83.3,
          23.0
         ],
         "text": "writeflac 1",
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
          284.7,
          170,
          77.0,
          23.0
         ],
         "text": "writecaf 2",
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
          202,
          102.2,
          23.0
         ],
         "text": "samptype int16",
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
          142.2,
          202,
          102.2,
          23.0
         ],
         "text": "samptype int24",
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
          254.39999999999998,
          202,
          102.2,
          23.0
         ],
         "text": "samptype int32",
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
          366.59999999999997,
          202,
          114.8,
          23.0
         ],
         "text": "samptype float32",
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
          500,
          202,
          400.0,
          21.0
         ],
         "text": "@samptype: int16, int24 (default), int32, float32",
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
          10,
          245,
          1000.0,
          35.5
         ],
         "text": "writetofolder <folder> [wav|aiff|flac|caf]: every memory as <name>.<n>.wav (or that format), as polybuffer~ does; the folder is made if missing. Then written <count> <folder>.",
         "id": "obj-12"
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
          290,
          24.0,
          24.0
         ],
         "id": "obj-13"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          58,
          290,
          60.0,
          21.0
         ],
         "text": "wav",
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
          160,
          290,
          24.0,
          24.0
         ],
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
          188,
          290,
          60.0,
          21.0
         ],
         "text": "flac",
         "id": "obj-16"
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
          322,
          116.5,
          23.0
         ],
         "text": "opendialog fold",
         "outlettype": [
          "",
          "bang"
         ],
         "id": "obj-17"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 2,
         "patching_rect": [
          160,
          322,
          116.5,
          23.0
         ],
         "text": "opendialog fold",
         "outlettype": [
          "",
          "bang"
         ],
         "id": "obj-18"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 1,
         "patching_rect": [
          160,
          354,
          91.3,
          23.0
         ],
         "text": "append flac",
         "outlettype": [
          ""
         ],
         "id": "obj-19"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 1,
         "patching_rect": [
          30,
          386,
          154.3,
          23.0
         ],
         "text": "prepend writetofolder",
         "outlettype": [
          ""
         ],
         "id": "obj-20"
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
          430,
          229.9,
          23.0
         ],
         "text": "bachmcp.pshmbuffer~ pshmhelp-file",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-21"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 1,
         "patching_rect": [
          400,
          322,
          72.4,
          23.0
         ],
         "text": "loadbang",
         "outlettype": [
          "bang"
         ],
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
          400,
          354,
          253.4,
          23.0
         ],
         "text": "load 1 jongly.aif, load 2 cherokee.aif",
         "id": "obj-23"
        }
       },
       {
        "box": {
         "maxclass": "comment",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          663.4,
          354,
          250.0,
          21.0
         ],
         "text": "two memories to write",
         "id": "obj-24"
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
          130.0,
          23.0
         ],
         "text": "print pshmbuffer~",
         "id": "obj-25"
        }
       }
      ],
      "lines": [
       {
        "patchline": {
         "destination": [
          "obj-17",
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
          "obj-18",
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
          "obj-20",
          0
         ],
         "source": [
          "obj-17",
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
          "obj-19",
          0
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
          "obj-3",
          0
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
          "obj-4",
          0
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
          "obj-5",
          0
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
          "obj-6",
          0
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
          "obj-7",
          0
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
          "obj-8",
          0
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
          "obj-9",
          0
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
          "obj-10",
          0
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
          "obj-20",
          0
         ]
        }
       },
       {
        "patchline": {
         "destination": [
          "obj-23",
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
          "obj-21",
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
          "obj-25",
          0
         ],
         "source": [
          "obj-21",
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
      482.0,
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
          "bachmcp.pshmbuffer~"
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
         "text": "set_name <name> (or name): the object goes to this name. Memories already there: it joins them. None: its memories come along (<name>.1 ...), and the old ones are removed if this object made them.",
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
         "text": "set_name pshmhelp-b",
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
          190,
          133.7,
          23.0
         ],
         "text": "set_name pshmhelp-a",
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
          220,
          39.2,
          23.0
         ],
         "text": "info",
         "id": "obj-5"
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
          260,
          248.8,
          23.0
         ],
         "text": "bachmcp.pshmbuffer~ pshmhelp-a 2 500",
         "outlettype": [
          "",
          ""
         ],
         "id": "obj-6"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 1,
         "patching_rect": [
          260,
          160,
          72.4,
          23.0
         ],
         "text": "loadbang",
         "outlettype": [
          "bang"
         ],
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
          260,
          190,
          121.1,
          23.0
         ],
         "text": "load 1 jongly.aif",
         "id": "obj-8"
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
          300,
          103.9,
          23.0
         ],
         "text": "print written",
         "id": "obj-9"
        }
       },
       {
        "box": {
         "maxclass": "newobj",
         "fontsize": 13.0,
         "numinlets": 1,
         "numoutlets": 0,
         "patching_rect": [
          260,
          300,
          130.0,
          23.0
         ],
         "text": "print pshmbuffer~",
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
          85,
          345,
          300.0,
          21.0
         ],
         "text": "show pshmhelp-b.<n>",
         "id": "obj-11"
        }
       },
       {
        "box": {
         "maxclass": "number",
         "fontsize": 13.0,
         "minimum": 1,
         "numinlets": 1,
         "numoutlets": 2,
         "outlettype": [
          "",
          "bang"
         ],
         "parameter_enable": 0,
         "patching_rect": [
          30,
          345,
          50.0,
          23.0
         ],
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
          377,
          121.1,
          23.0
         ],
         "text": "set pshmhelp-b.$1",
         "id": "obj-13"
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
          409,
          420.0,
          120.0
         ],
         "buffername": "pshmhelp-b.1",
         "id": "obj-14"
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
          "obj-3",
          0
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
          "obj-4",
          0
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
          "obj-5",
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
          "obj-6",
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
          "obj-6",
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
          "obj-6",
          1
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
      563.8,
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