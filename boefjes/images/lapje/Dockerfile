FROM golang:1.21 as build

WORKDIR /app

COPY sitecrawler/go.mod sitecrawler/go.sum ./
RUN go mod download

COPY sitecrawler/*.go ./

RUN CGO_ENABLED=0 GOOS=linux go build -o /sitecrawler

FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates mitmproxy gnupg libnss3-tools \
    && curl -fsSL https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /sitecrawler /usr/local/bin/sitecrawler
