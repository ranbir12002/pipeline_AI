# pipeline_AI



steps to run 

- clone the repository
- cd to Backend
- python -m venv .venv
- .venv/scripts/activate
- run pip install -r reqyirements.txt -y
- cd to Server
- uvicorn main:app --host 0.0.0.0 --port 8000 --reload
