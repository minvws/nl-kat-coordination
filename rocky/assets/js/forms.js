
window.addEventListener('load', (event) => {
  loadform();
  attachupdownbuttons();
  attachschemavalidation();
  metadataforms();
});

function attachupdownbuttons(){
  let buttons = document.querySelectorAll('button.updown');
  buttons.forEach(button => {
    button.addEventListener('click', function(event){
      event.preventDefault();
      let parent = button.closest('tr');
      let curpos = parseInt(parent.querySelector('input.sort').value);
      let table = parent.parentNode;
      if(button.classList.contains('up')){
        parent.querySelector('input.sort').value = curpos - 1;
        parent.previousElementSibling.querySelector('input.sort').value = curpos;
        table.insertBefore(parent, parent.previousElementSibling);
      } else {
        parent.querySelector('input.sort').value = curpos + 1;
        parent.nextElementSibling.querySelector('input.sort').value = curpos;
        table.insertBefore(parent, parent.nextElementSibling.nextSibling);
      }
    });
  });
}


function attachschemavalidation(){
  let schemas = document.querySelectorAll('#schema');
  schemas.forEach(schema => {
    schema.form.addEventListener('submit', function(event){
      try {
        JSON.parse(schema.value);
        schema.setCustomValidity('');
        schema.classList.add('succes');
        schema.classList.remove('error');
        return true;
      } catch(e) {
        schema.setCustomValidity('Your schema does not parse as Valid Json.');
        schema.classList.add('error');
        schema.classList.remove('succes');
        event.preventDefault();
        return false;
      }
    });
    schema.form.addEventListener('change', function(event){
      try {
        JSON.parse(schema.value);
        schema.setCustomValidity('');
        schema.classList.add('succes');
        schema.classList.remove('error');
        return true;
      } catch(e) {
        schema.setCustomValidity('Your schema does not parse as Valid Json.');
        schema.classList.add('error');
        schema.classList.remove('succes');
        return true;
      }
    });
  });
}

var inputtypes = {
  'string': 'text',
}

var formattypes = {
  'idn-email': ['input', 'email', null],
  'date-time': ['input', 'datetime-local', null],
  'hostname': ['input', 'text', '^[a-zA-Z][a-zA-Z\d-]{1,22}[a-zA-Z\d]$'],
  'idn-hostname': ['input', 'text', '^[a-zA-Z][a-zA-Z\d-]{1,22}[a-zA-Z\d]$'],
  'url': ['input', 'url', null],
  'uri': ['input', 'url', null],
  'uri-reference': ['input', 'url', null],
  'iri': ['input', 'url', null],
  'iri-reference': ['input', 'url', null],
  'ipv4': ['input', 'text', '((^|\.)((25[0-5])|(2[0-4]\d)|(1\d\d)|([1-9]?\d))){4}$'],
  'ipv6': ['input', 'text', '((^|:)([0-9a-fA-F]{0,4})){1,8}$'],
  'textarea': ['textarea']
}

function metadataforms(){
  let metadatafields = document.querySelectorAll('textarea.metadata');
  metadatafields.forEach(metadatafield => {
    let schema = document.getElementById('metadata_schema').value;
    let original = metadatafield.value;
    let article = metadatafield.dataset.article;
    schema = JSON.parse(schema);
    if (original) {
      try {
        original = JSON.parse(original);
      } catch (e) {
        console.log('Json parsing of content failed: ', original);
        original = null;
      }
    }
    let parent = metadatafield.parentNode;
    parent.insertBefore(renderSchema(schema, original, article+'_meta'),
                        metadatafield);
    metadatafield.style.display='none';
  });
}

function loadform(){
  let typefields = document.querySelectorAll('select[name], select[name="type[new]"]');
  typefields.forEach(typefield => {
    let schema = typefield[typefield.selectedIndex].dataset.schema;
    let original = typefield.dataset.original;
    let atom = typefield.dataset.id;
    let parent = typefield.closest('fieldset');
    settype(parent, schema, original, atom);
    typefield.addEventListener('change', (event) => {
      field = event.target;
      schema = field[field.selectedIndex].dataset.schema;
      original = field.dataset.original;
      parent = field.closest('fieldset');
      settype(parent, schema, original, atom);
    });
  });
}

function settype(parent, schema, original, atom) {
  schema = JSON.parse(schema);
  if (original) {
    try {
      original = JSON.parse(original);
    } catch (e) {
      console.log('Json parsing of content failed: ', original);
      original = null;
    }
  }
  atom = (atom?atom:'new');
  resetform(parent);
  parent.appendChild(renderSchema(schema, original, atom));
}

function renderSchema(schema, original, atom){
  if (schema['type'] === "object") {
    return renderobject(original, atom, schema);
  } else if (schema['type'] === 'array'){
    fieldname = schema['name'] || schema['description'] || 'Content';
    return renderarray(original, atom, fieldname, schema);
  }
}

function renderobject(original, path, schema){
  if (!schema['required']){
    schema['required'] = [];
  }
  let fieldset = document.createElement('fieldset');
  for (fieldname in schema['properties']) {
    childoriginal = (original && original[fieldname]?original[fieldname]:false);
    childschema = schema['properties'][fieldname];
    subpath = path + '_' + fieldname;
    if (schema['properties'][fieldname]['type'] === 'array'){
      fieldset.appendChild(renderarray(childoriginal, subpath,
          fieldname, childschema));
    } else if (schema['properties'][fieldname]['type'] === 'object'){
      fieldset.appendChild(renderobject(childoriginal, subpath, childschema));
    } else {
      fieldset.appendChild(renderfield(
          (schema['required'] && schema['required'].includes(fieldname)),
          childoriginal, subpath, fieldname, childschema));
    }
  }
  return fieldset;
}

