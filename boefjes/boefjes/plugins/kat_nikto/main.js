import fs from "node:fs";
import { execSync } from "node:child_process";

/**
 * @param {{}} boefje_meta The string input to base64 encode
 * @returns {(string | string[])[][]}
 */
export default function (boefje_meta) {
  // Depending on what OOI triggered this task, the hostname / address will be in a different location
  const object_type = boefje_meta.arguments.input.object_type;
  let ooi = "";
  if (["IPAddressV4", "IPAddressV6"].includes(object_type))
    ooi = boefje_meta.arguments.input.address;
  else if (object_type == "Hostname") ooi = boefje_meta.arguments.input.name;
  else throw new Error("Unexpected boefje_meta");

  // Running nikto and outputting to a file
  try {
    execSync(`./nikto/program/nikto.pl -h ${ooi} -o ./output.json`, {
      stdio: "inherit",
    });
  } catch (e) {
    console.error(e);
    throw new Error(
      "Something went wrong running the nikto command.\n" + e.message,
    );
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
