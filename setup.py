#!/usr/bin/env python

from distutils.core import setup

import sys
if not sys.version_info[0] >= 3:
    sys.exit("Requires python 3 or greater")

setup(name='vibase',
      version='0.0.1',
      description='Edit a database table using the VIM editor',
      author='Ben McGunigle',
      author_email='bnmcgn@gmail.com',
      url='https://github.com/BnMcGn/vibase',
      packages=['src'],
      entry_points = {
              'console_scripts': [
                  'vibase = src:main',
              ],
          },
     )
