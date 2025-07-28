FROM golang:1.24-alpine AS build

WORKDIR /app
COPY main.go .
RUN go build -o main main.go

FROM scratch

COPY --from=build /app/main .

ENTRYPOINT ["/app/main"]
