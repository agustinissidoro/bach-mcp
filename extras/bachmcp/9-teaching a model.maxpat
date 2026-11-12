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
                    "patching_rect": [ 919.0, 558.5, 855.0, 422.0 ],
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
                    "data": [ 9019, "png", "IBkSG0fBZn....PCIgDQRA..ALE...fOHX....fkVgOQ....DLmPIQEBHf.B7g.YHB..f.PRDEDU3wY6clGWUUm9G+8cCvDEzbCbAbkQD2aQ.EbIwDxlTmoTpzbWbWImIsrbISbxTwTDb2w0JM6moliNSAZn1tJhf3JBJBnwp20y8982efbiqrcIob6790q6Kfy1yy44d347878786yGE50qW.fBEJnr94c+6VWFJf6Zwk01UUVuLxHiLOrhx62NfLxHiLOJf562NP0AlMaFc5zgACFvhEKVWtZ0pwImbBGczQTpT99FxHiL+wwiDIS0pUKa8Rl3B50fRkBqKWAPucMe5nyVPsZaOUUpTIN5niTiZTCToR0exdrLxHyiZn3Qg9LMyLyjobJKnRgBTfvpsTn.To.ThRTThjrXAr.z5mvLStc0hZUqZ8Ghec2XznQhN5nIwDSjYLiYvMu4MYG6XGrrksLN+4OOaaaaiEtvE9mhuHiLxT8xiDsLURRhLxSGeVvdPCqoF6ZexRqId0u5pLROU9mVxz8t28xN24NYVyZVzvF1PxN6rQRRB.t0stEwFar+o3GxHiLU+7HQxTgPPCpgir9qZFIKlsq8QsRv0Z3.lMaeae0AolZp3qu9x.Fv..ft28tS26d2+Sy9xHiL+wwCruUlryN6xb4FLX.CFLTpk6ga0g70aAsFsuO4q2BMqg0AgPTFVAzqWOAGbvrqcsK9a+s+F95qu7lu4axMu4MAfXiMVF0nFEe3G9g3me9w+8+9eQHDDSLwv.G3.If.BfYNyYRVYkE.L24NW9rO6y3HG4HDbvAy4O+4I93imgMrgUl1+l27l7Vu0aQ26d24UdkWg8rm8XccYjQFL4IOY5V25F8u+8mMtwMVtmGxHiL+4fRJu+G793+adwKdQ17l2Lm8rm0lkmc1YyZVyZHt3hqT6iAyvsMYFsRV31lLWgeJdaLTAMJ0hEKjVZowJW4JY5Se5DczQSVYkEyXFy.nnW502+8eO5zoiniNZdpm5oX8qe8rksrEl9zmNQEUTnUqVlvDl.RRRDVXgQe5SevWe8kUu5UiGd3A5zoiLxHiRYaylMyTlxTPqVsrl0rFF1vFFu+6+9bzidT.XwKdwnToR9hu3K3cdm2gMu4MSBIjv8PDWFYj4dkGHeL+V1xVRG5PG3.G3..f2d6MFLXfCdvCB.ctyctT6iAil.EJQABD28aF6tv51HrTgaG.SaZSC+82e.3ce22kANvAxMtwM..mc1Yd629ssNZ.1291GSYJSg.BH..XAKXADXfAxEu3EwKu7BWc0U.vCO7nBs4UtxUHgDRf8su8gqt5JMtwMld0qdwgNzgnG8nGTXgEhZ0pQqVs3u+9K2WqxHyC.7.YxT.BJnfPud8bfCb.LXv.m4LmgbyMWFxPFB0u90uTauAIKkXzEXOMqVXWISaQKZg0eu3jfokVZ.PcqacslH0jISbwKdQ7zSOst80st0EWbwERM0TwKu7xN7oh3xW9x.PngFp0kke94iO93C.L6YOaVxRVBuzK8RT+5WeF7fGLicrisTC+KYjQl+7nz+2mfRMjmteQ+5W+Hu7xi+2+6+giN5X4lHE.IIyfRyfB6rafE2Y7QUIbsqcM5PG5..Vejb2c28R0mtZzngl0rlw0u90strBJn.xKu7nwMtw1mOcGJd6O7gOLOwS7DkZ8snEsvZ2HbzidTd629swM2biANvAVkriLxHS0G2Cu.p+36TUGczQd4W9kwe+8uBSjBfQIiXxfILYzf88wfILJYrR8gUrhUv4N24HiLxfO7C+PZUqZEt6t6k4116d2aV8pWMIkTRjYlYRDQDAt6t6z5V25pz4cqZUqnwMtwr3EuXxLyL4pW8pDVXgQzQGMVrXgW60dMV6ZWKJUpj10t1gyN6LN3fCUIaHiLxT8xC7OWniN5H95quU31nPgBLnSWUtA0B.EJpQEtMgDRHLxQNRqOl8xW9xKyI1..SYJSgBJn.F4HGIEVXgzoN0IhIlXpvDckbZtVbWFnQiFhN5nYNyYNz291WDBAAETP7pu5qhRkJY7ie7L24NWVwJVAN3fCLnAMHdtm64phm8xHiLUmnPuN8BTThY9zclYSkbFNU1y.Jf6Z42ulATYkUVL7uJcT5jZjjrT48EpBknVsRrnWhM2+lPCZPCJ0lnUqVd1m8YYW6ZWzpV0JzoSGN6ry1k+X1rYLXvPY9H5UUzpUKJUpDmbxoRst7xKOb1YmkmNrxHyC.7.eKSsGb1YmIldUODBgcWPSrXwBJTnvtRPpRkJ6NQZwae0QhTfJ733hKtTsXCYjQl6c9c2xzxZ42uZYpEKVvrYyHIIgPHpzAvdQyaeEnVsZToRUYl.1hEK7i+3OhO93S0VhQYjQlGc4QhjoxHiLxb+lGXmNoxHiLx7vDUXelZ1rYrXwBVDBDVDfhhJpHJ.DJT.k3woqzVkVzFUM3xxHiLx7fGkYxTKBAlkLgjjYDkn9fd+b95KiLxHyCxTpjoVDVPRRBSRR1V.ne.ZlQIiLxHyCZTpjoEmHE3wtjmFMZDEJUhEoRniTZzfREJPoR4FlKiLxT9XSxTIyl+sDo2MOhmX0rjDlQI0PiCXV0ukLUXQfyN+DXxjILXzn7HRPFYjoLwl2luvhvlWpziaHLKgdCFvfd8+1GC541Z0gFMZPiZGp1umR94mOSdxSlDSLwJcaO9wNFyXFy.SFq7ZJPUgO8S9D9+9hu3289mTRIwbm6bq9bnRf8Del8rlEW7hW7d1V+QEeebgkurkwN1wNte6F22vljoVrSI+3QYTpPAJJtxSoTInQMlLYB85MhiNpAK1QklppRU4edkJumb3dfykRJbgKbge26eN+5uZsvU+GAkL9jbxIyjlzjrYhY7Mey2Pd4kW0hs9iH993BEO4YdbEadLeKOF2pT.TnPI4kWtHDfy0t1H907gKjA2xa2oFZziIiFvwZTCpgiNTsU6PqcsqMQGSL1015qe9gu94W0hceXg6N9TXgEx2+ceWQCQup4tb4ww3a0IyH7vue6B2WwlLBOtqiPZz3.G+3GGgEAlUq.etoE77K9INwq2Ebot0gaq81DTeChJatNXPudF5PGJCZvCluXO6gbxMWF2XGKtVm5vJ+3OlaqUKgDbvL0oMMDBAuxK+xrnHhf1zl1PDKZQTaWbgTRIEN8oNE95qu7FiXDz5V2ZN9wNFaXCaf0tt0UkrgJUp3Dm3Dr5nhhKdwKRS8vCF8nFE8oO8wtiMYkUVrrktT99u+6wImbh9129xDm3DQSYTQrNz+4+v11113JW4Jzyd0KpiqthiN4DgEVX.E83zacqakyblyf2d6MCaXCyZRrHVzh3IpYMIwybFN8oOMwFWbD5PGJKJhH3V27lL+4Oe.XPCbf7Zu9qye6u82.fSepSwxV5RIszRCe80Wd624cvYmclHVzhnV0t1b1ydVN8oNE94meLpQOZ9nkrDRLwDwGe7g4Nu4QiZTirI9BvINwIXK+6+MIjPBzhVzBF23FWklr8l27lDYjQxINwInVN6L8qe8iQNpQgFMZPHDrg0udNzgOL+5u9q7LO8Syzl9zo90u9UouOkLYhgNzgxq+5uN6Z26lLt90oacqaLivCm5Uu58a9wxWNm369NpScpCOWe5CidLiAkJUhIiFYsqac7UG3.nUqV7yO+XFgGN0oNEoIZabCafu5q9JzpUKAFXfL0oNUbzIm3nG4Hr8suc7xKu3K+xuj2YNygd0qdY8b+C+W+Kbyc240dsWqRsQkEGd4W4U3+au6k7xIGB4EdAF4HGI0nFUbEd69Mxy.pRfEKRnQiFxN6r4pWKct5+83nxs5Sa0pgi8ieGcricxtZ8tEgfzSOchK1XYgevGPXgEFKYIKgcticvh+W+Kl8rmM6bm6jSdxShPHHszRCSlLA.+5u9qr8ssMBIjPX4Ke4jat4xF2vF..c50aUxTpJ131291L+4MOBLv.Yy+6+M8tm8jY8VuE4me91crI5niFc50STqd07Nuy6vd1yd3PG5PkZ6N0IOYQkNvfBh0st0QSZbiY6ae6jSN4..ojRJLyYNSdpm5oXcqe8zst0Ml4LmIIkTRVO++zO4Sn+8u+roMuYTpTo03SG5XGYhSbh.vxiLRBJnfrZ2CbfCvaNyYx6+9uOm7jmjst0sZywanCYHrxUtRRHgDX7iab7JCYHr9MrAxI2bYqaYKkJ9lRJovaFd3zoN0IV25WOADP.L0oNUR+NprPYgjjDyX5SmbxIGV9xVFSe5Smcs6cym7IeB.r4MsI1wN2ISYxSlku7kiVc5XZSaZXxjopz2mEusQGczLoINQhLxHI6rylY8VukU+X5SaZTPgExxW9xYZScprqcua1v5WO.70ey2vd1yd3e8geHqa8qmryNa1912N.r0stU9jO4SXFgGNKZQKhSc5SyGtjk..Z0oie5m9IzoSGQFYjzktzEaN+yM2bs1cKUjMrm3vA1+94cl8rYl+i+Ae9t2MwGe71wUo2e4QhpFU0EVDBP.OQMeB7vsVRah8FX5MBBSe9Aolt6HpTprnWRmcdKnwL1whWd4EsoMsgUDYjD5q9pz111VZaaaKd3gGbszS2ZU7ujzum+4ou8su.vK+JuBu8rmc41Wd1iM5ZW6JG3q9JDBA5zoifCIDV6ZWKW9xWlN1wNZywKwDSDsZ0Z8uqe8qOd5om7tu66BTj5vV+5Webyc247m+7kxe913imt4qu7Zu1qA.stMsge7G+wea8G8nz912dFwHGYQqu0slu+G9AN5QNBssssE.BNjP3ktipAT7MY.nl0rlzH2bC.ZVyZlMEnlQM5Qa8bo28t2btycNqqK3fClt2id..cuG8fBKn.5cu6M.7b8oOjvYNSoOON5QocsqcLlwNV.nMsoM3c6ZGp0nACFLvoO8osY68xKuH6ryljSNY1292u0x53pW8pQuNc.vA9puhvBKL7+Nx68blyb346W+3JW9xzjl1T.666Su81a.XxSdxVao7aMqYwPGxPHyLyjBKrPN24NGGX4K2ZKUmPXgwV25VYziYLb6aeaDBA4me9zpV1Ra5Fkcuqcwq85uNsqcsC.FwHFAydVyhYMqYATTEZal+i+Qk1MWUjMrm3v3G+3oc93CsC3q+5ulicri8.eM6UNYZIvhYybasZom8oO37skPYAGlamatTibzS+5oub1ykLA3u8qy8EKfdJTn.MZzPMKQ0mxQGcrb6VkFVh5qZ8qe8wnQiHJm27k8XCSFMxpiNZ16d2K50oiZW6ZWzFTF1eqaYK1jjr+8u+LpQOZhKt3XUqbkjZpoRscwExK2boycpSkZ+uQFYfaMpQ1rrF2jlX82uzktjM5pE.srEsvptWAP8dxmrLOWqHJoJLzH2biTu5Us920oN0w5uqQsZpYIJmhNTNeOboKcIZYKaoMKqacqa.PlYlIKNhHrYcyadyiLyJKb1Ymso931pV0JfhdIZW4xW1FwTrt0stTaWbgTu5UslDopbMSI0arlcm8O8zSm7xKOpUspk0Do.3gmdxUu5UwfACDRHgvUt7kY1yZVXvfABLv.YhSZRT+5UOt90uNe7JVAaZSaB.J3NO8RwRbdcpScrq2WPEYC6INTuR98YiZDWK8zqTad+FahJJTn3w79MUP.AD.0xkZCNXDKCKHdBSBdhQ9Wg11TZhZEHIIgCZd3RhP9tu66XGae6DSLwfOsu8nUqV5cI5qqRxhtqjDPQSlg2cNyggO7gyPCMTpQMpAgOiYfiN5Xo1113kW7k6cuXPudbzImPqVs7y+zOwy7rOK.zzl1TRJ4jsYet10tFs7NIcrWrXwhcW6Z+8PyZVy3z2k7YmVZogqt5JMrgMjcs6cWp8QSJoPgEVH+5u9qT25VW.3V25VXxnQZjatQSaZS4FkPZuKnfBH+7xqbkAmJiqe8qiOsu8.EkfG.2byMpUspUQG67y25MNyHiLnQMpQV+NaFgGNSYpSkjSJIV5RWJQDQDrhUrBZRSZBicbiim+4e9eW9Tw3niNVt1n5NN7fB1b0nxG6GP5EUrnMYzDFUCleI+PauZO58oonyhDlLZpxODO.h46zpVUpUSAET.qwNG8.Ei3NC4EkJUhYylI1Xikie7iWlaa+e9mG850SXgEFqZUqhwM1wZyip2Me8kSb7iy99xujbxIG1+92Oe629sUpzzTLEmj53G6XnWu9pz4QUA+7yO9we3G3y+7OmbxIGNvAN.CdPCxZepVVzbO8jl0rlwR9vOjabiaPJojBi3MdC1291G.DPfAxZVyZH4jSlrxJK9nO5inQMpQVa8ZUknhJJNeJovMxHCV1xVFMuEs.2byMZtmdh6t6NezG8QjYlYRJojBwDczV6ZiMswMxTm5TI2bykV05Viat4FNdmWjXfAFHqasqkTRIExO+7YMwDCCeXCCKkwSFke94yBW3B4RW5RkZcUjMptiCOnfMsLUoRUOVONwTnPIW3BmmBKn.TnPAN5TMPudsXwbQsBxM2cmZzvFYGGmJ+lREWfpqr8s796phM51y9rz6d2aFwa7F.Xs+JsW+0QmbhvCObV1xVFQEUTzwN1Qdlm8YsY+JtUh0q90m0r10RbwEGomVZL9wOdN5QOp0WbWG6XG4ceu2i0s10x7m+7wc2cm4Lm4Pm6bmsKeoEsnEzm9zGBO7vYBSXB7FiXDk49UdwoxKte26mOsu8L24MOV6ZVi0QXwrl0rpPwQTiCNvxiLRl+7lG+0W7EQkJUz2fBhPe0WEnn9srvBKz5O6PG5.e7JWIN3fC10MFtae+46e+Y7gEFEje93s2dyRVxRJp6AbvA93UtRl+7lGC3EdAb1Ymo28oOVe4c8O3f4G9geff6e+QgBEz912dd2268JxGmvDnfBKjwOtwQgEVHd17lybdm2w52ukz925V2h+yAOH94mekpqapPaTEiCU12YOnfMEGZIylwXIFfzk7DvleunEX6A5g7RvmYIILJYAUpThNcZQsZMXQHPoBEnRcQCb+ZVyZhPHvhjDZz7vW2MqSmNTnPQYpmT1CRRRnUq1eqOWKCRJoj3.6e+LpQOZb0UWovBKjAOnAwHF4HYHCYH1rsEje9TqJ3XUQXxnQToV8enOpewTxGW1dQqVsnQs5xbniIIIgISl9cOTezoSGAFP.r0ssMZYKaYEpOYZ0pEGbnrGWz50qGKVrTlJIQQSTE8TqZUqJzWLa1rUMHariYL3u+9yvuyMsqLabuFGdPCahvpUoBgZ0k+7y+QXTpREF0pEknDEnBy2oXmXFAlkzAnhamedHnh0koGj4d8hV0pUWoIU7vCO3zm9zL3AMHZdyaNImbxzxV1RqiNgRxu2Do.kYRp+nnplHEp3qQTqVc01j9nxzmrJxOpnappQiFznQicYennQVvYNyYXVyd11sMpNiCOHPojsDgP7akfuGiZYpLUeXxnQN6YOKYlUV3tatQa7xqJTtqkopgEKV3m+4eFu816GXtw9oN4Io0soMOv3O2OnL0.JKHvrjToKNzEuSEs.aOPxISkQFYdLlxrM1JUn.UZb.UpreYKQFYjQlGmoB6vBUpTgJUpJ625LT0acpbKSkQFYdDE44luLxHiLUCHmLUFYjQlpAdzYbIbOhPHH+BJ.TpDgzuMwETqQCpUoFmbR9sQKiLxT9HmL8NX1rYLYApgF0XVwu0fcyVD3bMc.KVr7PyLwPFYj4OejeL+RhEykqFPoToRrXo5ezKjWd4w3F233LkQYf6tI93imIMoIYybcu5fsu8sym+4e9u68+rm8r71u8aWM5Q+wPUIVKSoI2bykwN1wZs1yJisHmL8tnhz.phlpoFp1qrV1axwhmPEU2jbxISJojxu68+V25VDarwVs3KSYJSge9m+4pkiUYQ08MhdbCIIoxrnmHi7i4aC1qFPoVsK10TsydvEWbgMbmJoekQ26d2o6c29qmpOLxO9i+H+0+5e8OjicUIVKSowUWcUN9UAH2xzRfFMZ33G+3b7icLN3+8+v0NT7nYoeFmHtixO+y+Dm36+t6TFwp3vld85I3fClMsoMwK7Bu.96u+r8sucN3AOH8qe8C+82eV7hWLlMaFylMSHgDh0JC+BVvBXEqXELgILA70WeYlyblVa0X7wGOCaXCqJaC.N1wNFCYHCgt10txfG7f4vG9vUoXiPHXMqYMLfAL.5Se5CKbgKrbqzQ27l2j25sdK5d26Nuxq7Jrm8rmRcbF3.GH94meLsoMMtwMtARRRDRHgPAET.KXAKvZENZAKXArzktTFwHFActycFIIIt4MuI+y+4+j.BH.doW5kHpnhxZqkhM1XYzidzDUTQQO6YOIzPCk8u+8CPoh0kmuTYbricLF8nGMO8S+zLzgNT91u8astt3iOdF8nGMO6y9rLpQMJaV2BVvBHxHijwLlwvS8TOESe5SmyctywHFwHnqcsqLxQNRq1u3yiMsoMQfAFHO+y+7DUTQY8ohDBAwDSLLvANPBHf.XlybljUVYY0VwEWb72+6+c5ZW6JgFZn7K+xuTJ+uacqaLwINQqwihulZcqacDbvAy+7e9Os47VRRhfCNXqWOVQ1nxhCk203OTidc5E50qWXvfAgACFDFMZTXznQgIilDlLUzGIIoR8wrjjvrYy17whEKU3mGjwjIShbxKewms6cKVdjqP79KaIhuXPSVj2viP7Sw7ohYMu2SjTJmWbybxUXznTEdrt8susvGe7Q75u9qKRJojD6bm6T3iO9HBMzPEIlXhhCcnCI7wGeDe+2+8BSlLI7wGeDIjPBBgPHl5TmpnKcoKhCdvCJ9ke4WDiZTiRDd3gKDBg3vG9vhm64dtprMJrvBE8pW8RDSLwHN+4OuHpnhR3iO9HxM2bEBgPLm4LGwhVzhpvyoMrgMHBLv.EwGe7he4W9EwfG7fEu669tBgPHNxQNhvO+7SHDBgjjjXnCcnhIO4IKRLwDE6ae6SzktzEwQNxQDBgPr10tVgu95q3a9luQbxSdRw3G+3ECYHCQXwhEwUtxUDO0S8ThssssIt10tlMwicsqcIRJojDRRRh+9e+uKBKrvDIjPBhibjiHBHf.Dqd0qVHDBw92+9E93iOhEu3EKRN4jEqXEqPzktzEQgEVXoh0kmuTQjbxIK5RW5hHpnhRjbxIKhIlXD93iOhTSMUqqaMqYMhyctyIV25VmnKcoKhDSLQqmKOyy7LhXiMVwO+y+rnW8pWht0stIN7gOrHojRR7RuzKI9fO3Cr47XRSZRhyblyHNzgNj0XSw9t+96uHt3hSjPBIHlvDlfXvCdvBSlLIxO+7EctycVryctSQFYjg3i+3OVDRHgHLa1rHkTRQz0t1UwF23FEImbxhEtvEJ5cu6sHu7xy50TCZPCRDe7wKRKszr4b2nQiVieUjMrm3P4cM9CyH+X9k.6VCnrSlvDl.+k+xeAu7xKVxRVBCe3CGu81a71auwSO8jzSOcq0wyRRHgDB8qe8C.BMzPYlyblkacl0drwS+zOMe8W+0V0.pALfAPTQEEW9xWlNcWROxYNyY31291V+6FzfFPyady4S+zOkgO7gaUafF6XGKgGd3V0Fph4JW4JjPBIv9129vUWckF23FSu5Uu3PG5PzidzC1291GSYJSgd1ydBPQh11oNElMaFO7vCznQCMrgMzlpt9K9huHCdvCF.tvEt.IkTR7Mey2XUVNlxTlBabiajwO9wCbmp79LlApUqFO7vC1zl1D+zO8S32cornkmuHIIQxImbYFGhKt3nCcnCVUZUu7xK7wGevAGbfCdvCRm5TmXLiYL.EoaTm3DmfXiMVq51z.Fv.Hv.CDnnBwbAETfUsMJnfBhScpSYiO99u+6iKt3BsqcsiKcoKwgNzgHzPC0puGP.A.TTq8BLv.4hW7h7jO4ShISlnfBJ.mbxIlzjlDSZRSBnH8TpksrkLv6nwVSXBSfcricPBIjf0qECO7vKUr5twfACkqMhKt3pz3P4cMdwUgpGFQNYZIn5VCnJV6grpmO0rlVWmSN4T49hrZTIzPoF1vFhQiFK2N82drgISl3i+3OlO+y+bzoSGt3hK.kszduwMtQaDitALfAvHG4HI8zSmktzkx5tiLHWrxllc1Yay9WrVNEZngZcY4me93iO9fISl3hW7h1THgc0UWslbo7nj56zUtxUJk9F4omdRpolJFLX.nnXVwk1MmbxIpW8pm00ULUluTVwgwMtwwEtvEJUEgu3DOW3BWnT5FUqZUq3hW7hV+6hUJ.nntUpjkOu6VimZPCZf0uqfhJL1adya1puWRMfpt0st3hKtPpolJd4kWDQDQPLwDCQFYjz912dF6XGK8rm8ju9q+ZN6YOKAGbv13mW+5W2ZxzmzNzfq5Uu5Ut1vdhCk203xISejA6SCndXiicriwV1xVXiabizgNzAzpUa4JSHezG8Qk4xaZSaJSbhSjPBIjRstRJ.eMtwMF.N7gObYVN17vCOHszRim4YdFfhZgS5omNMu4M2Zgdt7tISw9QAET.4kWdVSzb8qecb2c2KSMop7PiFMUnuTdwAO8zSN4IOoMKK0TSk5V25hGd3AIlXh1rtzSO8Jr57WQjc1YiVsZsFGu10tFd5omnQiFZVyZFW+5W251VbLo33eHgDBgDRHjQFYvV1xVXxSdxbjibD5QO5AMpQMhHiLxRYuRpJs1CkmMptiCOrP4+lTdrbro+HpFPcmtHPsZ0je94ypV0ppxGid26dypW8p4bm6bjWd4QTQEECYHCoTsXtUspUz3F2XV7hWLYlYlb0qdUBKrvH5niF.5ae6KqZUqhyblyPlYlIye9ym27MeSq6eiZTi3Dm3DV0e86lVzhVPSZRSXwKdwbiabCN24NGqZUq52kL.WY9RYQ26d2469tuiO6y9LxImb3K+xujW3EdAxHiLve+8m3iOd9hu3KHmbxg8t28RbwEG96u+UYeCJ5lJQDQDjUVYwIO4IYCaXCVer9h+9HojRhLyLShHhHvc2cmV25VShIlHu3K9h7C+vOPCZPCvau8FMZzfJUpve+8mibjiv9129Hu7xiicriQvAGb4N1KS0Ulx..f.lmDQAQU2vF1.6cu6sTKuxrQ0Yb3gEjaYZInHMfJkGn0.pxRKdpLa3me9wy8bOGCcnCEnn96rp5uScpSkBJn.di23MnvBKjV1xVx7l27r5OE+3YZzngniNZlyblC8su8EgPPPAEDu5czAoINwIR94mOicrikBJn.7xKuXwKdwVONCaXCiHhHB9ke4WX26d2kx2t6iuyN6LAETPLsoMspz4i83KkEcnCcfO3C9.hJpnX9ye93hKtv68duGsoMsAnn93b0qd0Lm4LGZRSZBye9ymt10tVl9UkMi5ZRSZBN4jSzm9zGbzQGo+8u+L5QOZfh5m3BJn.F4HGIEVXgzoN0IhIlXvAGbf1111Ru5UuX7ie7XznQdxm7I4C9fOfZW6ZSm6bmYtyctrpUsJl0rlE0rl0jILgIfO93C5zoqT9vgNzgvSO8jW7EeQaVdEYiN0oNUkiCOJfB850KfRK.YkWU125xJZE1trGhKAeRRRja9EZWZ.kSZzfCNT8LNS+yDsZ0hBEJtmjuDIIIzoSWkpMPEaOkJUVlRWgYylwfACkYWAX1bQ0Q2Jar7pUqVbzQGum6msJxWpHJYWMb276Q2nJIG3.GfUspUw92+9QqVsnRkpxraLpr3XgEVX45i4latTqZUqJL9UxoQ8MtwMnu8sur28tWZdyatcYi603vCSH2xz6fRkJQHLiEIANnon+4W4cx8KLKgZkpwvc5SomvwGNK5IUGRJgZ0psqDoUl8ToRU4t9hqit2KG+pBUjuTQTdIPfee5FU4w8Rbrh7QWc00J01E2J8TSMUF1vFFsqcsyZhT6wFOtjHEjaYpLx7.I27l2jqcsqQG6XGue6J.E0J7zRKMZaaa6C0uw8+HQNYpLxHiLUCHOcRkQFYjoZfJrOSK9EAXQHrYNAWVBpWkqNoJdLc3VIiLx73.kYxTKBAlMYBIylslD01jkJ.jUlTYjQFYJlRkL0hEKHIYFSRlJ+VaJ2BSYjQFYrg+ev+SgeGNkL02A....PRE4DQtJDXBB" ],
                    "embed": 1,
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
                    "data": [ 10846, "png", "IBkSG0fBZn....PCIgDQRA..ArB...PZHX....fXCUvY....DLmPIQEBHf.B7g.YHB..f.PRDEDU3wY6clGeTTe+++4r6RtS.RBjCEPtIhjvU.AsZ4VvypVUHd7sBV01ZqsdTOa4m0Zq0qZsWpnBpbTEDPEviBxkAg.g666DylDxEjDx8te98GytyNyrytYCj.jue+77AgcmY9Lu+7Y9LymWy6OumOymU4jmrBgMEannnfhME.P8+0geqn4PX4WOi1+VvtHB59otMQKvzlSqh1+4YYEPQ8+PAE05PS1Pwh5NCqRnecApv0BqOTLldgEeSIPV0xy0JFRq0eWwxsabM9Ri4u4e15ecYPJf9s1ynK6jbFQKptVDzEMsVimUcnnndYqhhMK1rUqHTPWSgla+CoVLgP0gh2KuEd+mk1TQwijVnXxP3XWHDp4phGMBS6jPXgcBwytJgfxpPwhzneUJh.dJv65E52Ig+oVfHHmGUzmp.WNwnjmP2946pE8BWBszXpF0h71q88OERtvEquolh5eB+ulygvs.6NbX8EimQBU524PSjw.AT7JTuDTwiMsTwBs6X2BDsZV7XHgmhoRyIXY4giQuQ80vVf9BpgFjJfhIwEeKJL7g+mKEZ+oXwEFBuWzncwi+1P32+6+Qivz1Tz9T0fdtUoAOKMtrRfODjzFhUWjZc6vVRqy.i4q2ULz0FAfCEaJZWEbAwECAU7JzqV71ks.6bhhZy.ECZAsL7z.V3o4k02y2XZM8UcaL.YfPmGVFDw.TTT8rReWSCjCRlawK7Ji3FuBVFK+JHTr44aJphWBkl8hDicQT3IGz2YQEsO8drXTvxqUT766VWuErteJIzIXmXMemVnso11aCVesy0mKNrYyVaPl1JhVcSKUJ0a2aClXj2lI5LeKIlV3sqe3KS79cq5CowyCgXF5oAs.cBLFu7Qf+hHJh.TkoUYnuyWBuVQWN5U.yF3QzR6tdl8bLHkaABDBgmtqpdwnZr8DXSyyMcUaZ6sOOuLKXY93WRaIgVPDN68tRwzmlPHvVfBi4EbnfNkgVxN4yKKWtbGvzX0hVmdq2cgViS+65ClWN.5XFWVe2vzkBOdZoHDpM7854kEWoXxoqP.uhV5OJT+yk6lBXoMv4gE0BJBeBX9UqYD2tbEhkYIgJt7qNU+0Xlok2Vq0AgeKJ.r+TO0SMy.1MPE0CtsrksvW7EeAewW7Ert0sNNvAN.tb4hTRNYTZgdl4pIWrkMuYVwxWNqXEqf0s10xAOvAvUSMQxIkLMumdmIdXA0VSs73+1mj8efCvkOxQ1rVcqacaLyY9+iDRHA5V25Vvst25OCOYPe9EXNOpugF3iW3mvgOxgY.8e.9WFze9P6VVJZK6McG9nGguXkqjFZnQRIkTrtpIDptTBXCd077sm06y69duOiZzWNQFYjdOXMjxU+MqgMtwbHojShnhJJ+rrP63.O0QdruV8jm5MOIYVy5c4ce24vnF8H8kmVVe1N4lsW.vV1Rt7rO6LIwD6Bcu6cmVu5tV9YhfeKFqEPcX1.5SRUUVEya9yCmNcZXmxKu7Hu7xibyMWl1zlFwFargTArpJqh4Mu4RgEVng0me94S94mO4latjUVYQLA0dmY2I8z0TCm7jmjBcVnka2rUKsrxngFZfhOwIBpcMz0EuwTxa+JCfmfMzXC74KaYDWbwxMcC2PyW3MzmOedZc779d9rk8EbMSpIF1PGRKnlQemtTzsr03rnhnxJqlZNcMDem6Laaaam7+9BHiAmtlP928cah8rm8xfGRFjXhIh2XBpuGxVUL75Sk4HTUnyhnxppjSe5ZI9NGxGXRBBkTZozPiMvINQwshV8LKlgsntM5IwNDHTehRlZS4xkKl27lGNKzIcqaciBJn.b6VsaQ1rYiK5htHxO+7YdyadLiYLCra2dPyOWM4xRgJ8TXgEx7l27X5SeFX2gY6I7Uv0sXnRhIl.u5q7xDYjQX41MW4M9wMNFzkcYz0t10l23Zs1T+h+AZ225s9tOp4t4saNnyBT7LzK7XUE8oskh9fXZyiEstauOwi8qoppqlDRTstXyaNWVyZWOctyc1OuNM66iBpNgYS.tMnHE76F+3+1GgpppZOBeAKkRBUlzDmHYjQ5jTWSpU21sMcFWebUUvQfZAkat4hSmpBUyXFyfCbfCv7m+7AfoN0oR+5W+XVyZVZdDkYlYFzhet4tEMgpoOiYncQ9QOxQXtyctzTSpwDwoSmr0slKC2r8z7TQ0zkUV47Ru7KSW5RWnm8rmrpUtJBK7v4dtm6licriwW+UeMcnCcfIMoIxjtlIREkeRdoW5kIgDRfG8Q+Mrt0sdV9xWAibjifidzix92+AXPoOHt9q+ZoaWb2H6rylOeYKmwN1wvDF+33u+2+mTfSmLgILN9u+2UR4kWAiar+PRO8zYNu+GR4kUFCJ8Aw8Mi6kHhLRN4IqfO5iWH6cO6iSWyoo6cu6L0631oe8oOM6IF8Kt68tWVzhWJ4c7iS3gGNWVZowcm0TI1niFeBipm.qqt53Cm2+gsuycRjQFESdxSfks7ujDSHd9sO1uA.1wN2Mq3K9RN3gNLcoKIxPFb5bK270icaJr50sAV1x9Rxb3CkCcnivwxKOdkW5Ox6M64Q946jG9g+47Ue8pHmMsE.XAK3iImMuEd3G9gzjUOzgOBevGNeJtnSv.urz399oSmviLB96uw+hBJvISXhii+6WuRpnrJXriaLjQFCh2eNykxJsLxHizYFy3dIxHif29seWxO+ume8C+PjRJoPokVJ+m+yGy92uZHHFv.5O24clEw24f610V1Rt7Ue0WygO7QH9DhmKejifa7FuAra2NBgfk9oeFadyalhJrX5cu6ESXhimgOrgA.u9e6MnfBbxjl3D3q95+KUTV4L1wMVxHizY1y48orRKizyXPbeyXFDYjQnk9qYRSjUtpUwoNUkLnAcYjUVSkXhNFO0+6juXEeIG5fGhD6ZWXHCNCt4a9Ggc61owFajEu3kvF2TNTQ4UPpWTJb8W20xH8D1hxqnBVvB9Orm8rW5PG5.oOnAwcbG2NQFYDr10tN97ksbxb3CiCcnCywOdd7xuxKpku.rt0ud97OeYLtwMVlzDmHm3Dmf4Nu4yAOvAQHDzm9zalVVSkTRNEOk0cXprNXsx5ZW6Z4yW1xYTW9H4HG4nr+8seFTFoyMbCWOcu6ANrIMqKUAZ6p2vy3V7tzN1wN.fBJn.Nv9O.8qe8ioN0opITcfCb.JnfBLj1fw129109tUBUNb3qGoZ1yPzpEFhCaSM0DNcVHae66fsl6VoKcoKTZokxq+5+MV82rZ5Uu6EkUd4Lu4u.JpnhwkKW3rvB4Dkn1stpptZbVXgr3krDZpolHxnhjMsoMwRV7mB.UWc0TnSmTYkUB.kTZITnSmr3EuXRNojn95piksrUvq8W+ajRxIiC61Imbxg+6JWE.7dy98Y8q+aoW8pmLhgObN3ANH+kW5koIW5CTMltQgQuxp5zUyK9JuFG4nGkq5GbkjXhIx51vFXtezGivlZ7w71UJTf2bVuGqZMqE2tEz0t1El86OOJvYgT7IJA.1+ANHu7q9WYO6ceL7gOTZrwFYIe5xX1u+7.EaTc00PANKlk7oqfhKoT5Q26NJ1ryIJoTJvYgzPCMQJojBwFWb.PRIkDWRO5ggCmOYgKgN2oNgvsa1xlykO+yVA1PgRKoTJxYgrjEsDRI4jo95qmkurUve8UeCRIkjwgC6roM4q9qjSTBNc5jFZnQps153EdgWju661HW7EeQzyddIroMkC+k+xKGzq410t2Mu9q+FbvCdHxbDCGgPvmr3kvm84KC.VvB9HV3BWDm9z0PliX3bnCcXd8W+MX6dt9qjRTKCKZQeBImbRTa80wmurkwq8p+UOkYGdJyqzP5m8reehNpnQ31Mqacqm+8+5sTq+2+A3UdkWi8r28xvxbXzXiMxR+zOi4LmO..V8ZVCe5m84jP7wysbq+HN4IOEuwe+ehSmNot5pm+7e9uP1YuARO8AQu5UOYkqZU75u9eyy0yUgSmNYoe5mQwm3Dz8t2MSwLUgpq9z3zoSptppAf27Mea1xV1BWwUdEbk+fqjstsswq+5uQPJqeJyYNuuu1ONcxh9jESSM0DQDUTrwMtQV7hWbPOmDRnn+q9Vvgv6.BzjGVEWrZ+Zc61Mye9yWSjBEz7xxa2B8lVe3uzXQlRiYgprxJKl8blCHfBKrHB02KlHiLRd1m8owlM67.O3OiFZnA9M+lGlt0stwK9WdI18t2CEVXgzsK1rZupxWlYlI+7e9CRokVFO5i7Xr8su8f9T.mwzmNYjQF7Vu8rH6uMal3DGO27O5GwZVyZ48l8r46yWU.+NyZZjkGOfpolZYcq+aotZqihK9DDWGiyPonfBJfsjatZqSAEtwq+ZI7vCmW7Edd5PG5.NraiCejixq7ZuNG7vGAghhNAKEZrIWr4b2J.7rOySRRcsKrtucC7udy2VypYugMRStbyzl5OlqaJWCUbxSwC8qdDV6Zyl65txBPcHJLfAzOdxm3Qvgcu2.w2C8XhSXbb7imGEehhYLi4p4JuxQoq1Qg65tlFW8XtZV2ZWOu8a+tb7icb7F7bPg66mdeL3AmNu4aNKxd8YyjtlIvMeK2Lqc0qk24cdOJ36K.ywA4HG4HTRIkPe6ae4wdrGAaJJrnEsXN0opjpptJN0IOEawywNn9fNtgq+5XSaLGbKbyseG+XlzDmHkWQ4rjE+onnnfPHXMqYs.vS9DONcsqck91m9v69dylrydCjQ5oqYu66mdeLjAmA+627sX8q+aYRWyD4VtkalUu50vrdm2ku+6+dCWib62wOlqcJSgxJqT90+5Giss8sSs0VGaXCa.WtbwTm5sy0NkoPEm7j7q9k+ZV65VG28cmEkbhRAfnhNJ5Su6CO2yc4.PLQGCG5PGBmNcRhIlHWyjlDBgfb1zlYW6d2TdEUnUmMf9O.dhm7w0ctKv3MdrcpSchAmQ5L4IOIss4qrdG5JqOrmx5cpktQLhQvu7g9ETZokvC+qeD1111Ntb4J.gEpEDoJcIUwy3Oxgvs5Xfw6JztScfHPOa9loPoObEG4HGg49g9Dpl1zxhd1ydoaWB8d.2oN0IBKrv.fHiHBZngFnicpi.BhIFUWfEtCr8RM0TAAjXBIfCGNnolZB2tC7iLOg3iGg.M2q6rmtgDcLQ6qrKDru8tO9jEuXJq7JLb+M2VTVxK+74i93EYXc2v0ec31sa97ksB91MrApu958YCg23Von4UU4m7TzjKWDSLQQRdhyVu5YO8rGpdfc77xC.tjddIHPgN0oNQBIDOkTRobhhKQKVXoMf9iC6cv+CdCilBeBP5IkTRAETHYOcknwFaxPJSLgDPAEhyy4l36b7n.DcLwf+ntmETf5C3om87RvlmWKra4VtYsTsqctK93Odg9U+kW9pGucuacWKut268+A.Ju7xn5SWMQGUTZwk7RtDUuDO1wNtAakXBI..wFiwy4wncN2HCn+8G.RHgDoKcsKTbwESIkThV8eOujKQ0NcpSDeBwSokVJEW7IXBSXbrqcua17l2BadyaAGNbvHFQl7+7+bOjuGAwRKsTdpm9YLjed6gC.ok1.BIgJ.tyrlJyd1uOye9ym4O+4SGiqibC230yjl3Da1xpWt3KJU0i0D6ht1OtMIVoX56dGCcA+Uzx7t4P.pueaFBbsBcMojHu7xC61rYnqe.ZcIzq2UI00jLpunK1RdIojRl7yOe.LHTkUVYQu5UuzsyBRN4y9..Fb4Nea07qFiusa8X8PXJUVY1pq9z7Nu66Q3gGNO8S+jjZxIyuelOGkUVYVFevK6xFHyblOiuM4wNaLmMypV8pYvomNS6Ntcp5zUye3O9m7VvMLVGRHg3I7vCmpqtF129OHCn+8iMuksnqnoPpolJG3fGVMdRokF0TasTd4mDa1rSW5RW7ZJrY2tecO06PxP+FTGyNJ5Sk16XpsP4Eqz2dYQ0hu04ULwotmja1YuAprpp3ptpe.W1kcYLye+y5mERM0T4PG5vbhSbBRKsAPM0TCqa8qm3hMVFwHFAgGV3b5ZpgJqrRhKt3z5gPpolRHV1sl7xKe5cu6MUe5pUOmCjPBwSpolJG7fGhhJpXtzK8RolZqkJpnBroXitzE0F6+gmalTbwEygNzgYoe5mQ1YuA5e+5GImbx.vHFQlbeyXF.PiM1.M4xEwEWrjWdpssrYyXMYM0VKQoMzOLRlYlICcnCkicriwd16d4SVzh4C9fOjQNxQRpolBG7fGLfkUunnDrGbDAcKsTbHDtQHTPn6IBpffzGT5jWd4QpWzEoITYN.6dehfoq4xr+hTdI8zSWSrxmP0znW8pm.BOaS3IsYbFcvXvwrfnVIBkzHzEprfo7EfsIDBZnwF3nG4nrwuaiZWzZEwFarDarw52oUuOevxpnB1691GqO6rCnMrayNW2TlLKZwKgm6O9BzwN1QCdiAJLzgNTV8ZVG+mO5io7Jpf8rm8gK2tXnCYvDV3g44Izonkd+Qc6c0ySSZYKeEzPiMv3G+3Lse9riOonfscy4hw0z291ahIlXXW6ZW7tu6roCcvAe4W80jXhIxDmv3wVjQZ4vmYnCYvr10tNVvB9OTd4kyd1ydYu6aebcW60xnF0nHyQLbV+5+VdkW80HizSmU5IdYCeXCOf0ygBevGLWNzgOLG5PGllZpI5UO6IQGczLrgNTVyZVKezGsPpnhJXO6Yu3xkKF5PFBgEVXZcy7JthQSlCeXDsmwqV7wGO8o28lNFWGYy4rEtnTSkHiJJ9zk9YTeC0yq+WeUKKGqacqm27sdKlxjmBSaZ2ggsUe80yC8K9kTW80yzxZpDe7wicG1ILagQTQFICanCySY8isrrZl.ciaey.HFdTvVsGMKZcCTc1CvW.aG5PGB4l6VH+7ym2dVyhBJn.DdhQ07m+70DpRM0TYnCcnMalOzgNLxM2b87DAEzTSMxblyb7Kcp1aXMaAWyiHgZY2v5LkFuyrDASL0KpdZp2FlxOOoRy11T7SLKlXhla+1+w7IKdILu4u.F3klFWzEkJETfSCikR+dgmwXC2QjYlroMkCaaa6f47gyiwb0+.N3gNr+dC5Y4a9ltQRM0TXW6dODQjQvfyHc9S+4WRKYCanCg6aF+DVxR+LV7R9TBqCgwHGQlbey3dwZwI.7M0AgmT8C9AWAaYy4xQO1wX0qdcL9wOdKp6U+z6f7Uq9xzwtQOA7ISoe8QGcL7jOwuk2dVyhuY0qFgPP25V23m8fOPPGDwCe3Cm69tuS97Oe4rnOYw3vgCthqXzbS2zMB.S+d+InnnPNaZypOsv3imrxZZbEWwnLTFMeP0bCb4q8ZmLe4W7UTSc0Re5Su4W7y+Y.psolwzuWVxR+TV7RVJg0gvL3ozsca2JUdpJI6r2.e62lMgGV3bS23MP5oOHra2AO4S937Vu0rXIK8SQHDjTRIwu7d+EDWbczxxgPn1d0pvZDd3gyu3W9y4ce2YyG9gyE.RLwD4m7StGBKrv7TVmNKYoKkEujk3orNBsxpVdXYFa02EltYXKWtRozRKQX2tc7NmVo5wupAqpppX9yyyfB0B25SM0TYZSapDWHNHNqpppTG6VlFjoFsmuAYp4wqjgCtPdhoRDxIMvoyhmXpGkE8Mi80.UsaSB2to9FZfnhLJOo.c6fwYZ.eq0epqt5wtcazgNzAP3+T9h2wa069dylxJuBF+3FKWxkzCV1J9BVwx+BtxqXz7fOvO0PFbpJqjXhNZrauk7FHXrD61sa02yOEyiAdiSFLghcCV2HzusZqsNDB25Fk7gFm7TmhXhNJb3v+Xw4xkKN8oOMwEWbVrmgNOyy963XG637mdg+HolZJzXiMQDQDtkosxJqjniNZKCDcCMz.Ue5poycpydZK5KNOffZqsdZxUCDaLMe4sppqhXiIVJuhxY1u2bH2stUl1zlFSYxWigzXSwFQGs0wfyaY0lmxZf8KRDBmt84gUKUrxAf16ok9BhBpcOY5yXFr0bykcricn8zCRJojH8zSmgNzghc61BRlZbDLGSLwv8duSmst0sxN1w1onhKFEfjRNIRO8LXHCYn3vgcShRmYGXZ6tv7m97JxqXSvEyL0ryvcMzMmKoHPHTLnoaylcMgp.iwS8V0+eCWvqXNrj9RcZCHM92u0rXaay2PIoqcsqbcW60ZNozQKaXFnKAsVJwmGFVEwIeeyeqJLkh.g+hXAZP81bzoNZs2G.X2t8yZgJqrYvFnzAK+BKrvH9vhG+CLs5mp0AgV8Prwndi+k84Kmb25VI1Xhkq7JFskoo4JqdOOFPgpPhyzVxd7rxlMann34cf2y+4sKglce2+EZlBlYwFCdjDLCclePYnwrmXNIL2cQkfc+bgu+O.945eWEUzl4P8Nqq5c1CUKcF9RveExC76qWvozxJiCenCSM0VCImbJzyK4RTE6rLyZ97v+TD3RcyYMyau4BJaqWnYO2v92+AnlZpg9Of9GvfZG5z5dzezidTZrwFo28t2M6aahUDROvpVvkrmIWcqJVoXyvKjr1KWp2FedVYKu5yaidgGcKuduoD.AqV9gfEcPCSZUHbKL48nhlnhUVr451nWQOi1SmPkBnXyVyHV4cOsly7d16ugB9SqIv4itmYZHmcmck1KjDor9ZiVW6GH6cgQMfdZVwp1XgJ.8utM9tjVn2kBCWoGR8aRK8pmNDdBBt9X8HvX9pamznYb1LjiCktoiD2dBxth5qXqhPe7VB8Jb+G0+BzOsBnNl07FPQc0qn+nLHWPpWfokNQaoyr5mgpB1dqnKsl63Qf2OqK+AuzF7Fms8MQaIdx2RZRY77ba+9cAFAnpJz8jNzvg+VvaSWECcgSq4llnS.lVfUL5YlWOUbKP6oSfP+1sxiC810bWxBk3WYRLwqmUdyeEE0wAjh+OIOuGalwZuv7UtEd1MaftXW07WHZ9dA9sM+1nIQU+LuUcfr4JClhKW.IzubyZ+kCt.24WNaKEsTOwTL84EtDRcALDR+YqeoNBbiPShVBeyw39zQD9IcnNCUp1X0aGKc6MdQd+zqmCd7ZP3IFNAJ9Pd+PnKyElaz5wD9uap4qagut24clKva74Lq5ZVD1Wb7vvJM6EBnNuEnHrzwpyH7e28cS.io6r4h9ly6sytFTW3zgmy0dwbguPzYG92Fr0rixlIvhUl5llAOsDF+SOJJJpuRD170.xqPka2t8K8dCzs9fdaknTf9zOrnkgV.181MMTP8W8E0O0Nd8kiF5cpZ4SXTzxqZjo7SsGf9pyZMtb05NJqXXasNXkrRqSCNqjCO+zT9+EzsqygDvtyeNTjx60kN795QDnxjuyqdVPn9UgPMFPV0oLghue.EzG0DA55xgEGc5eagBnHklPfE1vp1ZB7qLpNGdgwYuRC1y2d3atLWwS2WEpdN5sFQunpB9M2foVGXUCDeqKTa93Mcs8WXz1Z8y+xEm+KAsGHTEpZaw2U7N79FnGPLedM.sV7FhTEcuCY91ManFRacMP0OL7aAW2n3YbF42jvoV7uLYLELFbeSo2v9nX4l07lRaHJXYZ7aMVmYmkbN85j1HZc8USx4Tr3BP+VkVisVVa6.mgpFwgZiPec8x7uwIAEOBW9FJB5m+wQK5v99URwqaY97hxqHmAE.8Ne4MNS34mcJc4m4xhlsz8gdukvbdp+3vvZL0gKEcqWwzJ0IREvyKV9KcpjyNZskskmeZVrvol.KT44SAblKZYbmb3VHvlMcSU+deJeJ5TMBp47HTo8CkfhOQJ8keucQBEOc+xWDcTzYGMrredX53Vwh0qX36dE3T+ScJb1j9kI8G+8Lyh0ZtFHjQ1Ajy0HqsOSveQnVlPkw3rpEKE+InmdL1Zwg5O2Q187n78zzS3KTzAJCTLKTnWrBiu1IZdfonf2tDpOdQlGQ4di4k5wnPmYTL7o4CX8cmSeJEl9SccBi6mYOyB9gu2Bt+IwBOnrVfR1H5bCxaOzRoEIT4QfRnKsFCCr2AUt+AXVQugr7TjIOqb41EJ1TvM1T+YCPQWSbccGymWRdiKkvmWKJ9ZvakmF97xAsALohNwB8ckxbQzrnnYa1LGe3syoppkdh0ktNC5WN27ZUFstEhSAcLYI47.RAqPEq6KkwdYoWnx3C.SnaYO6oVaayNwHvvSKODNE4vsK231l.61E3VfVfq8McwHzoo3SDSn68GT+gjVAzjqUJ5+IBVaTi6Vmc8Um3W2b8+KMK90ETucCUWj4CP71aYX0zRiUcmTx4IjmGBEBX.eLENFydT4UnR31sgwxnWOrTGJSB0W+LETGvz.dcqpkL7db.9lpOrYSQWYv2rGpCGc.a1rgc61v6K8L3yCBCu+aRuJjHQRa.pSQLtcq9CPfttwYytc5PG5.gEVGvdHNmNKQhDIsUn5YkP.dlMAUroP3QDIgGd3mQSkDRjHQRaA171WO2ddYeiLhHIpnhxfPUM0TCO0S8TbW20cQUUU04qxpDIR9+v3vlhBtDtATHpnilHsX5h8a9lugbxIGV9xWt5TqqDIRjbNFGJ1rghP82Xu.MuVWSM0P26d2kBURjH47FNronPjwDS.mr3Ant5pS9T9jHQx4UrY2tchHBqm74arwFYm6bmL24NWxLyLOGWzjHQhDe3nCgEV.epeNc5j6+9ueJt3hYxSdxmiKZRjHQhOTZrwFENbD7wQ0S7DOAQEUT769c+tyQEKIRjHwH1ZNgJ.F1vFFG+3G+bPwQhDIRrlP5mi2TRIENxQNRvmj9jHQhj1PBIwpQLhQfMa1HszRiSdxS1VWljHQhD+PQHcWRhDIsCHj7rJTogFZfctychKWtnnhJh7xKulce1111F0We8VtsFarQ10t1kg0s4MuY91u8a4XG6Xgz5asJmAicu6cyC9fOHO6y9rmU1QhDIAlVUwpBKrPRO8zo5pql25sdKdlm4YZ18YJSYJTTQEY41JszRYRSZRFV2N1wN3Ue0Wk25sdqPZ8sVkyfQAET.kTRIbxvWmn..fBIjDQAQ06+8+9yJ6HQhj.yEzy8KImbxru8sOCq6du26kFarQ+d5jAZ8mqvlMaDJOYUIRjblQqpmUAiO9i+XFzfFDwDSL7.OvC321KpnhXLiYLrwMtQ.3cdm2gzSOct0a8VaSyWqXXCaX7a+s+1yp7UhDIstzp5JPJojBaaaaiXhIF9o+zepgXQM8oOcV6ZWKYjQFr6cuaC6WQEUDSe5SmYNyYxHG4HAT8TZRSZRZKelhU4avJmfZLntzK8ROqxWIRjz5RqpXUXgEFYjQF.pcgSOibjijm4YdFxJqr3ltoaxv1l7jmLSbhSzfWTJJJsJS9eVkuAqbBvQO5QC36KoDIRN+v4rtAtzktT9w+3eLyZVyhq5ptJCaalyblrl0rFV25VWHau.MhKLu9fkuAhTRIE5bm6bHWVjHQRaOmSDqDBAUTQEbO2y8v7m+7I2bykSe5Sqs8a7FuQl8rmMYkUVbpScpl0d8qe8ist0shKWtB55at7MPzwN1QlwLlQK7nThDIskbNQrxsa2LjgLDxLyLYzidz77O+yaX9yRQQgIMoIw0ccWGO5i9n.v0dsWKie7imhJpHFxPFBO0S8TZoeTiZTDe7wSxImrggpf402b4afn95qmFZngVwZ.IRjb1x4rQvta2t4Dm3DjPBIbNcFG8bQ9lc1YyC8POD8rm8jEtvE1ljGRj7+0Q951HQhj1EbNK.6VQq8q8RaIsjWmmyF1yd1S.e8izyN24Not5pqMy96e+6mJqrRpt5pYu6cus37QhjVaNuJV0Z+ZuzVRK4044rgezO5GgSmNMrt+ze5OwV25VMrta61tMJnfBZUruULwINQxN6rImbxgq7JuxVb9HQRqMx2OjPjyUuNOaYKawuekgxM2bY3Ce3sY1Whj1Cbd0ypfwwO9wYRSZRDYjQx.G3.0590rl0rHgDRf3iOddy27M0R+28ceGyXFyfoMsoQ3gGNO8S+z.vhW7hoG8nGzm9zGdu268BZdJDBlvDl.QGczjRJov+3e7OZ1x4K7Bu.QEUTL9wOd9g+venl2Nabiaj92+9SDQDAOvC7.zTSMAn9jFGzfFDuzK8RDSLwvnF0n.fst0sR5omNiZTiRyymie7iSZokFe1m8YbO2y8PZokFqbkqTKuewW7EIt3hi69tuapu95ImbxgLyLShN5n4Nuy6jN0oNwbm6bCn8An1ZqkG7AePhKt3nqcsqr7ku7l8XVhjyKHNOR80WuXaaaahlZpIQgEVn3XG6XZa6gdnGR7a9M+FwoN0oD6ae6S78e+2KZngFDQGczhbxIGQt4lqH5niVTWc0IDBgXkqbkB.w+5e8uDUTQEhssssIZngFDIlXhhbxIGgSmNECbfCTb3Ce3fVlV0pVknolZRbricLQXgElvoSmZa6e+u+2hm7IeRskqnhJDwFarh8rm8HV3BWn.PbzidTgPHDW+0e8h+w+3eH99u+6ECdvCVjc1YKDBgnlZpQ.Ht+6+9ENc5Tr4MuYM60TSMI5W+5m3HG4HFJS25sdqhu5q9JCqa.CX.he0u5WIJojRDCYHCQ7ce22IVyZViXLiYLhu7K+RQ+6e+E4lathq9pu5fZ+EtvEJF6XGq3XG6XhxKubQt4lqPHDh8rm8HN0oNknxJqTrqcsqfVmIQx4BNu1Mv.8Zu3xkKl6bmKacqak3hKNhKt3.T8dZfCbfZcIZvCdvFhoRxImL2+8e+nnnPm5TmXUqZUTSM0vy+7OOtc6lJqrRV1xVF1sam24cdGCkkq5ptJdsW60vsa27XO1iwAO3Awtc6TbwESJojhkk+0u90yO7G9CIszRi9129RXgEFfp2Se0W8U7AevGPG6XG4FuwajUu5Uq4EE.O5i9njRJoXv1szWun67NuSRLwD4pu5ql8rm8Pu6cuoG8nGjZpoRO5QO3hu3KlxKu7fZ+EsnEw8ce2G8nG8..sQteZoklVZF3.GXKpbIQRaAWPFyplZpIps1ZIxHizv5qolZLrtHiLRCiH8LyLSC+XrVc0USFYjAuwa7FZqKt3hiFarQlvDlfAaGczQyN24N4Nti6fErfEP+5W+XDiXD9MJ4E5FoGM0TSZSKL5y2FarQb61s135JhHhfpppJssa2tc5Se5SnWgD.7JrDVXgo0MS61sic61wlMaXylMb61cPsQkUVoLFVRZWvEjwrJ7vCma61tMVvBV.BgfpppJpnhJ3xu7KmbxIGJt3hojRJgMrgMvnG8n01Oa1Ld3LtwMN10t1ENb3ft0stQLwDCtb4hDSLQ5ae6qg+RM0TI+7ymgMrgw3F23n3hK1uIEPyuNOW4UdkrpUsJxO+74a9luQaTuGSLwvUbEWAqYMqg5qud95u9qYLiYLZ1ok9qac25V23vG9vsn8IT4VtkagErfEPc0UGtc6l7yO+1j7QhjyVtfTrBT6lzpW8pY.CX.boW5kRQEUDQEUT7m+y+YF8nGMW9ke477O+ySrwFa.sQzQGM+y+4+joLkovvG9vIszRKnikqwN1wxoN0onO8oObW20cQO6YOMrcyuNOIlXh7y9Y+L5e+6OyblyjXiMVMOsd5m9o4odpmRSLTunpU7bO2ywPFxP3HG4HL4IOYF6XGq11t8a+14O7G9Cz291Ws.raVX1LJJJFDECj8uoa5lHgDRfANvARe6aeY0qd0A0tRjb9hK3GA6m7jmjHhHBCSYKMzPCHDBBO7vCY6TTQEQW5RWBo3BUVYkQBIjPHY25qud5PG5.kVZoLpQMJCd.IDBpt5pCpf5EJTSM0PSM0jV7AkH4BMtfWr5Bct5q9pIhHhfSbhSvi+3ONScpS87cQRhj+WIs5hUye9ym0t10xDlvD3lu4at0zzWPhKWtn3hKljRJoVkIKPIRjXMs5wr51tsaizSOcxImbZsM8EjX2tcRM0TkBURjzFSqtXkc61k+JuHQhjVctf8oAJQhDI5QJVIQhj1EHEqjHQR6BjhURjHocARwJIRjzt.oXkDIRZWPqtX0q7JuBu4a9lAbZUQhDIRNSP951HQhj1EzrdV8S9I+DdjG4QnrxJ6bQ4QhDIRrjlUrZVyZVTd4kyRW5ROWTdjHQhDKoYEqra2Ncu6cmJqrxyEkGIRjHwRBo.ra2t8ynePMkHQhjVKBIwpQLhQvBW3BI2bykZqs115xjDIRj3GgrXUXgEF2y8bOru8su15xjDIRj3Ggzb4xG8QeD8pW8hO7C+v15xiDIRjXIgjmUEVXgsZ+7kKQhDImIDRhUG8nGkN0oN0VWVjHQhj.RyJVkd5oyAO3AYJSYJmKJORjHQhkHecajHQR6Bjy5BRjHocARwJIRjzt.oXkDIRZWfTrRhDIsKPJVIQhj1EHEqjHQR6BjhURjHocARwJIRjzt.oXkDIRZWfTrRhDIsKPJVIQhj1EHEqjHQR6BjhURjHocARwJIRjzt.oXkDIRZWfTrRhDIsK3+ObLmx.Xk4HHB....PRE4DQtJDXBB" ],
                    "embed": 1,
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
                    "data": [ 6326, "png", "IBkSG0fBZn....PCIgDQRA..AnB...PPHX....fY9kt.....DLmPIQEBHf.B7g.YHB..XzVRDEDU3wY6clGdTTkt++S0aIgjHICfXF1BKdeTIvvxcjUAlIHfHv.bmw6U7NOfCHDwAH9CggEctfHHhPv3BaBDggL.xhWQIHiCOHxtd4AUFVBnPBfrkPBc15t5tp576ORRYRnS2c.BjDOeddpmtRcp5sdOUR8ly4zumuGkBKrPAJJn.T5mJJJfe9DTvb2xfhONnuNVvVtggA555noogPHPHDAzVJJJXylMrZ0JVrXwumuDIRpcfsasKS.3+.P2IvhEKXwhEra2d098RhDI0bQ1jCIRjTimpbKpz00wvv.iR5FVocIqztvU1tmc6zsOIRjHoTB5.UBg.ud8hlttYvHYfFIRjb2ffJPkggAZZZ3USSFbRhDI20InBTUZPp61nooga2tQUUEggg4wsZyFgEVX3vgC42rmDI+Lf.FnRSW+dRPJ.b4xEa5RVHCO0GKVJyXeAzyvym1FRtXyV4qBJVrPHgDBgFZn2TYRjHo1IA7MYgP.BA9LwoplwkKWrurBAqJ5nvOMtXJJvVy2F+u3.kxD.CCv.nUgpxy0ZAQFYjUo62IO4IYiabiLqYMqaprCdfCvl17l4Ml+746+genbm2Ll9zYziYLz5V25awZpDIR7GALPkgt9cC+vmnoowkcpwlFXKnwgGb4R00JxKOyNNOOSLZU4.U4lSNr28tW+5O95718t2M+9+venJcujHQRvSwAppPKlJa5bZDfrAu5DgPv8GVnrpyqilQvEvzlEHpvbftt5cTeoacu6zst286n1ThDIAGAbjnCzzVopR1YmsOOtppJpp2bvkVDSzjmaCJxSvskmaCZdii1u98916d4+9YdF5YO5AO6nFEe627M977V0JWIO2XFCW+5WmCdfCvyMlwDv5WvZaIRjD7T9.UUysd5rm8rjZpoxoN0oJ2wyNqrHkUuZ16W9k2z0npCE5UmhzLnPu59cqzyQ0OM9J+7ymoN0oxPG1vXyaYKzkt1UlyblCFk4aUDfUr7kym7IeB+OyZVzfFz.b41MW4JWwu0uf01RjHI3wiGO2py0uaMZUqZEw011xN24NAfG9geXTUU4y+7OG.5PG5vMcMpd7BJVPAAh.L+BMOGQkGXPUUEMMMJH+7IrvBiDRHARHgDJ24rrksL19m9orxUsJZbiabPW+BFaKQhjpFNb33t+b8K991WdvG7AYm6bm7sey2vV2xVvoSm76+8+dZXiZzMc9pZFnpYfaMg49U1VYOmJiF1vFxqNm4PZokFOde6KO6nFU4ZIW94kGqdUqBGNbvuH5nqR0s.YaIRjT0QWWOvAppNxD83iOdZ78e+r6u3K7aPJ.zzzQS2KZF5A2ltWzz7+.uOfAL.9vMsI1111Fsu8smIO4ISt4lqY4+80udb4xEIkTRU45VfrsDIRpZjQFYD3.UVpFBTERHgvvF9voacqa9MHE.dz7fWUu30iZvso5EOZdpT6chSbBdp+vefibjiPCaTi3gd3GFa1rgMqVAfHuu6i1zl1vBVvB3i+3Olst0sFz0q.YaIRjT0wvvHviQkEqVQuZHWpBIjPnKcoK98bTTTP0k6prxWInxaI3C8PODOVu5ESZhSDOd7PzQGMyZ1ylHuu6C.yojSbsqcLiYLCdsW60LSjyxZyJN0cTTTBnskHQRUmXiMVTJrvBEPETwyxnzmZ553wyO0Bkx9xZksu+NVUo7rxJKRX2Yi0vrillgeGj7hMnErYyB5t7xx9MMjF4mVpoqqSgEVH2W0PPjpSaKQxOGIfAp.vqWuly2u6lApb4xEWO6rQ.XMH69jttNJ.MngMjvBKrf5ZjHQRMaBp.UBgvmx7R0cfJCCCz0zP2v.CCifRyzsXwBVsXAq1rIUVAIRpiPPkGUkpa4k1Uv6zYqt+tuVb3.ohoKQxOuInS3SEEEb3vAVqDoHtzVgc2JHlDIR94C9LPk+5PlUqVwpUq9taaktraUtCI0McIRjb6gOGDGYahjHQRMIpSKAl555nppha2t8YtfYylMS0.UNv6RjTykpbW+pMgGOdPWWmnhJpxcbEEEz00wqWulSj3HhHBYvJIRpgREdyrtRHphQUUEKVrXNf+ktU5ppiVIoagttNETPAR4XQhjZnTmtID5kjJEU1F.gGd3lAqJpnhpU+sVdxSdRl4LmY0l8SJojXMqYMUZ4uzK8R78e+2eaeeb5zIIjPBb7ie7aaaUUYZSaZbxSdx652WI9m5zApJs0Sd8XfSUUtgGUJvqGtta2TflFZkjHq1saGqVshGOdvqWu2qc6aYxN6rYO6YOUa1uzUIan3fhiabiqbA120t1ENc57Nx8xiGO2S9mFewW7ER0tnFHkLFUJk6i5Z3tHMJvJnIzvBEm48E4QiHraCccUbXUAqVshPHvsa23vgi60tbMRlxTlh494me9bfCb.DBwc7TLo90u9r5Uu56n1TRsapS2hpRILGBZTAtHlB03WFdHDSX1oMQUOZb8rSDgERwIxZIApBTKpt90uNSaZSid0qdw.G3.48du2y7aTL6ry1rrgNzgxRW5RMaAxd1ydXzidzrvEtP5d26N6ZW6BgPvJVwJXHCYHDe7wybm6b8otwWVz00Y4Ke47DOwSPW5RWHgDRfe7G+QedtYlYlLgILA5RW5BiXDifMrgMvvG9vMK2e96blybHojRh+ze5OQG6XGQWWm4O+4SJojB6ae6ioMsoA.CZPChMtwMZZyidzixS8TOEcsqckIO4ISAETfY8eLiYLjbxISO6YOY3Ce37ce22wq8ZuFcsqckm7IeR10t1kYc7IexmjzSO8.9Lurnppx.G3.YMqYML3AOX5YO6I+8+9emctycx.Fv.nm8rm7FuwaXds555rnEsHhO93I93imMu4M62m8Rt2QIApp8NtLABCCC7XnipMvsPCWWOeT83E2pdP0iWT83Eud0L6lg+5tgttNie7imbyMWdu268XpScprwMtQV25VmYY4kWdrzktTl7jmLaXCaf2+8ee.nnhJhu5q9Jb4xEKaYKiN24NyG7Ae.qe8qmoMsoQRIkDey27MLu4MO+Ve9xu7K4C+vOjYNyYRJojBFFF97ZTUUY7ie7nnnPJojBicrik28ceWN+4Oe4pKUl+lSN4PpolJCZPCh0u90iUqVImbxAmNcRG6XGYRSZR.vRVxRX.CX.l22O8S+TlwLlAKXAKfidzixG7AefY8+vG9vX0pURIkTnksrkLxQNRBKrvH0TSkdzidvrm8rMe9e9yed750qeel6qeWegKbA18t2Mu4a9lLgILAd8W+04u829ar3EuXl0rlEolZpbzidTfhkb5O9i+Xl0rlEKdwKlzRKMJrvB86yeI2invBKTTXgEJJpnhDE4xkvkKWB2tcKb61sPUUUnppJ73wiviGOBud8Ztooocya55B8JrYXX32spSxJqrD4lathryIWw4uzUDW7JWUb9KcYwEtzUD+XI6eoqbMQ14jinvBKTjat4JxJqrpT6clybFQbwEm3pW8plG6zm9zhu8a+VyxJ60uksrEwfFzfDBgPjVZoI5ZW6pPSSyr7m3IdBwpW8pENc5T3zoSwN24NEwEWbBMMMwku7kEG5PGxb6HG4HkyWzzzDNc5Tr5UuZQm6bmEBgP7ke4WJ5QO5gPHDhicriIhKt3D4latlWyF1vFLO2.4uIlXhhYO6YWt64TlxTDKdwKVHDBwgO7gEwEWbBcccyx6PG5fHszRy7mm6bmq3EdgWvr92st0Myye+6e+h1291Kb61sPHDhzSOcS+USSSDWbwIN1wNleelWQJpnhDwEWbhCdvCJDBgvvvP7nO5iJ14N2o44L3AOXwV25VEBgPLnAMHwF1vFLK67m+7h3hKNw92+9uIaK4dKEOFU0wmFKVT.G1rf.ErZwhYCHsXUgPb3.KVTBpAtMiLxfHhHBt+6+9MO1C9fOH.7O+m+ShLxHogMrglk0hVzBxHiLL6N2u3W7KLkqFMMMtvEt.IkTRrpUsJ.LGH5ryNaN3AOn4wAHhHhfMrgMvktzkXNyYNbnCcHBMzPM6ZUE4pW8pTu5UuxkCY+xe4urb0k.4uksrfkx9rIlXhgLyLSyeN5ni1LW0ra2tYB2BX9YEweOyqLhtDstWQo3wdL7vC2rrPCMTfhe9mYlYRKaYKMKqoMsoXyVc5bftVK+r32JFF5n6QAEkhCRoXAP.BKdKYIqO3BT0rl0LJnfBH2by07kgbxIGTUUoYMqYje94iSmNo90u9.vktzknIMoI97kPa1rQyZVy3O+m+yLvANvap7gMrgwvF1vtoiuzktTTUU4y9rOiF23Fym7IeBKZQK5lNu1zl1PQEUDG6XGi10t1A.6e+6ub0kph+VYDLO2tcveOyiIlXtksqMa1nIMoIboKcIyikUVYYtZXKolE04GLcgPftg.cEunXSGrogFdPXSGTTP0iWbopFTI6YqacqoEsnEL24NWtxUtBomd5LhQLB1111FspUshl0rlwa7FuAW8pWkzSOcVxRVBwGe7Up8hO93YIKYIjd5oiSmNYIKYI7zO8S6WeozWjra2NYjQFr10tVeddMu4MmAO3AyDm3DYgKbgLkoLEykkLfaI+srzfFz..Xe6ae31s6f5ZtUveOyA3HG4HLu4MuaI4xtO8oOrzktTN0oNEW4JWg4O+4em18kbGh57Ap.vhhEvgM7ZQAErAJghGManYXmPb3f5EZHkKIPqLrYyFKaYKiqe8qS+6e+4oe5mlN0oNwe7O9Gwtc6rzktTt3EuHO9i+3LpQMJdzG8QIwDS7m7iJLEclzjlDctyclQMpQQO6YO4e7O9GLsoMM+NUdF8nGMW6ZWid26dyHG4Huo0BwRuVEEEl0rlE+k+xeAccc5XG6HyblyzLUBBj+5qTNnr9Uqacqoe8qeLgILARM0TqT+0e5Levf+dlCvwO9wIszRCWtbUoh2Xkk9DIlXhzt10NFwHFA8qe8i1zl1PjQFoTQOpARwJ7YoxyRET1yJ6yJteYNXMJYdImbxAn3WPTT9ot2U59kUASKM6zghGKo.QQEUDNb3vmioQQEUDgDRHUI4S1kKWDQDQDTmO.4kWdDd3gWo2Cud8RRIkD+1e6uke8u9WiggAyd1yle3G9ga5aLqp5uU79X0p06JySxJ6Yttt9sjuWJtc6FEEkpTWdkb2k5ziQkc61QUUsbAj70mktuggQP+Gq0qd06VpLegUqVqRAo.B3BGgc61I7vCmwN1wxC+vOLW9xWFWtbwhW7hus82JdetaQk4m2NAofeZ.1kTyk5zsnxqWubiabCtwMtQ.SjS61sSTQEEQEUT2Ue4q5lyd1yxYO6Yod0qd7HOxibSJIgDI0FnNcfJIRjT2feVLX5RjHo1MU4wnRuRVbGp33.AxVSIQhj6LDzApDkLgcK6xkkLPiDIRtaPPEnpTEwrhK.o0zQujkidWtbggORHPq1rQngFJgDRHRYHVhjZvDTApJMHUsM750KVTTnIkYNtAkWyzKnfBnvBJfvkZltDI0XIfuYpaXTqLHETbh7Yytc+pY5Nb3.EEEJTpY5RjTikxEnxWcpyvv.pkpi3AqloGRHgfhhRsdMSGfYL8oyO7C+v8Z2Hf71u8a62odS0EezV2pTf7pEhEv+JPruFamZKHDBDAoloGVXgY1cvZyr6cuaxKu7tssyF23FIkpQ4.1PW+VZhDe6xYNyY3Lm9z20uuRt8HfiQkQs7VX.AuloGVnghpTyzAfymYljW94WsY+DewWrZy1Rp6Q.CTUauqPPwZldHNcAnf06Ohhy6q543lpaB.OAglo+Vu0awgNzgHxHhf92+9ynGyXvlMajc1YSxImLG5PGhniNZd791WF8XFCVrXg8s28RpolJOzC8PrsssMdk+5ekd26dSJqd07Ye1mQgEVH8t28lIkXhAb9Fd3CeXV6ZVCG+3GmN04Nyy+7OuOESNgP3W6e3CeXV6ZWK+qicLZUqZEicrikt08tyhV3BY6ae6HDBF9vFFu867Njw4NmO8+UupUw+3y+bxImbnKO5ixjRLQZTiZDppp7z+W+W7T+m+m7waaaj2MtAC7IeRF8nGMgFZnrnEtPt+F2XSUPnx7kJx916dY8qe87Hsss7QezGQCaXC4km4LY6ae6ricrCZPCZ.SXhSj9zm9.T7JiyeasqkyctyQe9M+F.HT4jOtVGA2WyUsnTRnhXHD2Q0L8WLwD4F23F7VKdw7hu3Kxl2xVXiabilkke94SxImLINoIwl17lM69TQEUDG4HGAWtbQxImLcricj0st0wl1zl3+2jmLye9ymu669Ndy27M8a846+9umo7RuDcq6cm2+8eeh4Ad.RbRSh78Qqe7m8OyoOMuzjmLcrCcfUtxUxi8XOFIlXhbwKbAF4HGIOVu5Ec9e+em2J4jowMtw9z+WyG7ArgMtQlzDmHImbxTjKW7hIlHZZE+77hW7hj112Nu7LlASYpSkstksv9129.fbyMWSEM0e9REonhJhu9q+ZrZ0JKaYKiVFar7bO2yQngEFqNkTnqcsqL24NWDBAm3DmfWdlyjd0qdwJW4J4AdfGfcjVZAwe0HolDd73ots5ITJdEFTD5XIDELLzPoPcrXQAcCCrYwJNbXCqVsDvVOlQFYvoN0oX6okFMpQMBnXE2zsKWjQFYP5omNo8VukoD99Bie7rt0sNF8XFCPwxI7Tl5TMms+ezV2Ji3YdFZ6i7H.vnd1mkYL8oyzm9zIqrxhKTlWTsa2NcnCcf87EeAwFar76FxP.fwNtwwl1zl3e8u9Wzst0sx4u9y96cu6k1111xXdtmC.dv+s+MZabwgM61ogMpQbeQFIPwBvWoTQ+OscrCRHgDn68nG.vq7JuB8ue8iyctyQyZVy.fDRHAZabwATbqaN3AOH8su8sb9o+7EeQjQFIicriEKVrvuanCkcu6cSBIj.gDRHLzgML1zl1D4kWdbf8ue9U+peE+oQOZS6d3CcH+96XI07vgCG+7HPUvpY5AJYVO+4OOQDQDlAofhk7Wn3AwthZPdyaQKHyLyzTCxiN5nMeI2qWubwKdQdm29sMW8gyqjVXb8qec95u5qJ2pRb3gGNqYsqk8rm8voN0oXXkYYuBfKe4KWteNP1+bm6bzpV0pxcMcoKcwu0+J5+YlQFzhVzhxUd8iJJxLyLMCT0vx7rJlXhwmsRpp5KQEUTAT60EBAYjQFz5V25xcsstjeeIo1C555ANPUYEbtZiTbpHXDTZldfpmMsIMwm52sGUUZRSZB4me9jWd4YpUTW9xWlXhIFeNlS1saml1zlx3RHA5e+6+MU9fGxPXvkzpoxR26QO3AdfGfEDftHFH627l2b9ticrxcrKbgKPzQGcPoMVkZ+qTl.jETPA37F2flzjlDvq+NouTYzjl1Ty0FvR4hW3BDarwdKaSI28IiLxHviQkkZwiOEbmUyzisksjl27lyatfEvUu5U4Lm9z7riZTr8sucZYrwRSaZSYQKZQbsqcMN8oOMqX4KmeSICfqun28oO79qXEb5SeZxKu7XEKe4LpQNR+5Kcqqck8t28xN1wNH+7xiCe3CyvG1v3Dm3DUI62st0M9+95ulOZqakabiaPZokF+GCe3bkqbEfhWAZN4INA+3O9iUp+z69zGVwJVAm5TmhrxJKVzhVDwDSL2TqXBD9yWxKu7Xdyadb1yd1pjMghaU1AOvA3S+jOgbyMW17l2r4Z5mjZOXXXD3VTYwpUzqkmw1lZlNJXW2JnXAOZBrn.gGpErYM3ZQkc61I429s4Um8r42MjgfEKV3w6W+XDOyyfcGNLKavCZPDd3gyuM934EdgW3m7iJLEcF+3GO4me9jv3FGETPADaKaIuxK+x9cp77q5PG3kekWg2eEqf+m+5ek5Uu5w3RHAdjRFGpf09w0t1wrl8rYEKe475u9qS8iJJlwLlgYWY66i+3jVZowvF5P4C2zl7o++7O+ySAET.iujOae6aOuy69t3vgCTKYAenr+atxpe4JkwV9yWxHiLXme1mQ26d2M6dn+d9TVsSqScpSL4W5k3cdm2gW8UeU5Tm5TPu3UHolCwFarEKbd9Sn7zMLviGO9TwDBjP5cuVlWxImbHzPCE61rETZltGudwsa2Aklo6xkKrYylOUCTWtbYtLwGLnooga2tqxcywoSmDQDQDv6Sfre94kGQ5CoMtTEyHP4UVoIJ6cBI80W9xsqlnaXXPgEVHQVxWPfjZeDv.UPwCbZoy2uZSApxO+7QHDDZISQl.0hI2knu5x+fVhjZVDTeqektpeTaaxIGZHgfSmN4ZW6ZAmloW+5atXbJQhjZNDTsnpzVinooUoBmWMwVTIQhj5FDz4QkhhRwi6RUPJhkHQhj6DTkS3SqVs5yEcSP1pJIRjT8fexiJkJ7oDIRjbug++670fQHtchpA.....IUjSD4pPfIH" ],
                    "embed": 1,
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
                    "patching_rect": [ 15.0, 439.5, 839.0, 234.0 ],
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