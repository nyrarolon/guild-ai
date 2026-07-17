from setuptools import setup, find_packages

setup(
    name="guild-ai",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        "console_scripts": [
            "guild=guild.cli:main",
        ],
    },
    python_requires=">=3.10",
    author="Neech",
    author_email="",
    description="Open protocol for trusted agent-to-agent collaboration.",
    license="Apache 2.0",
    url="https://github.com/neech/guild-ai",
)
