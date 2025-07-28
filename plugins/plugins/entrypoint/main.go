package main

import (
	"bytes"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"os"
	"os/exec"
)

var defaultURL = "" // To override: go build -ldflags="-X main.defaultURL=http://test:443/upload" -o main main.go

//Example usage:
//docker run --network nl-kat-coordination_default -v path/to/main:/bin/main --entrypoint=/bin/main projectdiscovery/nuclei nuclei -h

func main() {
	if len(os.Args) < 2 {
		log.Fatal("Usage: go run main.go <command> [args...]")
	}

	// Get upload URL from environment or use default
	uploadURL := os.Getenv("UPLOAD_URL")
	if uploadURL == "" {
		uploadURL = defaultURL
	}

	// Prepare command
	cmd := exec.Command(os.Args[1], os.Args[2:]...)
	stdoutPipe, err := cmd.StdoutPipe()
	if err != nil {
		log.Fatalf("Failed to get stdout: %v", err)
	}
	stderrPipe, err := cmd.StderrPipe()
	if err != nil {
		log.Fatalf("Failed to get stderr: %v", err)
	}

	if err := cmd.Start(); err != nil {
		log.Fatalf("Failed to start command: %v", err)
	}

	stdoutBytes, err := io.ReadAll(stdoutPipe)
	if err != nil {
		log.Fatalf("Failed to read stdout: %v", err)
	}
	stderrBytes, err := io.ReadAll(stderrPipe)
	if err != nil {
		log.Fatalf("Failed to read stderr: %v", err)
	}

	if err := cmd.Wait(); err != nil {
		log.Printf("Command exited with error: %v", err)
	}

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)

	stdoutFile, err := writer.CreateFormFile("stdout", "stdout.txt")
	if err != nil {
		log.Fatalf("Failed to create stdout part: %v", err)
	}
	stdoutFile.Write(stdoutBytes)

	stderrFile, err := writer.CreateFormFile("stderr", "stderr.txt")
	if err != nil {
		log.Fatalf("Failed to create stderr part: %v", err)
	}
	stderrFile.Write(stderrBytes)

	writer.Close()

	resp, err := http.Post("http://openkat:8000/upload", writer.FormDataContentType(), &body)
	if err != nil {
		log.Fatalf("Upload failed: %v", err)
	}
	defer resp.Body.Close()

	log.Printf("Upload completed. Server responded with: %s", resp.Status)
}
