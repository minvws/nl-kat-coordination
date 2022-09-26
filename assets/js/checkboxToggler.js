function toggleCheckboxesOn(name) {
  var checkbox = document.getElementsByName(name);
  for (var i = 0; i < checkbox.length; i++) {
    if (checkbox[i].type == 'checkbox')
      checkbox[i].checked = true;
  }
}

function toggleCheckboxesOff(name) {
  var checkbox = document.getElementsByName(name);
  for (var i = 0; i < checkbox.length; i++) {
    if (checkbox[i].type == 'checkbox')
      checkbox[i].checked = false;
  }
}


const toggle_all_ooi_types_btn = document.querySelector(".toggle-all-ooi-types");
toggle_all_ooi_types_btn.addEventListener("click", function () {
  if (toggle_all_ooi_types_btn.classList.contains("toggle-on")) {
    toggle_all_ooi_types_btn.classList.remove("toggle-on")
    toggleCheckboxesOff('ooi_type')
  } else {
    toggle_all_ooi_types_btn.classList.add("toggle-on")
    toggleCheckboxesOn('ooi_type')
  }

})


