const htmlElement = document.getElementsByTagName("html")[0];
const language = htmlElement.getAttribute("lang");
const file_raw_buttons = document.querySelectorAll(".button-file-raw");

file_raw_buttons.forEach((button) => {
  const file_id = button.closest("tr").getAttribute("data-file-id");
  const file_url = button.closest("tr").getAttribute("data-file-url");
  const expando_row = button.closest("tr").nextElementSibling.children[0];

  const getFile = (url, callback) => {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = "text";
    xhr.onload = function () {
      var status = xhr.status;

      if (status === 200) {
        callback(xhr.response);
      } else {
        // Create HTML elements to build a snippet containing the error message.
        let error_element = document.createElement("div");
        let error_text_element = document.createElement("p");

        error_text_element.innerText =
          "Retrieving yielded raw files resulted in a Sever Error: Status code ";
        error_element.appendChild(error_text_element);
        error_element.classList.add("error");

        // Log the error in the console.
        console.log(
          "Server Error: Retrieving yielded raw files failed. Server response: Status code " +
            xhr.status +
            " - " +
            xhr.statusText,
        );
      }
    };
    xhr.send();
  };

  button.addEventListener("click", function () {
    getFile(file_url, function (data) {
      if (expando_row.children.length > 0) {
        return;
      }
      let rawfiles_element = document.createElement("div");
      if (data.length > 0) {
        let rawfile_container = document.createElement("div");
        rawfile_container.innerHTML = `<div role="tablist"
                       aria-labelledby="raw-file-${file_id}"
                       class="manual">
                        <div class="button-container">
                            <button id="plain-${file_id}"
                                type="button"
                                role="tab"
                                aria-selected="true"
                                aria-controls="plain-${file_id}-panel">
                                Plain text
                            </button>
                            <button id="json-${file_id}"
                                type="button"
                                role="tab"
                                aria-selected="false"
                                aria-controls="json-${file_id}-panel">
                                Json
                            </button>
                            <button id="hex-${file_id}"
                                type="button"
                                role="tab"
                                aria-selected="false"
                                aria-controls="hex-${file_id}-panel">
                                HEX view
                            </button>
                        </div>
                    <div id="plain-${file_id}-panel"
                       role="tabpanel"
                       aria-labelledby="#plain-${file_id}">
                        <pre class="plain"><code></code></pre>
                    </div>
                    <div id="json-${file_id}-panel"
                       role="tabpanel"
                       aria-labelledby="#json-${file_id}-panel"
                       class="hidden">
                        <pre class="json"></pre>
                    </div>
                    <div id="hex-${file_id}-panel"
                       role="tabpanel"
                       aria-labelledby="#hex-${file_id}"
                       class="hidden">
                      <table class="hex"></table>
                    </div>`;
        console.log(data);
        rawfile_container.querySelector("pre.plain code").innerText = data;
        try {
          jsondata = JSON.parse(data);
          rawfile_container.querySelector("pre.json").innerText =
            JSON.stringify(jsondata, null, "\t");
          rawfile_container
            .querySelector("pre.json")
            .classList.remove("hidden");
          rawfile_container
            .querySelector(`#hex-${file_id}`)
            .classList.add("hidden");
          rawfile_container
            .querySelector(`#hex-${file_id}-panel`)
            .classList.add("hidden");
        } catch (e) {
          rawfile_container
            .querySelector(`#json-${file_id}-panel`)
            .classList.add("hidden");
          rawfile_container
            .querySelector(`#json-${file_id}`)
            .classList.add("hidden");
          let hex_table = rawfile_container.querySelector("table.hex");
          let rawbytes = new TextEncoder();
          renderHexTable(hex_table, rawbytes.encode(data));
        }

        rawfiles_element.appendChild(rawfile_container);
      } else {
        rawfiles_element.innerHTML =
          "<p class='explanation'>File is empty.</p>";
      }
      expando_row.appendChild(rawfiles_element);
      initTablist();
    });
  });
});

function renderHexTable(hex_table, bytes) {
  const rowLength = 16;

  const headerRow = document.createElement("tr");
  headerRow.innerHTML =
    "<th>Offset</th>" +
    Array.from(
      { length: rowLength },
      (_, i) => `<th>${i.toString(16).padStart(2, "0").toUpperCase()}</th>`,
    ).join("") +
    "<th>ASCII</th>";
  hex_table.appendChild(headerRow);

  for (let i = 0; i < bytes.length; i += rowLength) {
    const row = document.createElement("tr");
    const offset = i.toString(16).padStart(8, "0").toUpperCase();
    const hexBytes = [];
    const ascii = [];

    for (let j = 0; j < rowLength; j++) {
      const byte = bytes[i + j];
      if (byte !== undefined) {
        hexBytes.push(byte.toString(16).padStart(2, "0").toUpperCase());
        const char =
          byte >= 32 && byte <= 126 ? String.fromCharCode(byte) : ".";
        ascii.push(char);
      } else {
        hexBytes.push("  ");
        ascii.push("."); // placeholder char
      }
    }
    row.addEventListener("mouseover", (event) => {
      let charposition = Array.from(event.target.parentNode.children).indexOf(
        event.target,
      );
      if (charposition > 0) {
        let asciistring =
          event.target.parentElement.querySelector(".ascii").textContent;
        let highlightedstring =
          asciistring.substring(0, charposition - 1) +
          "<span class='highlight'>" +
          escapeHTMLEntities(asciistring.charAt(charposition - 1)) +
          "</span>" +
          asciistring.substring(charposition);
        event.target.parentElement.querySelector(".ascii").innerHTML =
          highlightedstring;
      }
    });
    row.addEventListener("mouseout", (event) => {
      event.target.parentElement.querySelector(".ascii").innerText =
        event.target.parentElement.querySelector(".ascii").innerText;
    });

    row.innerHTML =
      `<td>${offset}</td>` +
      hexBytes.map((b) => `<td>${b}</td>`).join("") +
      `<td class="ascii">${ascii.join("")}</td>`;
    hex_table.appendChild(row);
  }
}

function escapeHTMLEntities(input) {
  var output = input.replace(/'/g, "&apos;");
  output = output.replace(/"/g, "&quot;");
  output = output.replace(/</g, "&lt;");
  return output.replace(/>/g, "&gt;");
}
