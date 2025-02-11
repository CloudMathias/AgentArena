FROM python:3.11.2

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py . 

CMD ["python", "app.py"]