function renderarray(original, path, name, schema) {
  if (!schema['required']){
    schema['required'] = [];
  }
  let fieldset = document.createElement('fieldset');
  let header = document.createElement('h4');
  let text = name.charAt(0).toUpperCase() + name.slice(1);
  if (schema.minItems && schema.maxItems) {
    text += ' (between '+schema.minItems+' and '+schema.maxItems+' items)';
  } else if(schema.minItems) {
    text += ' (at least '+schema.minItems+' items)';
  } else if(schema.minItems) {
    text += ' (at most '+schema.minItems+' items)';
  }
  let headertext = document.createTextNode(text);
  header.appendChild(headertext);
  fieldset.appendChild(header);
  let minamount = 1;
  if (original && original.length) {
    minamount = original.length;
  }
  if (schema.minItems) {
    // lets show the minimum number of input fields, if a minimum number is set, and larger than the current set.
    if (schema.minItems && schema.minItems > minamount) {
      minamount = schema.minItems;
    }
  }
  for (var count=0; count<minamount; count++) {
    subpath = path + '_' + count;
    if (schema['items']['type'] === 'array'){
      fieldset.appendChild(renderarray(
          (original && original[count]?original[count]:false),
          subpath, name, schema['items']));
    } else if (schema['items']['type'] === 'object'){
      fieldset.appendChild(renderobject(
          (original && original[count]?original[count]:false),
          subpath, schema['items']));
    } else {
      required = schema['required'] && count < (schema.minItems || 0);
      fieldset.appendChild(renderfield(required,
          (original && original[count]?original[count]:false),
          subpath, name, schema['items'], true, count));
    }
  }

  let morebutton = document.createElement('button');
  let plussign = document.createTextNode('+');
  morebutton.appendChild(plussign);
  morebutton.className = 'more';
  fieldset.appendChild(morebutton);
  morebutton.addEventListener('click', (event) => {
      event.preventDefault();
      if (!schema.maxItems ||
          fieldset.querySelectorAll(':scope > div, :scope > fieldset').length < schema.maxItems) {
        if (schema['items']['type'] === 'array'){
          subpath = path + '_' + fieldset.querySelectorAll('div').length;
          fieldset.insertBefore(renderarray(false, subpath, name,
              schema['items']), morebutton);
        } else if (schema['items']['type'] === 'object'){
          subpath = path + '_' + fieldset.querySelectorAll('fieldset').length;
          fieldset.insertBefore(renderobject(false, subpath,
              schema['items']), morebutton);
        } else {
          subpath = path + '_' + fieldset.querySelectorAll('div').length;
          fieldset.insertBefore(renderfield(
              (schema['required'] && schema['required'].includes(name)),
              false, subpath, name, schema['items']),
              morebutton);
        }
      }
      if (schema.maxItems &&
          fieldset.querySelectorAll(':scope > div, :scope > fieldset').length === schema.maxItems) {
        morebutton.disabled = true;
      }
    });
  if (schema.maxItems &&
    fieldset.querySelectorAll(':scope > div, :scope > fieldset').length === schema.maxItems) {
    morebutton.disabled = true;
  }
  return fieldset;
}

function renderfield(required, original, path, name, field) {
  let div = document.createElement('div');
  let label = document.createElement('label');
  let labeltext = document.createTextNode(name.charAt(0).toUpperCase() + name.slice(1));
  label.appendChild(labeltext);
  div.appendChild(label);

  let fieldformat = null;
  if (field['format']) {
    let format = field['format'];
    if (format in formattypes){
      fieldformat = formattypes[format];
    }
  }
  let input = null;
  if (field['enum']) {
    input = document.createElement('select');
    field['enum'].forEach(fieldvalue => {
      let value = document.createElement('option');
      value.value = fieldvalue;
      if (original && original === fieldvalue) {
        value.selected = true;
      }
      let valuetext = document.createTextNode(fieldvalue);
      value.appendChild(valuetext);
      input.appendChild(value);
    });
  } else {
    if (!fieldformat) {
      fieldformat = ['input',
                     (field['type']?field['type']:'text'),
                     null];
    }
    input = document.createElement(fieldformat[0]);
    input.type = fieldformat[1];
    if (!input.pattern && fieldformat[2]) {
      input.pattern = fieldformat[2];
    }
  }
  input.name = path;
  input.id = input.name;
  label.htmlFor = input.id;
  if (path.substring(0,3) !== 'new') {
    input.required = required;
  }
  if (field['pattern']) {
    input.pattern = field['pattern'];
  }
  if (!field['format'] &&
      field['type']) {
    input.type = (field['type'] in inputtypes ?
        inputtypes[field['type']]:
        field['type']);
  }
  if (field['markdown']) {
    div.classList.add('markdown');
  }
  if (field['description']) {
    input.placeholder = field['description'];
  }
  if (field['minLength']) {
    input.minlength = parseInt(field['minLength']);
  }
  if (field['maxLength']) {
    input.maxlength = parseInt(field['maxLength']);
  }
  if (original) {
    input.value = original;
  }
  div.appendChild(input);
  return div;
}

function resetform(wrapper) {
  wrapper.querySelectorAll('div, fieldset').forEach(field => {
    field.querySelectorAll('input, textarea, div').forEach(inputfield => {
      if (field.parentNode) {
        field.parentNode.removeChild(field);
      }
    });
  });
}
