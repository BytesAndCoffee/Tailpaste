from setuptools import setup, find_packages

setup(
    name="tailpaste",
    version="1.0.0",
    description="A paste service with Tailscale authentication",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "flask>=3.0.0",
        "requests>=2.31.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.3",
            "hypothesis>=6.92.1",
        ],
    },
)
