from setuptools import setup, find_packages
from codecs import open
from os import path

setup_dir = path.abspath(path.dirname(__file__))

with open(path.join(setup_dir, "README.markdown"), encoding='utf-8') as f:
    long_description = f.read()

# Get __version__ and __url__
with open('./cdparacord/appinfo.py') as f:
    exec(f.read())

setup(
    name='cdparacord',
    version=__version__,

    description='Quick & dirty cdparanoia wrapper',
    long_description=long_description,
    url=__url__,

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

    install_requires=[
        'musicbrainzngs',
        'discid',
        'mutagen',
        'xdg',
        'PyYAML'
    ],

    package_data={},
    data_files=[],

    entry_points={
        'console_scripts': [
            'cdparacord=cdparacord.main:entrypoint_wrapper'
        ]
    }
)
