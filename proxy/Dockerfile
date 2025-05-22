FROM golang:1.24.3

WORKDIR /app

COPY . /app/

RUN go mod download
RUN go build -o /app/main .

RUN chmod +x /app/main

ENTRYPOINT [ "/app/main" ]