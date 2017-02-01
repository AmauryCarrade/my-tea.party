from setuptools import setup

setup(
    name='myteaparty',
    packages=['myteaparty'],
    include_package_data=True,
    install_requires=[
        'flask',
        'peewee',
        'PyMySQL',
        'beautifulsoup4',
        'requests',
        'python-slugify',
        'titlecase'
    ],
    extras_require={
        'dev': [
            'flake8'
        ]
    }
)
