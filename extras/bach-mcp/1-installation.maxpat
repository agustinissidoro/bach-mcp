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
		"rect" : [ 377.0, 149.0, 937.0, 780.0 ],
		"gridsize" : [ 15.0, 15.0 ],
		"boxes" : [ 			{
				"box" : 				{
					"id" : "obj-2",
					"linecount" : 5,
					"maxclass" : "comment",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 448.0, 421.0, 318.0, 87.0 ],
					"text" : "If installing for Claude, you might need to run an authorisation. This is the only step in which you need to use the terminal. The rest (downloading models, starting the server, etc.) can be done in Max through bachmcp.server\n"
				}

			}
, 			{
				"box" : 				{
					"fontface" : 1,
					"id" : "obj-12",
					"linecount" : 2,
					"maxclass" : "comment",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 46.0, 43.0, 342.0, 33.0 ],
					"text" : "bachmcp relies on a specific folder structure. The main folder needs to be placed inside /Max 9/Packages"
				}

			}
, 			{
				"box" : 				{
					"fontface" : 1,
					"id" : "obj-11",
					"linecount" : 4,
					"maxclass" : "comment",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 64.0, 716.0, 486.0, 60.0 ],
					"text" : "To uninstall bachmcp, simply remove the folder from Max's packages.\n\nIf you also had a Claude installation, you will need to remove the entry from Claude manually. Leaving it does no harm, but Claude will try to connect to it."
				}

			}
, 			{
				"box" : 				{
					"fontface" : 1,
					"id" : "obj-10",
					"maxclass" : "comment",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 46.0, 89.0, 342.0, 20.0 ],
					"text" : "To install bachmcp you need Python 3.11 or newer"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-9",
					"linecount" : 8,
					"maxclass" : "comment",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 305.0, 571.0, 318.0, 114.0 ],
					"text" : "Both versions of installation will create a venv using any Python version on your machine. Be aware that, if you have Conda installed and it creates a venv using Conda's Python version, whevener you remove Conda you will have to do another installation.\n\nThe Claude installation will try to automatically set the MCP. If it fails, you will have to do it manually."
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-8",
					"linecount" : 4,
					"maxclass" : "comment",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 448.0, 334.0, 318.0, 74.0 ],
					"text" : "Check the console to follow the installation state. If the installation succeeds, you can continue either with downloading a model (check 2 - downloading a model) or using it with Claude.\n"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-7",
					"linecount" : 3,
					"maxclass" : "comment",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 305.0, 132.0, 318.0, 47.0 ],
					"text" : "Choose only one:\n1) \"install\" will install both, claude and local options\n2) \"install [arg]\" will only install that option"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-6",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 0,
					"patching_rect" : [ 408.0, 360.0, 32.0, 22.0 ],
					"text" : "print"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-5",
					"maxclass" : "message",
					"numinlets" : 2,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 455.0, 203.0, 67.0, 22.0 ],
					"text" : "install local"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-4",
					"maxclass" : "message",
					"numinlets" : 2,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 359.0, 203.0, 78.0, 22.0 ],
					"text" : "install claude"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-3",
					"maxclass" : "message",
					"numinlets" : 2,
					"numoutlets" : 1,
					"outlettype" : [ "" ],
					"patching_rect" : [ 305.0, 203.0, 39.0, 22.0 ],
					"text" : "install"
				}

			}
, 			{
				"box" : 				{
					"id" : "obj-1",
					"maxclass" : "newobj",
					"numinlets" : 1,
					"numoutlets" : 3,
					"outlettype" : [ "", "dictionary", "" ],
					"patching_rect" : [ 305.0, 302.0, 122.0, 22.0 ],
					"text" : "bachmcp.server local"
				}

			}
 ],
		"lines" : [ 			{
				"patchline" : 				{
					"destination" : [ "obj-6", 0 ],
					"source" : [ "obj-1", 2 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-1", 0 ],
					"source" : [ "obj-3", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-1", 0 ],
					"midpoints" : [ 368.5, 288.0, 314.5, 288.0 ],
					"source" : [ "obj-4", 0 ]
				}

			}
, 			{
				"patchline" : 				{
					"destination" : [ "obj-1", 0 ],
					"midpoints" : [ 464.5, 288.0, 314.5, 288.0 ],
					"source" : [ "obj-5", 0 ]
				}

			}
 ],
		"originid" : "pat-6",
		"dependency_cache" : [ 			{
				"name" : "bachmcp.server.config.js",
				"bootpath" : "~/Documents/Max 9/Packages/bach-mcp/javascript/server_utilities",
				"patcherrelativepath" : "../../javascript/server_utilities",
				"type" : "TEXT",
				"implicit" : 1
			}
, 			{
				"name" : "bachmcp.server.download.js",
				"bootpath" : "~/Documents/Max 9/Packages/bach-mcp/javascript/server_utilities",
				"patcherrelativepath" : "../../javascript/server_utilities",
				"type" : "TEXT",
				"implicit" : 1
			}
, 			{
				"name" : "bachmcp.server.maxpat",
				"bootpath" : "~/Documents/Max 9/Packages/bach-mcp/patchers",
				"patcherrelativepath" : "../../patchers",
				"type" : "JSON",
				"implicit" : 1
			}
, 			{
				"name" : "bachmcp.server.modelcheck.js",
				"bootpath" : "~/Documents/Max 9/Packages/bach-mcp/javascript/server_utilities",
				"patcherrelativepath" : "../../javascript/server_utilities",
				"type" : "TEXT",
				"implicit" : 1
			}
, 			{
				"name" : "bachmcp.server.playground.js",
				"bootpath" : "~/Documents/Max 9/Packages/bach-mcp/javascript/server_utilities",
				"patcherrelativepath" : "../../javascript/server_utilities",
				"type" : "TEXT",
				"implicit" : 1
			}
, 			{
				"name" : "bachmcp.translate.mxo",
				"type" : "iLaX"
			}
, 			{
				"name" : "shell.mxo",
				"type" : "iLaX"
			}
 ],
		"autosave" : 0
	}

}
