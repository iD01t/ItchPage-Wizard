from pathlib import Path
from setuptools import setup, find_packages

this_dir = Path(__file__).parent
readme = (this_dir / "README.md").read_text(encoding="utf-8") if (this_dir / "README.md").exists() else ""

setup(
    name="itchpage-wizard",
    version="1.0.0",
    description="Generate itch.io-compliant page assets fast",
    long_description=readme,
    long_description_content_type="text/markdown",
    author="iD01t Productions",
    license="MIT",
    packages=find_packages(exclude=("tests", "samples", "dist")),
    include_package_data=True,
    install_requires=[
        "PySimpleGUI",
        "Pillow",
        "imageio",
        "numpy",
    ],
    python_requires=">=3.11",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Multimedia :: Graphics",
    ],
)
