=======
History
=======

0.4.0(2023-04-20)
=================

+ Refactored a few things
+ Modernized the repo a bit, getting rid of travis in favor of github actions
+ Moved to click-based cli
+ Added a new apipie parser that doesn't need to visit each link
+ Moved old apipie parser to an unused file
+ Added a new compact subcommand to convert existing data to a compact format

0.3.1(2019-07-15)
=================

+ Added the ability to specify a data directory via --data-dir

0.3.0(2019-07-07)
=================

+ Added three new templates (basic, intermediate, advanced)
+ Modified the libmaker to be much more flexible

0.2.6(2018-11-08)
=================

+ Added compact modes to explore and diff
+ Switched code style to black

0.2.5(2018-02-26)
=================

+ Added a test for explore module
+ Added test parser for above test
+ Added a bit of feedback to explore's explore and save_data
+ Added more in-code documentation

0.2.4(2018-02-23)
=================

+ Added ability to write custom parsers for new api types
+ Separated base apipie parser logic into a new class

0.2.3(2018-02-23)
=================

+ Updated string formatting to f-strings

0.2.2(2018-02-18)
=================

+ Added initial tests
+ Added travis config

0.2.1(2018-02-15)
=================

+ Improved diff results, separating changed from added/removed

0.2.0(2018-02-15)
=================

+ Added makelib subcommand
+ Added template files for nailgun
+ Allowed apix to assume the most likely arguments, if not specified
+ Other miscellaneous changes

0.1.2(2018-02-13)
=================

+ Fixed async behavior, greatly improving url fetch/download time
+ Increased timeout tries to 3
+ Sorted the results by url to account for async results
+ Added more logging output

0.1.1(2018-02-11)
=================

+ Added parameter validation information to saved data

0.1.0(2018-02-11)
=================

+ Initial commit!
+ Added ability to explore APIs with an apidoc
+ Added ability to save the diff between versions
+ Added the ability to list current APIs and versions
+ Added Dockerfile
