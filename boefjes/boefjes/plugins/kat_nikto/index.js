import fs from "node:fs";
import fetch from "node-fetch"; // npm install node-fetch
import { execSync } from "node:child_process";

// Getting information from INPUT_URL: http://boefje:8000/api/v0/tasks/6f08f386-0dfe-4cd4-a1b4-91e95411c883
// Found boefje input with ooi: 46.23.85.171
// - ***** TLS/SSL support not available (see docs for SSL install) *****
// - Nikto v2.5.0
// ---------------------------------------------------------------------------
// + Target IP:          46.23.85.171
// + Target Hostname:    46.23.85.171
// + Target Port:        80
// + Start Time:         2024-08-05 09:55:56 (GMT0)
// ---------------------------------------------------------------------------
// + Server: nginx/1.18.0 (Ubuntu)
// + /: The X-Content-Type-Options header is not set. This could allow the user agent to render the content of the site in a different fashion to the MIME type. See: https://www.netsparker.com/web-vulnerability-scanner/vulnerabilities/missing-content-type-header/
// + No CGI Directories found (use '-C all' to force check all possible dirs)
// + nginx/1.18.0 appears to be outdated (current is at least 1.25.3).
// + 8108 requests: 0 error(s) and 2 item(s) reported on remote host
// + End Time:           2024-08-05 09:56:14 (GMT0) (18 seconds)
// ---------------------------------------------------------------------------
// + 1 host(s) tested
// Encoding: [{"host":"46.23.85.171","ip":"46.23.85.171","port":"80","banner":"","vulnerabilities":[{"id": "999103","references": "https://www.netsparker.com/web-vulnerability-scanner/vulnerabilities/missing-content-type-header/","method":"GET","url":"/","msg":"The X-Content-Type-Options header is not set. This could allow the user agent to render the content of the site in a different fashion to the MIME type."},{"id": "600575","method":"HEAD","url":"/","msg":"nginx/1.18.0 appears to be outdated (current is at least 1.25.3)."}]}]
// FINISHING...
// SENDING OUT WITH:
// {"status":"COMPLETED","files":[{"content":"W3siaG9zdCI6IjQ2LjIzLjg1LjE3MSIsImlwIjoiNDYuMjMuODUuMTcxIiwicG9ydCI6IjgwIiwiYmFubmVyIjoiIiwidnVsbmVyYWJpbGl0aWVzIjpbeyJpZCI6ICI5OTkxMDMiLCJyZWZlcmVuY2VzIjogImh0dHBzOi8vd3d3Lm5ldHNwYXJrZXIuY29tL3dlYi12dWxuZXJhYmlsaXR5LXNjYW5uZXIvdnVsbmVyYWJpbGl0aWVzL21pc3NpbmctY29udGVudC10eXBlLWhlYWRlci8iLCJtZXRob2QiOiJHRVQiLCJ1cmwiOiIvIiwibXNnIjoiVGhlIFgtQ29udGVudC1UeXBlLU9wdGlvbnMgaGVhZGVyIGlzIG5vdCBzZXQuIFRoaXMgY291bGQgYWxsb3cgdGhlIHVzZXIgYWdlbnQgdG8gcmVuZGVyIHRoZSBjb250ZW50IG9mIHRoZSBzaXRlIGluIGEgZGlmZmVyZW50IGZhc2hpb24gdG8gdGhlIE1JTUUgdHlwZS4ifSx7ImlkIjogIjYwMDU3NSIsIm1ldGhvZCI6IkhFQUQiLCJ1cmwiOiIvIiwibXNnIjoibmdpbngvMS4xOC4wIGFwcGVhcnMgdG8gYmUgb3V0ZGF0ZWQgKGN1cnJlbnQgaXMgYXQgbGVhc3QgMS4yNS4zKS4ifV19XQ==","tags":[]}]}
//   % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
//                                  Dload  Upload   Total   Spent    Left  Speed

//   0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
// 100   903  100   158  100   745   8777  41388 --:--:-- --:--:-- --:--:-- 53117
// {"detail":[{"type":"json_invalid","loc":["body",1],"msg":"JSON decode error","input":{},"ctx":{"error":"Expecting property name enclosed in double quotes"}}]}
// FINISHED

function b64encode(inp) {
  console.log(`Encoding: ${inp}`);
  return Buffer.from(inp).toString("base64");
}

let out;
let output_url;

async function main() {
  const input_url = process.argv[process.argv.length - 1];
  console.log(`Getting information from INPUT_URL: ${input_url}`);
  try {
    var boefje_input = JSON.parse(
      execSync(`curl --request GET --url ${input_url} -s`).toString(),
    );
  } catch (error) {
    console.error("FIRST FETCH WENT WRONG");
    console.error(error);
    return;
  }

  output_url = boefje_input.output_url;
  const ooi = boefje_input.boefje_meta.arguments.input.address;
  console.log(`Found boefje input with ooi: ${ooi}`);

  execSync(`./nikto/program/nikto.pl -h ${ooi} -o ./output.json`, {
    stdio: "inherit",
  });

  const file_contents = fs.readFileSync("./output.json").toString();
  return {
    status: "COMPLETED",
    files: [
      {
        content: b64encode(file_contents),
        tags: [],
      },
    ],
  };
}

main()
  .then((value) => {
    out = value;
  })
  .catch((reason) => {
    out = {
      status: "FAILED",
      files: [
        {
          content: b64encode(reason),
          tags: ["error/boefje"],
        },
      ],
    };
  })
  .finally(async () => {
    console.log("FINISHING...");
    if (out == undefined) return;

    try {
      console.log("SENDING OUT WITH:");
      console.log(JSON.stringify(out));
      console.log(output_url);
      const cmd = `curl --request POST --url ${output_url} --header "Content-Type: application/json" --data ${JSON.stringify(
        out,
      ).replaceAll('"', '\\"')}`;
      console.log(cmd);
      try {
        const x = execSync(cmd).toString();
        console.log(x);
        console.log("FINISHED");
      } catch (error) {
        console.error(error.status); // Might be 127 in your example.
        console.error(error.message); // Holds the message you typically want.
        console.error(error.stderr); // Holds the stderr output. Use `.toString()`.
        console.error(error.stdout); // Holds the stdout output. Use `.toString()`.
      }
    } catch (error) {
      console.error("SECOND FETCH WENT WRONG");
      console.error(error);
      return;
    }
  });
