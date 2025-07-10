# Ecommerce Project Setup Instructions

## Make sure the following

- You have python installed on your machine
- You have the Mongodb server installed

## Steps
- create a virtual environment using `python3 -m venv venv`
- select the virtual environment:
  - For windows `source venv\Scripts\activate`
  - For Linux or MacOS `source venv/bin/activate`
- install dependencies using `pip3 install -r requirements.txt`
- create a `.env` file and copy content of `sample.env` to it
- update the `.env` file according to your configurations
- run one of the following command to start the server:
  - `python run.py`