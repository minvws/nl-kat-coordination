import { execSync } from "node:child_process";
import run from "./main.js";

/**
 * @param {string} inp The string input to base64
 * @returns {string}
 */
function b64encode(inp) {
  console.log(`Encoding: ${inp}`);
  return Buffer.from(inp).toString("base64");
}

let out;
let output_url;

async function main() {
  const input_url = process.argv[process.argv.length - 1];

  // Getting the boefje input
  try {
    var boefje_input = JSON.parse(
      execSync(`curl --request GET --url ${input_url} -s`).toString(),
    );
  } catch (error) {
    console.error(`Getting boefje input went wrong with URL: ${input_url}`);
    throw new Error(error);
  }

  output_url = boefje_input.output_url;
  const raws = run(boefje_input.boefje_meta);
  console.log("RAWS: " + JSON.stringify(raws));
  return {
    status: "COMPLETED",
    files: raws.map((x) => ({
      content: b64encode(x[1]),
      tags: x[0],
    })),
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
          content: b64encode("main caught an error: " + reason),
          tags: ["error/boefje"],
        },
      ],
    };
  })
  .finally(async () => {
    console.log("Finishing with: " + out);
    if (out == undefined) return console.error("`out` is undefined.");

    try {
      console.log("SENDING OUT WITH: " + JSON.stringify(out));
      const cmd = `curl --request POST --url ${output_url} --header "Content-Type: application/json" --data ${JSON.stringify(
        out,
      ).replaceAll('"', '\\"')}`;
      console.log(cmd);
      try {
        execSync(cmd).toString();
        console.log("FINISHED");
      } catch (error) {
        console.error(
          "Something went wrong outputting to the boefje api: " + error.message,
        );
      }
    } catch (error) {
      console.error("SECOND FETCH WENT WRONG: " + error);
    }
  });
