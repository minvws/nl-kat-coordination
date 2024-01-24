const toggle_all_btn = document.querySelectorAll('.toggle-all');
for (var i = 0; i < toggle_all_btn.length; i++) {
  toggle_all_btn[i].addEventListener('click', function (event) {
    var toggle_target = event.target.dataset.toggleTarget;
    toggleCheckboxes(toggle_target, !this.classList.contains('toggle-on'));
    this.classList.toggle('toggle-on');
  });
};

function toggleCheckboxes(name, value) {
  var checkboxes = document.getElementsByName(name);
  for (var i = 0; i < checkboxes.length; i++) {
    if (checkboxes[i].tagName == 'INPUT' && checkboxes[i].type == 'checkbox') {
      checkboxes[i].checked = value;
    }
  }
}

const checkbox_required_anchors = document.querySelectorAll('.checkboxes_required');
for (var i = 0; i < checkbox_required_anchors.length; i++){
  let anchor = checkbox_required_anchors[i];
  if (anchor.tagName == 'INPUT' && anchor.type == 'checkbox'){
    // we are looking at a checkbox itself, assume we want all checkboxes with the same name in the same form
    var form = anchor.form;
    var collection = form.getElementsByName(anchor.name);
  } else if (anchor.tagName == 'FORM'){
    var form = anchor;
    var collection = anchor.querySelectorAll('input[type=checkbox]');
  } else {
    // we are looking at a parent of a group of checkboxes. lets collect all underlying checkboxes.
    var collection = anchor.querySelectorAll('input[type=checkbox]');
    var form = collection[0].form;
  }
  form.addEventListener('submit', checkbox_required_validity.bind(null, form, anchor));
};

function checkbox_required_validity(form, anchor, event) {
  //  validate the current list of checkboxes against the current min/max required settings only at submit time.
  var selected_count = 0;
  var error_element = null;
  if (anchor.tagName == 'INPUT' && anchor.type == 'checkbox'){
    // we are looking at a checkbox itself, assume we want all checkboxes with the same name in the same form
    var name = anchor.name;
    selected_count = anchor.form.querySelectorAll('input[type=checkbox][name='+name+']:checked').length;
    error_element = anchor.form.querySelector('input[type=checkbox][name='+name+']');
  } else if (anchor.tagName == 'FORM'){
    selected_count = anchor.querySelectorAll('input[type=checkbox]:checked').length;
    error_element = anchor.querySelector('input[type=checkbox]');
  } else {
    // we are looking at a parent of a group of checkboxes. lets collect all underlying checkboxes.
    selected_count = anchor.querySelectorAll('input[type=checkbox]:checked').length;
    error_element = anchor.form.querySelector('input[type=checkbox]');
  }

  var minselected = 1;
  var validity = true;
  error_element.setCustomValidity('');
  if ((("min" in anchor.dataset) && anchor.dataset.min > selected_count) || minselected > selected_count) {
    error_element.setCustomValidity('Not enough checkboxes selected, select at least: '+(("min" in anchor.dataset) && anchor.dataset.min || minselected));
    validity = false;
    event.preventDefault();
  } else if (("max" in anchor.dataset) && anchor.dataset.max < selected_count) {
    error_element.setCustomValidity('Too many checkboxes selected. select at most: '+anchor.dataset.max);
    validity = false;
    event.preventDefault();
  }
  error_element.addEventListener('change', function(event){
    // we need to remove the custom error on change, because otherwise the submit code won't run.
    if(event.target.checked){
      event.target.setCustomValidity('');
    }
  });
  error_element.reportValidity();
  return validity;
}
