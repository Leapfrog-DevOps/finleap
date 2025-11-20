FROM golang:1.23-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN go mod tidy
RUN CGO_ENABLED=0 GOOS=linux go build -o cost-calculator ./cmd/main.go

FROM alpine:latest

WORKDIR /app

COPY --from=builder /app/cost-calculator .

EXPOSE 8080

CMD ["./cost-calculator"]
