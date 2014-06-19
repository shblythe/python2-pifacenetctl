# vim: set et sts=4:
from distutils.core import setup

setup(	name='pifacenetctl',
    description='Raspberry Pi and PiFace headless network manager',
    author='Stephen Blythe',
    author_email='stephen@urwick.co.uk',
    url='https://github.com/shblythe/python2-pifacenetctl',
    version='0.2.1',
    py_modules=['pifacenetctl'],
    license='GPL v3',
    extras_require = {
        'Control of netctl wireless profiles':["netctl>=0.2.0"],
    }
)
