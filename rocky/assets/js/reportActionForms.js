export function renderRenameSelection(modal, selection) {
  let form_element = document.getElementById("rename-form");
  let csrf_token_element = form_element.querySelector(
    "input[name='csrfmiddlewaretoken']",
  );
  let report_names = getReportNames(selection);

  let content_element = modal.querySelector(".content");
  content_element.innerHTML = "";

  let header_element = document.createElement("h3");
  header_element.innerText = "Rename the following report(s):";

  let table_element = document.createElement("table");
  let table_heading_row_element = document.createElement("tr");
  let th_type_element = document.createElement("th");
  th_type_element.innerText = "Report type";
  let th_name_element = document.createElement("th");
  th_name_element.innerText = "Name";
  let th_date_element = document.createElement("th");
  th_date_element.innerText = "Add reference date";

  table_heading_row_element.appendChild(th_type_element);
  table_heading_row_element.appendChild(th_name_element);
  table_heading_row_element.appendChild(th_date_element);
  table_element.appendChild(table_heading_row_element);

  report_names.forEach((report_name) => {
    let table_row_element = document.createElement("tr");
    let td_type_element = document.createElement("td");
    let td_name_element = document.createElement("td");
    let td_date_element = document.createElement("td");

    let name_input_element = document.createElement("input");
    name_input_element.setAttribute("type", "text");
    name_input_element.setAttribute("value", report_name);
    name_input_element.setAttribute("name", "report_name");

    let reference_input_element = document.createElement("input");
    reference_input_element.setAttribute("type", "hidden");
    reference_input_element.setAttribute("value", report_name);
    reference_input_element.setAttribute("name", "report_reference");

    td_type_element.innerText = "type";
    td_name_element.appendChild(reference_input_element);
    td_name_element.appendChild(name_input_element);
    td_date_element.innerText = "date";
    table_row_element.appendChild(td_type_element);
    table_row_element.appendChild(td_name_element);
    table_row_element.appendChild(td_date_element);
    table_element.appendChild(table_row_element);
  });

  form_element.appendChild(table_element);
  content_element.appendChild(csrf_token_element);
  content_element.appendChild(header_element);
  content_element.appendChild(form_element);
}

export function renderDeleteSelection(modal, selection) {
  let form_element = document.getElementById("delete-form");
  let csrf_token_element = form_element.querySelector(
    "input[name='csrfmiddlewaretoken']",
  );
  let report_names = getReportNames(selection);

  let content_element = modal.querySelector(".content");
  content_element.innerHTML = "";

  let header_element = document.createElement("h3");
  header_element.innerText =
    "Are you sure you want to permanently delete the following report(s):";

  report_names.forEach((report_name) => {
    let name_input_element = document.createElement("input");
    name_input_element.setAttribute("type", "text");
    name_input_element.setAttribute("value", report_name);
    name_input_element.setAttribute("readonly", "true");

    let reference_input_element = document.createElement("input");
    reference_input_element.setAttribute("type", "hidden");
    reference_input_element.setAttribute("value", report_name);
    reference_input_element.setAttribute("name", "report_reference");

    form_element.appendChild(reference_input_element);
    form_element.appendChild(name_input_element);
  });

  content_element.appendChild(csrf_token_element);
  content_element.appendChild(header_element);
  content_element.appendChild(form_element);
}

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
