#!/usr/bin/env python
from distutils.core import setup
import sys
setup(name='log-zoom',
      version='1.0',
      description='A collection of scripts for creating maps in logarithmic polar coordinates',
      author='Dmitry Shintyakov',
      author_email='shintyakov@gmail.com',
      url='https://github.com/dmishin/log-zoom',
      packages=[],
      scripts=['auto_glue.py','gmap_get.py','log_transform.py','mercator2ortho.py'],
      license='MIT',
      requires=["pillow"]
)
