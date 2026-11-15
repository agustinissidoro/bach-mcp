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
			100.0,
			100.0,
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
						200.0,
						22.0
					],
					"saved_object_attributes": {
						"filename": "helpstarter",
						"parameter_enable": 0
					},
					"text": "js helpstarter bachmcp.onnx~"
				}
			},
			{
				"box": {
					"border": 0,
					"filename": "helpname.js",
					"id": "obj-2",
					"ignoreclick": 1,
					"jsarguments": [
						"bachmcp.onnx~"
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
					"patching_rect": [
						10.0,
						205.0,
						95.0,
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
							1069.0,
							827.0
						],
						"showontab": 1,
						"boxes": [
							{
								"box": {
									"maxclass": "jsui",
									"filename": "helpdetails.js",
									"jsarguments": [
										"bachmcp.onnx~"
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
									"id": "obj-1",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "Turn the audio on, then play a file: every @hop seconds the last @window seconds are heard (the models must be downloaded: see the models tab).",
									"patching_rect": [
										10,
										100,
										900,
										21.0
									],
									"id": "obj-2",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open drumLoop.aif, loop 1, 1",
									"patching_rect": [
										30,
										128,
										238,
										23.0
									],
									"id": "obj-3",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open jongly.aif, loop 1, 1",
									"patching_rect": [
										260,
										128,
										222,
										23.0
									],
									"id": "obj-4",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open cherokee.aif, loop 1, 1",
									"patching_rect": [
										470,
										128,
										238,
										23.0
									],
									"id": "obj-5",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "0",
									"patching_rect": [
										695,
										128,
										22,
										23.0
									],
									"id": "obj-6",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 2,
									"numoutlets": 2,
									"outlettype": [
										"signal",
										"bang"
									],
									"text": "sfplay~",
									"patching_rect": [
										30,
										163,
										69.19999999999999,
										23.0
									],
									"id": "obj-7",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										"signal"
									],
									"text": "*~ 0.3",
									"patching_rect": [
										330,
										203,
										61.599999999999994,
										23.0
									],
									"id": "obj-8",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "ezdac~",
									"numinlets": 2,
									"numoutlets": 0,
									"patching_rect": [
										330,
										238,
										45.0,
										45.0
									],
									"id": "obj-9",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "audio on",
									"patching_rect": [
										385,
										248,
										300,
										21.0
									],
									"id": "obj-10",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 2,
									"outlettype": [
										"",
										""
									],
									"text": "bachmcp.onnx~ @model ced-base @window 3 @hop 1 @labels 4",
									"patching_rect": [
										30,
										210,
										441.59999999999997,
										23.0
									],
									"id": "obj-11",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "dict.view",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										30,
										300,
										420,
										300
									],
									"id": "obj-12",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"outlettype": [],
									"text": "print bachmcp.onnx~",
									"patching_rect": [
										470,
										300,
										160.4,
										23.0
									],
									"id": "obj-13",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "right outlet: bang after each answer,\nmodel <name> <kind> <sr> <window>,\nerror <words>",
									"patching_rect": [
										470,
										330,
										420,
										63
									],
									"linecount": 3,
									"id": "obj-14",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "One channel: mix several before the inlet.\nThe model runs on its own thread, never the audio one.",
									"patching_rect": [
										470,
										410,
										420,
										42
									],
									"linecount": 2,
									"id": "obj-15",
									"fontsize": 13.0
								}
							}
						],
						"lines": [
							{
								"patchline": {
									"source": [
										"obj-3",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-4",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-5",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-6",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-7",
										0
									],
									"destination": [
										"obj-8",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-8",
										0
									],
									"destination": [
										"obj-9",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-8",
										0
									],
									"destination": [
										"obj-9",
										1
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-7",
										0
									],
									"destination": [
										"obj-11",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-11",
										0
									],
									"destination": [
										"obj-12",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-11",
										1
									],
									"destination": [
										"obj-13",
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
						150.0,
						205.0,
						86.0,
						22.0
					],
					"text": "p clap",
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
									"maxclass": "jsui",
									"filename": "helpdetails.js",
									"jsarguments": [
										"bachmcp.onnx~"
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
									"id": "obj-1",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "A CLAP compares the sound with texts (@text, each atom one text). CLAP2 hears up to 30 s; live, a few seconds answer faster.",
									"patching_rect": [
										10,
										100,
										900,
										21.0
									],
									"id": "obj-2",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open drumLoop.aif, loop 1, 1",
									"patching_rect": [
										30,
										128,
										238,
										23.0
									],
									"id": "obj-3",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open jongly.aif, loop 1, 1",
									"patching_rect": [
										260,
										128,
										222,
										23.0
									],
									"id": "obj-4",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open cherokee.aif, loop 1, 1",
									"patching_rect": [
										470,
										128,
										238,
										23.0
									],
									"id": "obj-5",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "0",
									"patching_rect": [
										695,
										128,
										22,
										23.0
									],
									"id": "obj-6",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 2,
									"numoutlets": 2,
									"outlettype": [
										"signal",
										"bang"
									],
									"text": "sfplay~",
									"patching_rect": [
										30,
										163,
										69.19999999999999,
										23.0
									],
									"id": "obj-7",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										"signal"
									],
									"text": "*~ 0.3",
									"patching_rect": [
										330,
										203,
										61.599999999999994,
										23.0
									],
									"id": "obj-8",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "ezdac~",
									"numinlets": 2,
									"numoutlets": 0,
									"patching_rect": [
										330,
										238,
										45.0,
										45.0
									],
									"id": "obj-9",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "audio on",
									"patching_rect": [
										385,
										248,
										300,
										21.0
									],
									"id": "obj-10",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "text \"A drum loop plays.\" \"A man is speaking.\" \"Someone plays the guitar.\"",
									"patching_rect": [
										30,
										245,
										520,
										23.0
									],
									"id": "obj-11",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 2,
									"outlettype": [
										"",
										""
									],
									"text": "bachmcp.onnx~ @model laion-clap2-m @window 5 @hop 1 @text \"A drum loop plays.\" \"A man is speaking.\" \"Someone plays the guitar.\"",
									"patching_rect": [
										30,
										280,
										820,
										23.0
									],
									"id": "obj-12",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "dict.view",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										30,
										320,
										420,
										300
									],
									"id": "obj-13",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"outlettype": [],
									"text": "print bachmcp.onnx~",
									"patching_rect": [
										470,
										320,
										160.4,
										23.0
									],
									"id": "obj-14",
									"fontsize": 13.0
								}
							}
						],
						"lines": [
							{
								"patchline": {
									"source": [
										"obj-3",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-4",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-5",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-6",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-7",
										0
									],
									"destination": [
										"obj-8",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-8",
										0
									],
									"destination": [
										"obj-9",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-8",
										0
									],
									"destination": [
										"obj-9",
										1
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-7",
										0
									],
									"destination": [
										"obj-12",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-11",
										0
									],
									"destination": [
										"obj-12",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-12",
										0
									],
									"destination": [
										"obj-13",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-12",
										1
									],
									"destination": [
										"obj-14",
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
						290.0,
						205.0,
						104.0,
						22.0
					],
					"text": "p timing",
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
									"maxclass": "jsui",
									"filename": "helpdetails.js",
									"jsarguments": [
										"bachmcp.onnx~"
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
									"id": "obj-1",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "@hop: seconds between answers. @window: seconds heard each time (0: the model's, at most 10; up to 31). If the model is still busy at a hop, that hop is skipped: answers never pile up.",
									"patching_rect": [
										10,
										100,
										900,
										42
									],
									"id": "obj-2",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open drumLoop.aif, loop 1, 1",
									"patching_rect": [
										30,
										150,
										238,
										23.0
									],
									"id": "obj-3",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open jongly.aif, loop 1, 1",
									"patching_rect": [
										260,
										150,
										222,
										23.0
									],
									"id": "obj-4",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "open cherokee.aif, loop 1, 1",
									"patching_rect": [
										470,
										150,
										238,
										23.0
									],
									"id": "obj-5",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "0",
									"patching_rect": [
										695,
										150,
										22,
										23.0
									],
									"id": "obj-6",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 2,
									"numoutlets": 2,
									"outlettype": [
										"signal",
										"bang"
									],
									"text": "sfplay~",
									"patching_rect": [
										30,
										185,
										69.19999999999999,
										23.0
									],
									"id": "obj-7",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										"signal"
									],
									"text": "*~ 0.3",
									"patching_rect": [
										330,
										225,
										61.599999999999994,
										23.0
									],
									"id": "obj-8",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "ezdac~",
									"numinlets": 2,
									"numoutlets": 0,
									"patching_rect": [
										330,
										260,
										45.0,
										45.0
									],
									"id": "obj-9",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "audio on",
									"patching_rect": [
										385,
										270,
										300,
										21.0
									],
									"id": "obj-10",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "hop 0.25",
									"patching_rect": [
										30,
										270,
										78,
										23.0
									],
									"id": "obj-11",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "hop 1",
									"patching_rect": [
										120,
										270,
										54,
										23.0
									],
									"id": "obj-12",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "hop 3",
									"patching_rect": [
										190,
										270,
										54,
										23.0
									],
									"id": "obj-13",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "window 1",
									"patching_rect": [
										290,
										270,
										78,
										23.0
									],
									"id": "obj-14",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "window 3",
									"patching_rect": [
										380,
										270,
										78,
										23.0
									],
									"id": "obj-15",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "window 10",
									"patching_rect": [
										470,
										270,
										86,
										23.0
									],
									"id": "obj-16",
									"fontsize": 13.0
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
										270,
										24.0,
										24.0
									],
									"id": "obj-17",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "message",
									"numinlets": 2,
									"numoutlets": 1,
									"outlettype": [
										""
									],
									"text": "active $1",
									"patching_rect": [
										600,
										300,
										86,
										23.0
									],
									"id": "obj-18",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "@active 0: no answers (the sound is still kept)",
									"patching_rect": [
										630,
										270,
										300,
										21.0
									],
									"id": "obj-19",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 2,
									"outlettype": [
										"",
										""
									],
									"text": "bachmcp.onnx~ @model ced-base @window 3 @hop 1 @labels 3",
									"patching_rect": [
										30,
										340,
										441.59999999999997,
										23.0
									],
									"id": "obj-20",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "dict.view",
									"numinlets": 1,
									"numoutlets": 0,
									"patching_rect": [
										30,
										380,
										420,
										300
									],
									"id": "obj-21",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "newobj",
									"numinlets": 1,
									"numoutlets": 0,
									"outlettype": [],
									"text": "print bachmcp.onnx~",
									"patching_rect": [
										470,
										380,
										160.4,
										23.0
									],
									"id": "obj-22",
									"fontsize": 13.0
								}
							}
						],
						"lines": [
							{
								"patchline": {
									"source": [
										"obj-3",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-4",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-5",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-6",
										0
									],
									"destination": [
										"obj-7",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-7",
										0
									],
									"destination": [
										"obj-8",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-8",
										0
									],
									"destination": [
										"obj-9",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-8",
										0
									],
									"destination": [
										"obj-9",
										1
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-17",
										0
									],
									"destination": [
										"obj-18",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-7",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-11",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-12",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-13",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-14",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-15",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-16",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-18",
										0
									],
									"destination": [
										"obj-20",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-20",
										0
									],
									"destination": [
										"obj-21",
										0
									]
								}
							},
							{
								"patchline": {
									"source": [
										"obj-20",
										1
									],
									"destination": [
										"obj-22",
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
						430.0,
						205.0,
						104.0,
						22.0
					],
					"text": "p models",
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
									"maxclass": "jsui",
									"filename": "helpdetails.js",
									"jsarguments": [
										"bachmcp.onnx~"
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
									"id": "obj-1",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "@model takes a name of models/catalog.toml, or a model folder's full path. Download a model first, in a terminal, from the package folder:",
									"patching_rect": [
										10,
										100,
										900,
										21.0
									],
									"id": "obj-2",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "python py/main.py download laion-clap2-m",
									"fontname": "Menlo",
									"fontsize": 12.0,
									"linecount": 1,
									"patching_rect": [
										10,
										128,
										900,
										19.0
									],
									"id": "obj-3"
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "ced-base",
									"patching_rect": [
										10,
										160,
										200,
										21.0
									],
									"id": "obj-4",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "tagger",
									"patching_rect": [
										215,
										160,
										60,
										21.0
									],
									"id": "obj-5",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "16000 Hz, 10 s",
									"patching_rect": [
										280,
										160,
										130,
										21.0
									],
									"id": "obj-6",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "527 AudioSet labels (CED), what the MCP uses",
									"patching_rect": [
										415,
										160,
										480,
										21.0
									],
									"id": "obj-7",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "ced-mini",
									"patching_rect": [
										10,
										182,
										200,
										21.0
									],
									"id": "obj-8",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "tagger",
									"patching_rect": [
										215,
										182,
										60,
										21.0
									],
									"id": "obj-9",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "16000 Hz, 10 s",
									"patching_rect": [
										280,
										182,
										130,
										21.0
									],
									"id": "obj-10",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "the same, smaller and faster",
									"patching_rect": [
										415,
										182,
										480,
										21.0
									],
									"id": "obj-11",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "laion-clap-music-speech",
									"patching_rect": [
										10,
										204,
										200,
										21.0
									],
									"id": "obj-12",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "clap",
									"patching_rect": [
										215,
										204,
										60,
										21.0
									],
									"id": "obj-13",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "48000 Hz, 10 s",
									"patching_rect": [
										280,
										204,
										130,
										21.0
									],
									"id": "obj-14",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "LAION CLAP for music and speech, what the MCP uses",
									"patching_rect": [
										415,
										204,
										480,
										21.0
									],
									"id": "obj-15",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "laion-clap-general",
									"patching_rect": [
										10,
										226,
										200,
										21.0
									],
									"id": "obj-16",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "clap",
									"patching_rect": [
										215,
										226,
										60,
										21.0
									],
									"id": "obj-17",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "48000 Hz, 10 s",
									"patching_rect": [
										280,
										226,
										130,
										21.0
									],
									"id": "obj-18",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "LAION CLAP, all sounds",
									"patching_rect": [
										415,
										226,
										480,
										21.0
									],
									"id": "obj-19",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "laion-clap-small",
									"patching_rect": [
										10,
										248,
										200,
										21.0
									],
									"id": "obj-20",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "clap",
									"patching_rect": [
										215,
										248,
										60,
										21.0
									],
									"id": "obj-21",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "48000 Hz, 10 s",
									"patching_rect": [
										280,
										248,
										130,
										21.0
									],
									"id": "obj-22",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "the first LAION CLAP, small",
									"patching_rect": [
										415,
										248,
										480,
										21.0
									],
									"id": "obj-23",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "laion-clap2-m",
									"patching_rect": [
										10,
										270,
										200,
										21.0
									],
									"id": "obj-24",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "clap2",
									"patching_rect": [
										215,
										270,
										60,
										21.0
									],
									"id": "obj-25",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "32000 Hz, 30 s",
									"patching_rect": [
										280,
										270,
										130,
										21.0
									],
									"id": "obj-26",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "LAION CLAP2, medium: the best for its size",
									"patching_rect": [
										415,
										270,
										480,
										21.0
									],
									"id": "obj-27",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "laion-clap2-l",
									"patching_rect": [
										10,
										292,
										200,
										21.0
									],
									"id": "obj-28",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "clap2",
									"patching_rect": [
										215,
										292,
										60,
										21.0
									],
									"id": "obj-29",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "32000 Hz, 30 s",
									"patching_rect": [
										280,
										292,
										130,
										21.0
									],
									"id": "obj-30",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "LAION CLAP2, large: the best, the slowest",
									"patching_rect": [
										415,
										292,
										480,
										21.0
									],
									"id": "obj-31",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "The sound is resampled to the model's rate here, whatever Max's or the buffer~'s rate is. @samplerate feeds it another rate (with a warning: the model was trained at its own). @window is the model's own when 0. A tagger names sounds by its own labels; a CLAP answers with @text (similarity) or @embedding 1. Objects loading the same model share one copy of it.",
									"patching_rect": [
										10,
										328,
										900,
										63
									],
									"id": "obj-32",
									"fontsize": 13.0
								}
							}
						],
						"lines": []
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
						570.0,
						205.0,
						104.0,
						22.0
					],
					"text": "p answer",
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
									"maxclass": "jsui",
									"filename": "helpdetails.js",
									"jsarguments": [
										"bachmcp.onnx~"
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
									"id": "obj-1",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "The answer comes out of the left outlet as dictionary <name>: the object's own dictionary, filled again at each answer. Copy it with [dict] to keep it past the next hop.",
									"patching_rect": [
										10,
										100,
										900,
										21.0
									],
									"id": "obj-2",
									"fontsize": 13.0
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "{\n  \"model\": \"laion-clap2-m\",\n  \"kind\": \"clap2\",                   tagger, clap or clap2\n  \"samplerate\": 32000,               Hz the model was fed\n  \"duration\": 4000,                  ms heard\n  \"tags\": [                          a tagger: the @labels best labels, highest first\n    { \"label\": \"Drum kit\", \"score\": 0.71 },\n    { \"label\": \"Snare drum\", \"score\": 0.52 } ],\n  \"similarity\": [                    a CLAP with @text: the cosine to each text, in @text order\n    { \"text\": \"A drum loop plays.\", \"score\": 0.38 },\n    { \"text\": \"A man is speaking.\", \"score\": 0.02 } ],\n  \"embedding\": [ 0.012, -0.034, ... ]   a CLAP with @embedding 1: the sound's unit embedding\n}",
									"fontname": "Menlo",
									"fontsize": 12.0,
									"linecount": 13,
									"patching_rect": [
										10,
										130,
										900,
										199.0
									],
									"id": "obj-3"
								}
							},
							{
								"box": {
									"maxclass": "comment",
									"numinlets": 1,
									"numoutlets": 0,
									"text": "Right outlet: bang when an answer is done (after its dictionary); model <name> <kind> <samplerate> <window> when a model is loaded; error <words> when something fails (also in the Max console).",
									"patching_rect": [
										10,
										375,
										900,
										42
									],
									"id": "obj-4",
									"fontsize": 13.0
								}
							}
						],
						"lines": []
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
						710.0,
						205.0,
						59.0,
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
							1069.0,
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
		"lines": []
	}
}