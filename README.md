# apix
apix (API Explorer) let's you quickly discover new APIs and versions.
apix can also help you generate new versions of your API interaction libraries.

**note:** apix currently only supports APIs that have an apidoc.

Installation
------------
```pip install .```
or
```python setup.py install```


Usage
-----
```usage: apix [-h] {explore,diff,makelib,list}```

API Exploration
---------------
Explore a target API, saving all entities, methods, and parameters to a version file.
If you don't specify a version, apix will save the results by date.

**Examples:**

```apix explore --help```

```apix explore -n satellite6 -u https://my.sathost.com/ -v 6.2.14```

Version Diff
------------
apix can give you a diff between previously explored versions of an API.
This is more helpful than performing a linux-style diff on the file, since it retains context.
By default it will use the most recently explored API and the latest known versions (with dated version sorted to the bottom).

**Examples:**

```apix diff --help```

```apix diff -n satellite6 -l 6.3 -p 6.2.14```

```apix diff -n satellite6 -l 6.3```

```apix diff -n satellite6```

```apix diff```

Library Maker
-------------
You can setup apix to populate any library you may be using to interact with your API.
You will have to provide template files, as well as extend apix's code base to populate those templates.
apix comes with the ability to populate Nailgun, a python library used for Satellite 6.
By default it will use the most recently explored API and the latest known versions (with dated version sorted to the bottom).

**Examples:**

```apix makelib --help```

```apix makelib -n satellite6 -v 6.3```

```apix makelib -n satellite6```

```apix makelib```


List
----
apix can also list out the APIs and versions for an API that is currently knows about.

**Examples:**

```apix list --help```

```apix list apis```

```apix list versions -n satellite6```

Docker
------
apix is also available with automatic builds on dockerhub.
You can either pull down the latest, or a specific released version.
Additionally, you can build your own image locally. You will want to mount the local apix directory to keep any data apix creates.

**Examples:**

```docker build -t apix .```
or
```docker pull jacobcallahan/apix```

```docker run -it apix explore --help```

```docker run -it -v $(pwd):/apix/:Z apix explore -n satellite6 -u https://my.sathost.com/ -v 6.2.14```

Note
----
This project only explicitly supports python 3.6+.


