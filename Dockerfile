FROM python:3-slim
ENV PYTHONUNBUFFERED 1
RUN mkdir /pybooru
WORKDIR /pybooru
COPY requirements.txt /pybooru/
RUN pip install -r requirements.txt
COPY . /pybooru/
EXPOSE 8000 45869 45868
CMD ["python3", "manage.py", "runserver", "0.0.0.0:8000"]