#!/usr/bin/env python

from setuptools import setup

def readme():
    with open('README.md') as f:
        return f.read()

setup(
    name='Florida2000',
    version='0.1',
    description='Read Punched Cards from scanned images',
    long_description=readme(),
    classifiers=[],
    keywords='punched-cards preservation',
    url='https://github.com/Datamuseum-DK/Florida2000',
    author='Poul-Henning Kamp',
    author_email='phk@FreeBSD.org',
    license='BSD',
    packages=['florida2000'],
    zip_safe=False
)

