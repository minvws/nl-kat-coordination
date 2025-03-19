const htmlElement = document.getElementsByTagName("html")[0];
const language = htmlElement.getAttribute("lang");
const organization_code = htmlElement.getAttribute("data-organization-code");

const buttons = document.querySelectorAll(
  ".expando-button.boefjes-task-list-table-row",
);

buttons.forEach((button) => {
  const raw_task_id = button.closest("tr").getAttribute("data-task-id");
  const task_id = button
    .closest("tr")
    .getAttribute("data-task-id")
    .replace(/-/g, "");
  const organization =
    organization_code ||
    button.closest("tr").getAttribute("data-organization-code");
  const json_url =
    "/" +
    language +
    "/" +
    organization +
    "/bytes/" +
    encodeURI(task_id) +
    "/raw?format=json";

  const getJson = (url, callback) => {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = "json";
    xhr.onload = function () {
      var status = xhr.status;

      const messages = button
        .closest("tr")
        .nextElementSibling.querySelectorAll(".error, .explanation");
      messages.forEach((element) => {
        element.remove();
      });

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

        // Insert the HTML snippet into the expando row, which is the buttons parent TR next TR-element sibling.
        button
          .closest("tr")
          .nextElementSibling.querySelector("#yielded-rawfiles-" + raw_task_id)
          .appendChild(error_element);
      }
    };
    xhr.send();
  };

  let element = document.createElement("div");
  element.classList.add("yielded-rawfiles");
  button.addEventListener("click", function () {
    // Make sure there are no yielded objecst rendered, so we don't do unnecessary GET requests.
    if (
      !button
        .closest("tr")
        .nextElementSibling.querySelector("#yielded-rawfiles-" + raw_task_id)
        .querySelector(".yielded-rawfiles")
    ) {
      // Retrieve JSON containing yielded raw files of task.
      getJson(json_url, function (data) {
        if (data.length > 0) {
          let rawfiles_list = document.createElement("div");
          // Build HTML snippet for every yielded rawfiles.
          data.forEach((rawfile) => {
            mimetypes = "";
            rawfile["mime_types"].forEach((mime_type) => {
              mimetypes += `<li>${mime_type["value"]}</li>`;
            });
            rawdata = atob(rawfile["raw_file"]);
            let rawfile_container = document.createElement("div");
            rawfile_container.innerHTML = `<h3>${rawfile["id"]}</h3>
            <p>Secure Hash: ${rawfile["secure_hash"]}, signed by ${rawfile["signing_provider_url"]}</p>
            <h4>Mimetypes:</h4>
              <ul>${mimetypes}</ul>
            <h4>Content:</h4>
            <pre></pre>`;
            rawfile_container.querySelector("pre").innerText = rawdata;
            rawfiles_list.appendChild(rawfile_container);
          });

          element.appendChild(rawfiles_list);
        } else {
          element.innerHTML =
            "<p class='explanation'>Boefje task yielded no raw files.</p>";
        }
      });

      // Insert HTML snippet into the expando row, which is the buttons parent TR next TR-element sibling.
      button
        .closest("tr")
        .nextElementSibling.querySelector("#yielded-rawfiles-" + raw_task_id)
        .appendChild(element);
    } else {
      return;
    }
  });
});
