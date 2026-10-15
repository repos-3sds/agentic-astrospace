from setuptools import setup, find_packages

setup(
    name="astrospace",
    version="1.0.0",
    description="AI-Powered Astrology Engine with Autonomous Agents",
    packages=find_packages(),
    python_requires=">=3.11",
    # Kept in step with requirements.txt, which is what the image and CI
    # install. kerykeion is pinned exactly for the reason given there: 6.x
    # removed the API this app imports, so `pip install -e .` with the old
    # `>=4.0.0` pulled 6.0.5 and the app failed to import.
    install_requires=[
        "kerykeion==5.12.9",
        "pyswisseph>=2.10.0",
        "anthropic>=0.34.0",
        "google-genai>=1.0.0",
        "fastapi>=0.104.0",
        "uvicorn>=0.24.0",
        "python-dotenv>=1.0.0",
        "pydantic>=2.0.0",
        "requests>=2.31.0",
        "python-multipart>=0.0.9",
        "psycopg[binary]>=3.2.0",
        "sqlalchemy>=2.0.0",
        "fonttools[woff]>=4.50.0",
    ],
)
