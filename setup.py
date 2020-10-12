from setuptools import setup

with open('VERSION') as f:
    version = f.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='fierai',
    version=version,
    packages=['fierai'],
    exclude_package_data={'data': 'data/'},
    url='https://github.com/knowbodynos/fierai',
    license='MIT',
    author='Ross Altman',
    author_email='knowbodynos@gmail.com',
    description='',
    install_requires=required,
    entry_points={
        'console_scripts': [
            'fierai = fierai.cli:cli'
        ]
    }
)
