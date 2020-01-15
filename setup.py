# flake8: noqa

from setuptools import setup, find_packages

reqs = [
    'eth-keys==0.3.1',
    'pycryptodomex',
    'websockets'
]

setup(
    name='riemann-ether',
    version='6.0.0',
    description=('App prototyping library for Ethereum-based chains'),
    url='https://github.com/summa-tx/riemann-ether',
    author='James Prestwich',
    author_email='james@summa.one',
    install_requires=reqs,
    packages=find_packages(),
    package_dir={'ether': 'ether'},
    package_data={'ether': ['py.typed']},
    keywords = 'ethereum cryptocurrency blockchain development',
    python_requires='>=3.6',
    classifiers=[
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)'
    ]
)
