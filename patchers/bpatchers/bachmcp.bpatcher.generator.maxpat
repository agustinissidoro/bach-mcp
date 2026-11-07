{
	"patcher" : 	{
		"fileversion" : 1,
		"appversion" : 		{
			"major" : 9,
			"minor" : 0,
			"revision" : 5,
			"architecture" : "x64",
			"modernui" : 1
		}
,
		"classnamespace" : "box",
		"rect" : [ 573.0, 118.0, 824.0, 759.0 ],
		"openinpresentation" : 1,
		"gridsize" : [ 15.0, 15.0 ],
		"boxes" : [ 			{
				"box" : 				{
					"id" : "obj-13",
					"maxclass" : "message",
					"numinlets" : 2,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 756.0, 119.0, 155.0, 22.0 ],
					"text" : "presentation_rect 0 0 $3 $4"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-15",
					"maxclass" : "newobj",
					"numinlets" : 2,
					"numoutlets" : 2,
					"outlettype" : [ "", "" ],
					"patching_rect" : [ 756.0, 86.0, 111.0, 22.0 ],
					"text" : "route patching_rect"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-14",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 756.0, 51.0, 136.0, 22.0 ],
					"saved_object_attributes" : 					{
						"filename" : "bachmcp.gui.resize.js",
						"parameter_enable" : 0
					}
,
					"text" : "js bachmcp.gui.resize.js"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-10",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 2,
					"outlettype" : [ "", "" ],
					"patching_rect" : [ 242.0, 232.0, 297.0, 22.0 ],
					"saved_object_attributes" : 					{
						"versionnumber" : 80300
					}
,
					"text" : "bachmcp.translate @from json @to llll @transparent 1"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-11",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 2,
					"outlettype" : [ "", "" ],
					"patching_rect" : [ 242.0, 98.0, 297.0, 22.0 ],
					"saved_object_attributes" : 					{
						"versionnumber" : 80300
					}
,
					"text" : "bachmcp.translate @from llll @to json @transparent 1"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-9",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 582.0, 38.0, 54.0, 22.0 ],
					"text" : "deferlow"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-4",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 2,
					"outlettype" : [ "bang", "bang" ],
					"patching_rect" : [ 582.0, 66.0, 32.0, 22.0 ],
					"text" : "t b b"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-5",
					"maxclass" : "message",
					"numinlets" : 2,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 454.0, 157.0, 168.0, 22.0 ],
					"text" : "set_name #1"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-7",
					"maxclass" : "message",
					"numinlets" : 2,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 357.0, 71.0, 62.0, 22.0 ],
					"text" : "get_name"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-3",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 1,
					"outlettype" : [ "bang" ],
					"patching_rect" : [ 582.0, 10.0, 58.0, 22.0 ],
					"text" : "loadbang"
				}

			}
, 			{
				"box" : 				{
					"comment" : "",
					"id" : "obj-2",
					"index" : 1,
					"maxclass" : "outlet",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 242.0, 291.0, 30.0, 30.0 ]
				}

			}
, 			{
				"box" : 				{
					"comment" : "",
					"id" : "obj-1",
					"index" : 1,
					"maxclass" : "inlet",
					"numinlets" : 0,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 242.0, 43.0, 30.0, 30.0 ]
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-8",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 3,
					"outlettype" : [ "", "", "" ],
					"patching_rect" : [ 242.0, 157.0, 241.0, 22.0 ],
					"text" : "bachmcp.algo.generate #1"
				}

			}
