function toggleChoice(form, group, value) {
  // Groups are input/label pairs i their respective parent Div's
  // find all groups that are bound to this toggler by its data-choicegroup atribute value
  let groupfields = form.querySelectorAll('.'+group);
  groupfields.forEach(function (groupfield) {
    // find the label, form there we find the bounding parent div.
    let associatedLabel = form.querySelector("label[for='" + groupfield.id + "']");
    // lets hide them all initially
    associatedLabel.parentNode.classList.add("hidden");
  });

  if(value){
    // find all groups that should be visible
    let active_groups = form.querySelectorAll('.'+group+'.'+value);
    active_groups.forEach(function (active_group) {
      // find the label, form there we find the bounding parent div.
      let associated_active_Label = form.querySelector("label[for='" + active_group.id + "']");
      associated_active_Label.parentNode.classList.remove("hidden");
    });
  }
}

function initChoiceTogglers() {
  const forms = document.querySelectorAll("form");
  
  forms.forEach(function (form) {
    
    // are there any currently active choices?
    let initial = form.querySelector("input.radio-choice:checked");
    if (initial){
      toggleChoice(form, initial.dataset.choicegroup, initial.value);
    }
    // lets catch all change events on the forms, and filter out those that are created by inputs with out radio-choice class
    form.addEventListener("change", function (event) {
      let tag = event.target;
      if (tag.tagName == "INPUT" && tag.classList.contains('radio-choice')){
        let visibleGroup = tag.value;
        let toggleGroup = tag.dataset.choicegroup;
        toggleChoice(tag.form, toggleGroup, visibleGroup);
      }
    });
  });
}

document.addEventListener("DOMContentLoaded", initChoiceTogglers);
