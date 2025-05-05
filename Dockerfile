FROM python:3.12.6
ENV PYTHONBUFFERED 1
WORKDIR /app
COPY requirements.txt /app
COPY . /app
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt
CMD ["python", "app.py"]