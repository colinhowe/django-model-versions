from setuptools import setup
    
import os

root_dir = os.path.dirname(__file__)
if not root_dir:
    root_dir = '.'
long_desc = open(root_dir + '/README').read()

setup(
	name='django-model-versions',
	version='0.1.3',
	description='A base model class for adding version information and preventing concurrent modifications',
	url='https://github.com/colinhowe/django-model-versions',
	author='Colin Howe',
	author_email='colin@colinhowe.co.uk',
	packages=['modelversions'],
	classifiers=[
		'Development Status :: 4 - Beta',
		'Environment :: Web Environment',
		'Framework :: Django',
		'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
		'Operating System :: OS Independent',
		'Programming Language :: Python',
		'Topic :: Software Development :: Libraries :: Python Modules',
	],
	license='Apache 2.0',
	long_description=long_desc,
)
