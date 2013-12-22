Log-Zoom
========
A collection of scripts for creatign maps in logarithmic polar coordinates.


Scripts:
- **auto_glue.py**
  Automatically download sequence of Google map images of some point, ransform them to log-polar coordinates and glue into single image.
- **gmap_get.py**
  Library for downloading map images, using Google maps satic API. Can be used as script.
- **log_transform.py**
  Convert arbitraryimage from Cartesian to log-polar coordinates.
- **mercator2ortho.py**
  Script and library to convert pieces of maps in Mercator projection into maps in orthogonal projection.

To get detailed information on possible command line options, run scripts with the **--help** option.

Requirements
------------

1. Python 3.3 or higher.
2. Pillow (fork of the PIL - Python Imaging Library)
