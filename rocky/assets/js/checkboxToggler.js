const toggle_all_btn = document.querySelectorAll(".toggle-all");
for (var i = 0; i < toggle_all_btn.length; i++) {
  toggle_all_btn[i].addEventListener("click", function (event) {
    var toggle_target = event.target.dataset.toggleTarget;
    toggleCheckboxes(toggle_target, !this.classList.contains('toggle-on'));
    this.classList.toggle('toggle-on');
  })
};

function toggleCheckboxes(name, value) {
  var checkboxes = document.getElementsByName(name);
  for (var i = 0; i < checkboxes.length; i++) {
    if (checkboxes[i].type == 'checkbox') {
      checkboxes[i].checked = value;
    }
  };
}