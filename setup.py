#!/usr/bin/env python

from setuptools import setup

import sys
if not sys.version_info[0] >= 3:
    sys.exit("Requires python 3 or greater")

setup(name='vibase',
      version='0.1.0',
      description='Edit a database table using the VIM editor',
      author='Ben McGunigle',
      author_email='bnmcgn@gmail.com',
      url='https://github.com/BnMcGn/vibase',
      download_url='https://github.com/BnMcGn/vibase/archive/0.1.0.tar.gzip',
      packages=['src'],
      entry_points = {
              'console_scripts': [
                  'vibase = src.vibase:main',
              ],
          },
     )
