from setuptools import setup, find_packages

setup(
    name="astrospace",
    version="1.0.0",
    description="AI-Powered Astrology Engine with Autonomous Agents",
    packages=find_packages(),
    python_requires=">=3.11",
    install_requires=[
        "kerykeion>=4.0.0",
        "anthropic>=0.34.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
    ],
)
