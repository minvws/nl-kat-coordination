function toggleCheckboxes(event, checkboxName) {
  if(event.target.type == "checkbox") {
    let checked = event.target.checked = !event.target.checked;

    if(!checked) {
      setAllCheckboxes(checkboxName, true)
      event.target.checked = true;
    }
    else {
      if(allCheckboxesChecked(checkboxName)) {
        setAllCheckboxes(checkboxName, false)
        event.target.checked = false;
      } else {
        setAllCheckboxes(checkboxName, true);
      }
    }
  }
  else {
    if(allCheckboxesChecked(checkboxName)) {
      setAllCheckboxes(checkboxName, false);
    } else {
      setAllCheckboxes(checkboxName, true);
    }
  }
}

function setAllCheckboxes(checkboxName, state) {
  let checkboxes = document.getElementsByName(checkboxName);

  for (var i = 0, n = checkboxes.length; i < n; i++) {
    if(state === null){
      checkboxes[i].checked = !checkboxes[i].checked;
    } else {
      checkboxes[i].checked = state;
    }
  }
}

function allCheckboxesChecked(checkboxName) {
  return !document.querySelectorAll('input[name='+checkboxName+']:not(:checked)').length > 0;
}
