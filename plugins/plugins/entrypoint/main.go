package main

import (
  "bytes"
  "encoding/json"
  "fmt"
  "io"
  "log"
  "mime/multipart"
  "net/http"
  "os"
  "os/exec"
  "regexp"
  "strings"
)

var defaultURL = "http://openkat:8000/api/v1/file/" // To override: go build -ldflags="-X main.defaultURL=http://test:443/upload" -o main main.go

//Example usage:
//docker run --network nl-kat-coordination_default -v path/to/main:/bin/main --entrypoint=/bin/main projectdiscovery/nuclei nuclei -h

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

  pattern := regexp.MustCompile(`^\{file/(\d+)\}$`)

  new_args := []string{}

  for _, arg := range os.Args {
    if matches := pattern.FindStringSubmatch(arg); matches != nil {
      fileName, err := downloadFile(matches[1], "tmp")

      if err != nil {
        log.Fatalf("Failed to download file: %v", err)
      }

      new_args = append(new_args, fileName)
    } else {
      new_args = append(new_args, arg)
    }
  }

  // Prepare command
  cmd := exec.Command(new_args[1], new_args[2:]...)

  if uploadURL == "/dev/null" {
    cmd.Stdout = os.Stdout
    cmd.Stderr = os.Stderr
    if err := cmd.Start(); err != nil {
      log.Fatalf("Failed to start command: %v", err)
    }

    if cmd.Wait() != nil {
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

  var body bytes.Buffer

  req, err := http.NewRequest("GET", api_url+"/file/"+file_pk+"/", &body)

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

  // Check if status is OK
  if resp.StatusCode != http.StatusOK {
    return "", fmt.Errorf("bad status: %s", resp.Status)
  }

  var data map[string]interface{}
  if err := json.NewDecoder(resp.Body).Decode(&data); err != nil {
    log.Fatalf("Decode error:", err)
  }

  fileUri := data["file"].(string)
  splitString := strings.Split(fileUri, "/")
  fileName := destination + "/" + splitString[len(splitString)-1]

  req, err = http.NewRequest("GET", fileUri, &body)

  if err != nil {
    return "", fmt.Errorf("failed to create GET request: %w", err)
  }

  req.Header.Add("Authorization", bearer)

  resp, err = client.Do(req)

  if err != nil {
    return "", fmt.Errorf("failed to make GET request: %w", err)
  }
  defer resp.Body.Close()

  // Check if status is OK
  if resp.StatusCode != http.StatusOK {
    return "", fmt.Errorf("bad status: %s", resp.Status)
  }

  // Create local file
  out, err := os.Create(fileName)
  if err != nil {
    return "", fmt.Errorf("failed to create file: %w", err)
  }
  defer out.Close()

  // Copy response body to file
  _, err = io.Copy(out, resp.Body)
  if err != nil {
    return "", fmt.Errorf("failed to save file: %w", err)
  }

  return fileName, nil
}
