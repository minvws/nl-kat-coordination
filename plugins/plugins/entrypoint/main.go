package main

import (
	"bytes"
	"fmt"
	"io"
	"log"
	"mime/multipart"
	"net/http"
	"net/url"
	"os"
	"os/exec"
	"regexp"
)

var defaultURL = "http://openkat:8000/api/v1/file/" // To override: go build -ldflags="-X main.defaultURL=http://test:443/upload" -o main main.go

func main() {
	if len(os.Args) < 2 {
		log.Fatal("Usage: go run main.go <command> [args...]")
	}

	pluginId := os.Getenv("PLUGIN_ID") // TODO: force plugin id?
	var bearer = "Token " + os.Getenv("OPENKAT_TOKEN")

	// Get upload URL from environment or use default
	uploadURL := os.Getenv("UPLOAD_URL")
	if uploadURL == "" {
		uploadURL = defaultURL
	}

	pattern := regexp.MustCompile(`\{file/(\d+)\}`)

	new_args := []string{}

	for _, arg := range os.Args {
		replaced := pattern.ReplaceAllStringFunc(arg, func(m string) string {
			sub := pattern.FindStringSubmatch(m)
			if sub == nil {
				return m
			}
			fileName, err := downloadFile(sub[1], "/tmp")
			if err != nil {
				log.Fatalf("Failed to download file: %v", err)
			}
			return fileName
		})
		new_args = append(new_args, replaced)
	}

	// Prepare command
	cmd := exec.Command(new_args[1], new_args[2:]...)

	inFile := os.Getenv("IN_FILE")
	if inFile != "" {
		stdinPipe, err := cmd.StdinPipe()

		if err != nil {
			log.Fatalf("Failed to get stdin: %v", err)
		}
		inFileName, err := downloadFile(inFile, "/tmp")

		if err != nil {
			log.Fatalf("Failed to download input file: %v", err)
		}
		file, err := os.Open(inFileName)

		if err != nil {
			log.Fatalf("Failed to open input file: %v", err)
		}
		_, err = io.Copy(stdinPipe, file)

		if err != nil {
			log.Fatalf("failed to pass file to stdin: %w", err)
		}
		err = stdinPipe.Close()

		if err != nil {
			log.Fatalf("failed to close stdin pipe: %w", err)
		}
	}

	if uploadURL == "/dev/null" {
		cmd.Stdout = os.Stdout
		cmd.Stderr = os.Stderr
		if cmd.Run() != nil {
			os.Exit(1)
		}
		os.Exit(0)
	}

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

	var body bytes.Buffer
	writer := multipart.NewWriter(&body)

	cmdError := cmd.Wait()

	if cmdError != nil {
		log.Printf("Command exited with error: %v", cmdError)

		if len(stderrBytes) == 0 {
			log.Printf("No stderr data present.")
			os.Exit(1)
		}

		stderrFile, err := writer.CreateFormFile("file", "stderr")
		if err != nil {
			log.Fatalf("Failed to create stderr part: %v", err)
		}
		stderrFile.Write(stderrBytes)

		err = writer.WriteField("type", "error")
		if err != nil {
			log.Fatalf("Failed to create type part: %v", err)
		}
	} else {
		if len(stdoutBytes) == 0 {
			log.Printf("No stdout data present.")
			os.Exit(0)
		}

		stdoutFile, err := writer.CreateFormFile("file", "stdout")
		if err != nil {
			log.Fatalf("Failed to create stdout part: %v", err)
		}
		stdoutFile.Write(stdoutBytes)

		err = writer.WriteField("type", pluginId)
		if err != nil {
			log.Fatalf("Failed to create type part: %v", err)
		}
	}

	writer.Close()

	req, err := http.NewRequest("POST", uploadURL, &body)

	if err != nil {
		log.Fatalf("Creating request failed: %v", err)
	}

	req.Header.Add("Authorization", bearer)
	req.Header.Add("Content-Type", writer.FormDataContentType())

	client := &http.Client{}
	resp, err := client.Do(req)

	if err != nil {
		log.Fatalf("Upload failed: %v", err)
	}
	defer resp.Body.Close()

	bodyBytes, err := io.ReadAll(resp.Body)
	log.Printf("Upload completed. Server responded with: %s\n%s", resp.Status, string(bodyBytes))

	if cmdError != nil {
		os.Exit(1)
	}
}

func downloadFile(file_pk string, destination string) (string, error) {
	api_url := os.Getenv("OPENKAT_API")
	var bearer = "Token " + os.Getenv("OPENKAT_TOKEN")
	var furi, _ = url.Parse(api_url)
	var body bytes.Buffer

	req, err := http.NewRequest("GET", furi.Scheme+"://"+furi.Host+"/files/"+file_pk+"/", &body)

	if err != nil {
		return "", fmt.Errorf("failed to create GET request: %w", err)
	}

	req.Header.Add("Authorization", bearer)

	client := &http.Client{}
	resp, err := client.Do(req)

	if err != nil {
		return "", fmt.Errorf("failed to make GET request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("bad status: %s", resp.Status)
	}

	fileName := destination + "/" + file_pk

	out, err := os.Create(fileName)
	if err != nil {
		return "", fmt.Errorf("failed to create file: %w", err)
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to save file: %w", err)
	}

	return fileName, nil
}
