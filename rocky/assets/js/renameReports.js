function editReportName() {
  const old_name_id = document.getElementById("old-report-name").value;
  const new_name = document.getElementById("new-report-name").value;

  const update_cell = document.getElementById(old_name_id);
  update_cell.innerHTML = new_name;
}

document.addEventListener("DOMContentLoaded", function () {
  confirm_id.addEventListener("click", function (event) {
    const old_report_name = event.target
      .closest("dialog")
      .querySelector(".old-report-name").value;
    const confirm_button = event.target
      .closest("dialog")
      .getElementById("confirm");
  });
});
