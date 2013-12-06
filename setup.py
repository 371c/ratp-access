# -*- coding: utf-8 -*-
import sys
from setuptools import setup, find_packages

requires = [
    'sqlalchemy',
    'xlrd'
]

if sys.version_info[:3] < (2, 5, 0):
    requires.append('pysqlite')

setup(name='Ratp',
      version='1.0',
      description='Simple App exploiting RATP data',
      author='Eric',
      author_email='eric.gitau@gmail.com',
      url='',
      packages=find_packages(),
      include_package_data=True,
      zip_safe=False,
      install_requires=requires,
      tests_require=requires
      )
