# flake8: noqa

from setuptools import setup, find_packages

reqs = [
    'eth-abi==1.3.0',
    'eth-keys==0.2.1',
    'eth-account==0.3.0'
]

setup(
    name='riemann-ether',
    version='0.0.2',
    description=('Transaction creation library for Ethereum'),
    url='https://github.com/summa-tx/riemann-ether',
    author='James Prestwich',
    author_email='james@summa.one',
    license='LGPLv3.0',
    install_requires=reqs,
    packages=find_packages(),
    package_dir={'ether': 'ether'},
    keywords = 'ethereum cryptocurrency blockchain development',
    python_requires='>=3.6'
)
