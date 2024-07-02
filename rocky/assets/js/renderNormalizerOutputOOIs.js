import { language, organization_code } from "./utils.js";

const buttons = document.querySelectorAll(
  ".expando-button.normalizer-list-table-row",
);
const asyncoffset = 5; // time (in seconds) to allow for the database to actually save the OOIs

buttons.forEach((button) => {
  const raw_task_id = button.closest("tr").getAttribute("data-task-id");
  const task_id = button
    .closest("tr")
    .getAttribute("data-task-id")
    .replace(/-/g, "");
  const json_url =
    "/" +
    language +
    "/" +
    organization_code +
    "/tasks/normalizers/" +
    encodeURI(task_id);

  const getJson = (url, callback) => {
    var xhr = new XMLHttpRequest();
    xhr.open("GET", url, true);
    xhr.responseType = "json";
    xhr.onload = function () {
      var status = xhr.status;
      if (status === 200) {
        const error_messages = button
          .closest("tr")
          .nextElementSibling.querySelectorAll(".error");
        error_messages.forEach((element) => {
          element.remove();
        });

        callback(xhr.response);
      } else {
        // Create HTML elements to build a snippet containing the error message.
        let error_element = document.createElement("div");
        let error_text_element = document.createElement("p");

        error_text_element.innerText =
          "Retrieving yielded objects resulted in a Sever Error: Status code ";
        error_element.appendChild(error_text_element);
        error_element.classList.add("error");

        // Log the error in the console.
        console.log(
          "Server Error: Retrieving yielded objects failed. Server response: Status code " +
            xhr.status +
            " - " +
            xhr.statusText,
        );

        // Insert the HTML snippet into the expando row, which is the buttons parent TR next TR-element sibling.
        button
          .closest("tr")
          .nextElementSibling.querySelector("#yielded-objects-" + raw_task_id)
          .appendChild(error_element);
      }
    };
    xhr.send();
  };

  let element = document.createElement("p");
  element.classList.add("yielded-objects-paragraph");
  button.addEventListener("click", function () {
    // Make sure there are no yielded objecst rendered, so we don't do unnecessary GET requests.
    if (
      !button
        .closest("tr")
        .nextElementSibling.querySelector("#yielded-objects-" + raw_task_id)
        .querySelector(".yielded-objects-paragraph")
    ) {
      // Retrieve JSON containing yielded objects of task.
      getJson(json_url, function (data) {
        if (data["oois"].length > 0) {
          const url =
            "/" +
            language +
            "/" +
            escapeHTMLEntities(encodeURIComponent(organization_code));
          let object_list = "";
          // set the observed at time a fews seconds into the future, as the job finish time is not the same as the ooi-creation time. Due to async reasons the object might be a bit slow.
          data["timestamp"] = Date.parse(data["valid_time"]);
          data["valid_time_async"] = new Date(data["timestamp"] + asyncoffset)
            .toISOString()
            .substring(0, 19); // strip miliseconds
          // Build HTML snippet for every yielded object.
          data["oois"].forEach((object) => {
            object_list += `<li><a href='${url}/objects/detail/?observed_at=${data["valid_time_async"]}&ooi_id=${escapeHTMLEntities(encodeURIComponent(object))}'>${escapeHTMLEntities(object)}</a></li>`;
          });
          element.innerHTML = `<ul>${object_list}</ul>`;
        } else {
          element.innerText = "Normalizer task yielded no objects.";
        }
      });

      // Insert HTML snippet into the expando row, which is the buttons parent TR next TR-element sibling.
      button
        .closest("tr")
        .nextElementSibling.querySelector("#yielded-objects-" + raw_task_id)
        .appendChild(element);
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
