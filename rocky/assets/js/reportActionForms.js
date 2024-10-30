export function renderRenameSelection(modal, selection) {
  let report_names = getReportNames(selection);
  let references = [];

  selection.forEach((input_element) => {
    references.push(input_element.value);
  });

  let table_element = document.getElementById("rename-table");
  let table_body = table_element.querySelector("tbody");
  let table_row = table_element.querySelector("tr.rename-table-row");
  console.log(table_row);

  table_body.innerHTML = "";

  for (let i = 0; i < references.length; i++) {
    let table_row_copy = table_row.cloneNode(true);
    console.log(table_row_copy);

    let type_td = table_row_copy.querySelector("td.type");
    let name_input_element = table_row_copy.querySelector(".report-name-input");
    let reference_input_element = table_row_copy.querySelector(
      ".report-reference-input",
    );
    let date_td = table_row_copy.querySelector("td.date");

    name_input_element.setAttribute("value", report_names[i]);
    reference_input_element.setAttribute("value", references[i]);

    type_td.innerText = "type";
    date_td.innerText = "date";

    table_body.appendChild(table_row_copy);
  }
}

export function renderDeleteSelection(modal, selection) {
  let report_names = getReportNames(selection);
  let references = [];

  selection.forEach((input_element) => {
    references.push(input_element.value);
  });

  let table_element = document.getElementById("delete-table");
  let table_body = table_element.querySelector("tbody");
  let table_row = table_element.querySelector("tr.delete-table-row");
  console.log(table_row);

  table_body.innerHTML = "";

  for (let i = 0; i < references.length; i++) {
    let table_row_copy = table_row.cloneNode(true);
    console.log(table_row_copy);

    let reference_input_element = table_row_copy.querySelector(
      ".report-reference-input",
    );

    let type_td = table_row_copy.querySelector("td.type");
    let name_td = table_row_copy.querySelector("td.name");
    let date_td = table_row_copy.querySelector("td.date");

    name_td.innerText += report_names[i];
    reference_input_element.setAttribute("value", references[i]);

    type_td.innerText = "type";
    date_td.innerText = "date";

    table_body.appendChild(table_row_copy);
  }
}

// export function renderDeleteSelection(modal, selection) {
//   let form_element = document.getElementById("delete-form");
//   let csrf_token_element = form_element.querySelector(
//     "input[name='csrfmiddlewaretoken']",
//   );
//   let report_names = getReportNames(selection);

//   let content_element = modal.querySelector(".content");
//   content_element.innerHTML = "";

//   let header_element = document.createElement("h3");
//   header_element.innerText =
//     "Are you sure you want to permanently delete the following report(s):";

//   report_names.forEach((report_name) => {
//     let name_input_element = document.createElement("input");
//     name_input_element.setAttribute("type", "text");
//     name_input_element.setAttribute("value", report_name);
//     name_input_element.setAttribute("readonly", "true");

//     let reference_input_element = document.createElement("input");
//     reference_input_element.setAttribute("type", "hidden");
//     reference_input_element.setAttribute("value", report_name);
//     reference_input_element.setAttribute("name", "report_reference");

//     form_element.appendChild(reference_input_element);
//     form_element.appendChild(name_input_element);
//   });

//   content_element.appendChild(csrf_token_element);
//   content_element.appendChild(header_element);
//   content_element.appendChild(form_element);
// }

export function getReportNames(selection) {
  let report_names = [];

  for (let i = 0; i < selection.length; i++) {
    let report_name = selection[i]
      .closest("tr")
      ?.querySelector("td.report_name a")?.innerText;

    if (!report_name) {
      continue;
    }

    report_names.push(report_name);
  }

  return report_names;
}
