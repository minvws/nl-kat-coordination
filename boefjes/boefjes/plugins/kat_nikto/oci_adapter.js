import { request as httpRequest } from "node:http";
import { request as httpsRequest } from "node:https";
import { readFileSync } from "node:fs";
import { URL } from "node:url";
import run from "./main.js";

/**
 * @param {string} inp The string input to base64
 * @returns {string}
 */
function b64encode(inp) {
  return Buffer.from(inp).toString("base64");
}

/**
 * @param {string} inp The string input to cleaned for Logging usage
 * @returns {string}
 */
function sanitizeLog(inp) {
  return String(inp)
    .replace(/[\r\n]+/g, " ") // Remove newlines
    .replace(/[\x1B\x9B][[()#;?]*[0-9]{1,4}[0-9;]*[A-Za-z]/g, "") // Remove ANSI escape codes
    .replace(/[^\x20-\x7E]+/g, ""); // Remove non-printable characters
}

/**
 * Optional custom CA, if provided via env
 */
let customCA = undefined;
if (process.env.CA_PATH) {
  try {
    customCA = readFileSync(process.env.CA_PATH);
  } catch (error) {
    console.error(
      `Failed to read custom CA file at ${sanitizeLog(process.env.CA_PATH)}:`,
      sanitizeLog(error.message),
    );
    process.exit(1);
  }
}

/**
 * Make an HTTP(S) GET request and return the parsed JSON response.
 * @param {string} urlStr
 * @returns {Promise<any>}
 */
function fetchJson(urlStr) {
  const url = new URL(urlStr);
  const isHttps = url.protocol === "https:";
  const client = isHttps ? httpsRequest : httpRequest;

  const options = {
    hostname: url.hostname,
    path: url.pathname + url.search,
    port: url.port || (isHttps ? 443 : 80),
    method: "GET",
    ...(isHttps && customCA ? { ca: customCA } : {}),
  };

  return new Promise((resolve, reject) => {
    const req = client(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch (err) {
          reject(new Error("Invalid JSON response: " + err.message));
        }
      });
    });

    req.on("error", (err) => reject(err));
    req.end();
  });
}

/**
 * Send a POST request with JSON data
 * @param {string} urlStr
 * @param {any} jsonData
 * @returns {Promise<void>}
 */
function postJson(urlStr, jsonData) {
  const url = new URL(urlStr);
  const isHttps = url.protocol === "https:";
  const client = isHttps ? httpsRequest : httpRequest;
  const data = JSON.stringify(jsonData);

  const options = {
    hostname: url.hostname,
    path: url.pathname + url.search,
    port: url.port || (isHttps ? 443 : 80),
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Content-Length": Buffer.byteLength(data),
    },
    ...(isHttps && customCA ? { ca: customCA } : {}),
  };

  return new Promise((resolve, reject) => {
    const req = client(options, (res) => {
      res.on("data", () => {}); // optional: consume response
      res.on("end", resolve);
    });

    req.on("error", (err) => reject(err));
    req.write(data);
    req.end();
  });
}

async function main() {
  const input_url = process.argv[process.argv.length - 1];

  let boefje_input;
  try {
    boefje_input = await fetchJson(input_url);
  } catch (error) {
    console.error(
      `Getting boefje input went wrong with URL: ${sanitizeLog(input_url)}`,
    );
    throw error;
  }

  Object.assign(process.env, boefje_input["boefje_meta"]["environment"]);

  let out;
  const output_url = boefje_input.output_url;
  try {
    const raws = run(boefje_input.boefje_meta);
    out = {
      status: "COMPLETED",
      files: raws.map((x) => ({
        content: b64encode(x[1]),
        tags: x[0],
      })),
    };
  } catch (error) {
    out = {
      status: "FAILED",
      files: [
        {
          content: b64encode("Boefje caught an error: " + error.message),
          tags: ["error/boefje"],
        },
      ],
    };
  }

  try {
    await postJson(output_url, out);
  } catch (error) {
    console.error(
      `Failed to POST output to ${sanitizeLog(output_url)}:`,
      sanitizeLog(error.message),
    );
    throw error;
  }
}

main();
