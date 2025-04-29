const htmlElement = document.getElementsByTagName("html")[0];
const language = htmlElement.getAttribute("lang");
const organization_code = htmlElement.getAttribute("data-organization-code");
const asyncoffset = 5; // time (in seconds) to allow for the database to actually save the OOIs
const task_buttons = document.querySelectorAll(
  ".expando-button.boefjes-task-list-table-row, .expando-button.normalizer-list-table-row",
);
task_buttons.forEach((button) => {
  const raw_task_id = button.closest("tr").getAttribute("data-task-id");
  const task_id = button
    .closest("tr")
    .getAttribute("data-task-id")
    .replace(/-/g, "");
  const organization =
    organization_code ||
    button.closest("tr").getAttribute("data-organization-code");
  const task_type = button.closest("tr").getAttribute("data-task-type");
  const expando_row = button.closest("tr").nextElementSibling;
  var json_url = "";
  if (task_type == "boefje") {
    json_url =
      "/" +
      language +
      "/" +
      organization +
      "/bytes/" +
      encodeURI(task_id) +
      "/raw?format=json";
  } else {
    json_url =
      "/" +
      language +
      "/" +
      organization +
      "/tasks/normalizers/" +
      encodeURI(task_id);
  }
  const getJson = (url, callback) => {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = "json";
    xhr.onload = function () {
      var status = xhr.status;

      const messages = expando_row.querySelectorAll(".error, .explanation");
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
        expando_row
          .querySelector("#yielded-rawfiles-" + raw_task_id)
          .appendChild(error_element);
      }
    };
    xhr.send();
  };

  button.addEventListener("click", function () {
    // only load the results once, by checking if we are already showing output
    if (
      !button
        .closest("tr")
        .nextElementSibling.querySelector(".yielded-rawfiles, .yielded-objects")
    ) {
      // Retrieve JSON containing yielded raw files or oois of task.
      getJson(json_url, function (data) {
        let rawfiles_element = document.createElement("div");
        rawfiles_element.classList.add("yielded-rawfiles");

        let yielded_objects_element = document.createElement("div");
        yielded_objects_element.classList.add("yielded-objects");
        if (data["oois"] && data["oois"].length > 0) {
          const url =
            "/" +
            language +
            "/" +
            escapeHTMLEntities(encodeURIComponent(organization));
          let object_list = "";
          // set the observed at time a fews seconds into the future, as the job finish time is not the same as the ooi-creation time. Due to async reasons the object might be a bit slow.
          data["timestamp"] = Date.parse(data["valid_time"] + "Z");
          data["valid_time_async"] = new Date(
            data["timestamp"] + asyncoffset * 1000,
          )
            .toISOString()
            .substring(0, 19); // strip milliseconds
          // Build HTML snippet for every yielded object.
          data["oois"].forEach((object) => {
            object_list += `<li><a href='${url}/objects/detail/?observed_at=${data["valid_time_async"]}&ooi_id=${escapeHTMLEntities(encodeURIComponent(object))}'>${escapeHTMLEntities(object)}</a></li>`;
          });
          yielded_objects_element.innerHTML = `<ul>${object_list}</ul>`;
        } else if (task_type == "normalizer") {
          yielded_objects_element.innerHTML =
            "<p class='explanation'>task yielded no objects.</p>";
        }
        expando_row
          .querySelector("#yielded-objects-" + raw_task_id)
          .appendChild(yielded_objects_element);

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

          rawfiles_element.appendChild(rawfiles_list);
        } else if (task_type == "boefje") {
          rawfiles_element.innerHTML =
            "<p class='explanation'>Task yielded no raw files.</p>";
        }
        // Insert HTML snippet into the expando row, which is the buttons parent TR next TR-element sibling.
        expando_row
          .querySelector("#yielded-rawfiles-" + raw_task_id)
          .appendChild(rawfiles_element);
      });
    } else {
      return;
    }
  });
});

function escapeHTMLEntities(input) {
  var output = input.replace(/'/g, "&apos;");
  output = output.replace(/"/g, "&quot;");
  output = output.replace(/</g, "&lt;");
  return output.replace(/>/g, "&gt;");
}
