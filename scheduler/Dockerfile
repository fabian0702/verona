FROM python:3.12-slim

COPY --from=docker:dind /usr/local/bin/docker /usr/local/bin/

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./ /app/scheduler

WORKDIR /app

ENV PYTHONPATH=.

CMD ["python", "scheduler/main.py"]