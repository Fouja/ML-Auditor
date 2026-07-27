from setuptools import setup, find_packages

setup(
    name="mlauditor-sdk",
    version="0.1.0",
    description="ML-Auditor Python SDK",
    author="ML-Auditor Team",
    packages=find_packages(),
    install_requires=["requests>=2.31.0"],
    python_requires=">=3.10",
)
