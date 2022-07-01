function toggleCheckboxes(checkboxName) {
  checkboxes = document.getElementsByName(checkboxName);
  checked = !allCheckboxesChecked(checkboxName);
  
  for (var i=0,n=checkboxes.length;i<n;i++) {
    checkboxes[i].checked = checked;
  }
}

function allCheckboxesChecked(checkboxName) {
  checkboxes = document.getElementsByName(checkboxName);

  for (var i=0,n=checkboxes.length;i<n;i++) {
    if (!checkboxes[i].checked) {
      return false;
    }
  }

  return true;
}
