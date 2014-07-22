from distutils.core import setup
import py2exe, sys, os

setup(console=['MetricsApp.py'],
	  data_files=['config.json'],    
      options = {'py2exe': {"optimize": 2, 'compressed': True}}
	  )
