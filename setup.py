from setuptools import setup, find_packages

setup(
    name="convertintomp4",
    version="1.0.0",
    description="Official Python SDK for the ConvertIntoMP4 file conversion API",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="ConvertIntoMP4",
    author_email="support@convertintomp4.com",
    url="https://convertintomp4.com",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
            "mypy>=1.0",
            "ruff>=0.1.0",
            "types-requests>=2.28.0",
        ],
    },
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video :: Conversion",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Typing :: Typed",
    ],
    license="MIT",
    keywords=["convertintomp4", "file-conversion", "video", "audio", "image", "pdf", "api"],
)
