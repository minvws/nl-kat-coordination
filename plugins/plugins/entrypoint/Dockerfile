FROM golang:1.24-alpine AS build

WORKDIR /app
COPY entrypoint.go .
RUN go build -o entrypoint entrypoint.go

FROM scratch
COPY --from=build /app/entrypoint .
