from setuptools import setup, find_packages
from codecs import open
from os import path

setup_dir = path.abspath(path.dirname(__file__))

with open(path.join(setup_dir, "README.markdown"), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='cdparacord',
    version='0.1.0',

    description='Quick & dirty cdparanoia wrapper',
    long_description=long_description,
    url='https://github.com/fennekki/cdparacord',
    
    author='fennekki',

    license='BSD 2-clause',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Multimedia :: Sound/Audio :: CD Audio :: CD Ripping'
    ],

    keywords='cdparanoia cd ripping',

    install_requires=[''],

    package_data={},
    data_files=[],

    entry_points={
        'console_scripts': [
            'cdparacord=cdparacord:main'
        ]
    }
)
