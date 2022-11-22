# What is This?
---
This is a Python/FastApi application that runs an optimization script to determine the 10 year strategic asset management for the Vaccine Packaging Network.

The inputs are contained in an excel file and the outputs are pushed to AWS for ingestion.

# How to use this?

1. Install the environment using the conda package manager: ```conda env create -f environment.yml```
2. Activate the new environment: ```conda activate api```
3. Verify that the new environment was installed correctly: ```cona env list```
1. run ```python -m src.entrypoints.main``` to run the application in DEV mode.
2. Navigate to <http://localhost:8000> in your browser to connect to local api endpoints.

# Testing

1. Install the test dependencies using ```conda install pytest pytest-cov```
2. Ensure you are at the project root
3. Run ```python -m pytest -vv --cov=src/``` to complete tests