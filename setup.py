from setuptools import setup, find_packages

setup(
    name='mangadex-downloader',
    version='1.1.0',
    description='A simple Python application to download manga chapters directly from MangaDex.',
    py_modules=['mangadex_downloader'],
    install_requires=[
        'requests>=2.28.0',
    ],
    entry_points={
        'console_scripts': [
            'mangadex-dl=mangadex_downloader:main',
        ],
    },
    author='MangaDex Downloader Contributors',
    python_requires='>=3.6',
)
