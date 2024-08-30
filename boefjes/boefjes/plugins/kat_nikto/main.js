import fs from "node:fs";
import { execSync } from "node:child_process";
/**
 * @param {Object} boefje_meta Information about the task
 * @param {Object} boefje_meta.arguments
 * @param {Object} boefje_meta.arguments.input
 * @param {string} boefje_meta.arguments.input.object_type
 * @param {"http" | "https"} boefje_meta.arguments.input.scheme
 * @param {number} boefje_meta.arguments.input.port
 * @param {Object} boefje_meta.arguments.input.netloc
 * @param {string} boefje_meta.arguments.input.netloc.name
 * @returns {(string | string[])[][]}
 */
export default function (boefje_meta) {
  // Depending on what OOI triggered this task, the hostname / address will be in a different location
  const hostname = boefje_meta.arguments.input.netloc.name;
  const scheme = boefje_meta.arguments.input.scheme;

  let command = `./nikto/program/nikto.pl -h ${hostname} -o ./output.json -404code=301,302,307,308`;
  if (scheme == "https") command += " -ssl";

  // Running nikto and outputting to a file
  try {
    execSync(command, {
      stdio: "inherit",
    });
  } catch (e) {
    console.error(e);
    throw new Error("Something went wrong running the nikto command.\n");
  }

  const raws = [];

  // Reading the file created by nikto
  try {
    var file_contents = fs.readFileSync("./output.json").toString();
    raws.push([["boefje/nikto-output"], file_contents]);
  } catch (e) {
    console.error(e.message);
    throw new Error(
      "Something went wrong reading the file from the nikto command.\n" +
        e.message,
    );
  }

  // Looking if outdated software has been found
  try {
    const data = JSON.parse(file_contents);
    for (const vulnerability of data["vulnerabilities"])
      if (vulnerability["id"].startsWith("6"))
        raws.push([["openkat/finding"], "KAT-OUTDATED-SOFTWARE"]);
  } catch (e) {
    console.error(e.message);
  }

  return raws;
}
