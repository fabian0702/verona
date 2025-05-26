FROM golang:1.24.3 AS builder

WORKDIR /app

COPY ./proxy/ /app/

RUN mkdir -p /app/build/

RUN go mod download
RUN go build -o /app/build/proxy .

RUN go install github.com/DarthSim/hivemind@latest

FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y ca-certificates curl && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/debian \
    $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null && \
    apt-get update

RUN apt-get install -y docker-ce-cli git

COPY ./scheduler/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY --from=builder /app/build/proxy /app/proxy
RUN chmod +x /app/proxy

COPY --from=builder /go/bin/hivemind /usr/local/bin/hivemind

COPY ./scheduler/ /app/scheduler

COPY ./Procfile /app/Procfile

RUN mkdir -p /run/verona

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=.

CMD ["hivemind"]