, 			{
				"box" : 				{
					"embedstate" : [ [ "restore", "{\"title\":\"bachmcp.generator\",\"path\":\"Macintosh HD:/Users/danieleghisi/Documents/Max 9/Packages/bach-mcp/playground/algorithms/bachmcp.generator.js\",\"kind\":\"producer\",\"source\":null,\"params\":[{\"name\":\"length\",\"type\":\"slider\",\"range\":[4,60],\"step\":1,\"unit\":\"\",\"options\":null,\"value\":20,\"default\":20,\"kind\":\"\",\"grid\":1,\"display\":\"\"},{\"name\":\"factors\",\"type\":\"list\",\"range\":[1,9],\"step\":1,\"unit\":\"\",\"options\":null,\"value\":[3],\"default\":[3],\"kind\":\"\",\"grid\":1,\"display\":\"\"},{\"name\":\"phases\",\"type\":\"list\",\"range\":[0,59],\"step\":1,\"unit\":\"\",\"options\":null,\"value\":[1],\"default\":[0],\"kind\":\"\",\"grid\":1,\"display\":\"\"},{\"name\":\"pitches\",\"type\":\"list\",\"range\":[1200,12700],\"step\":1,\"unit\":\"mc\",\"options\":null,\"value\":[6200,6200,6500,6700,6900,7200,6100],\"default\":[6000,6200,6400,6500,6700,6900,7100],\"kind\":\"pitch\",\"grid\":100,\"display\":\"mc\"},{\"name\":\"rests\",\"type\":\"list\",\"range\":[0,1],\"step\":0,\"unit\":\"\",\"options\":null,\"value\":[0,1,0,0,0,0,0.93],\"default\":[0,0,0,0,0,0,0],\"kind\":\"\",\"grid\":0.01,\"display\":\"\"},{\"name\":\"assign\",\"type\":\"menu\",\"range\":null,\"step\":0,\"unit\":\"\",\"options\":[\"list\",\"random\"],\"value\":\"list\",\"default\":\"list\",\"kind\":\"\",\"grid\":0,\"display\":\"\"},{\"name\":\"tailored\",\"type\":\"toggle\",\"range\":null,\"step\":0,\"unit\":\"\",\"options\":null,\"value\":true,\"default\":true,\"kind\":\"\",\"grid\":0,\"display\":\"\"},{\"name\":\"period\",\"type\":\"slider\",\"range\":[60,1000],\"step\":1,\"unit\":\"ms\",\"options\":null,\"value\":200,\"default\":200,\"kind\":\"time\",\"grid\":10,\"display\":\"\"},{\"name\":\"seed\",\"type\":\"seed\",\"range\":[0,9999],\"step\":1,\"unit\":\"\",\"options\":null,\"value\":1,\"default\":1,\"kind\":\"\",\"grid\":0,\"display\":\"\"}],\"snap\":true,\"sourceMode\":\"nondestructive\",\"involutive\":false,\"selectionOnly\":true,\"bypass\":false,\"withinSelection\":false,\"pitchSnap\":3,\"timeSnap\":0}" ] ],
					"filename" : "bachmcp.gui.params.v8ui.js",
					"id" : "obj-6",
					"maxclass" : "v8ui",
					"numinlets" : 1,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"parameter_enable" : 0,
					"patching_rect" : [ 367.0, 212.0, 325.0, 740.0 ],
					"presentation" : 1,
					"presentation_rect" : [ 0.0, 0.0, 194.0, 366.0 ],
					"textfile" : 					{
						"filename" : "bachmcp.gui.params.v8ui.js",
						"flags" : 0,
						"embed" : 0,
						"autowatch" : 1
					}

				}

			}
 ],
		"lines" : [ 			{
				"patchline" : 				{
					"destination" : [ "obj-11", 0 ],
					"source" : [ "obj-1", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-2", 0 ],
					"source" : [ "obj-10", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-8", 0 ],
					"source" : [ "obj-11", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-6", 0 ],
					"source" : [ "obj-13", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-15", 0 ],
					"source" : [ "obj-14", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-13", 0 ],
					"source" : [ "obj-15", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-9", 0 ],
					"source" : [ "obj-3", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-5", 0 ],
					"source" : [ "obj-4", 1 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-7", 0 ],
					"source" : [ "obj-4", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-6", 0 ],
					"source" : [ "obj-5", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-8", 0 ],
					"midpoints" : [ 376.5, 635.2265625, 148.8828125, 635.2265625, 148.8828125, 136.3046875, 251.5, 136.3046875 ],
					"source" : [ "obj-6", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-8", 0 ],
					"source" : [ "obj-7", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-10", 0 ],
					"source" : [ "obj-8", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-6", 0 ],
					"source" : [ "obj-8", 1 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-4", 0 ],
					"source" : [ "obj-9", 0 ]
				}

			}
 ],
		"originid" : "pat-272"
	}

}
