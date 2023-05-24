
window.addEventListener('load', (event) => {
  loadform();
});

var inputtypes = {
  'string': 'text',
  'integer': 'number',
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

function loadform(className){
  let schemafields = document.querySelectorAll('.'+className);
  schemafields.forEach(schemafield => {
    let schema = schemafield.value;
    let original = schemafield.dataset.original;
    let identifier = schemafield.id || typefield.id;
    let parent = schemafield.closest('fieldset') || schemafield.closest('form');
    schemafield.style.display = "none";
    settype(parent, schema, original, identifier);
    schemafield.addEventListener('change', (event) => {
      field = event.target;
      schema = field.value;
      original = field.dataset.original;
      parent = field.closest('fieldset') || field.closest('form');
      settype(parent, schema, original, identifier);
    });
    let form = schemafield.closest('form');
    form.addEventListener('submit', (event) => {
      console.log('handle submit');
    });
  });

}



function settype(parent, schema, original, identifier) {
  schema = JSON.parse(schema);
  if (original) {
    try {
      original = JSON.parse(original);
    } catch (e) {
      console.log('Json parsing of content failed: ', original);
      original = null;
    }
  }
  identifier = (identifier?identifier:'new');
  resetform(parent);
  parent.appendChild(renderSchema(schema, original, identifier));
}

function renderSchema(schema, original, identifier){
  if (schema['type'] == "object") {
    return renderobject(original, identifier, schema);
  } else if (schema['type'] == 'array'){
    fieldname = schema['name'] || schema['description'] || 'Content';
    return renderarray(original, identifier, fieldname, schema);
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
    if (schema['properties'][fieldname]['type'] == 'array'){
      fieldset.appendChild(renderarray(childoriginal, subpath,
        fieldname, childschema));
    } else if (schema['properties'][fieldname]['type'] == 'object'){
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
    if (schema['items']['type'] == 'array'){
      fieldset.appendChild(renderarray(
        (original && original[count]?original[count]:false),
        subpath, name, schema['items']));
    } else if (schema['items']['type'] == 'object'){
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
      if (schema['items']['type'] == 'array'){
        subpath = path + '_' + fieldset.querySelectorAll('div').length;
        fieldset.insertBefore(renderarray(false, subpath, name,
          schema['items']), morebutton);
      } else if (schema['items']['type'] == 'object'){
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
      fieldset.querySelectorAll(':scope > div, :scope > fieldset').length == schema.maxItems) {
      morebutton.disabled = true;
    }
  });
  if (schema.maxItems &&
    fieldset.querySelectorAll(':scope > div, :scope > fieldset').length == schema.maxItems) {
    morebutton.disabled = true;
  }
  return fieldset;
}

function renderfield(required, originalvalue, path, name, field) {
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
      if (originalvalue && originalvalue == fieldvalue) {
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
  input.required = required;
  if (field['pattern']) {
    input.pattern = field['pattern'];
  }
  if (!field['format'] &&
    field['type']) {
    input.type = (field['type'] in inputtypes ?
      inputtypes[field['type']]:
      field['type']);
  }
  if (field['type'] == 'number'){
    if (field['multipleOf']){
      input.step = field['multipleOf'];
    } else {
      input.step = "0.01"; // default step size is one, thats what we have Integers for.
    }
    if (field['minimum']){
      input.min = field['minimum'];
    }
    if (field['maximum']){
      input.max = field['maximum'];
    }
    if (field['exclusiveMinimum']){
      input.min = field['exclusiveMinimum']+1;
    }
    if (field['exclusiveMaximum']){
      input.max = field['exclusiveMaximum']-1;
    }
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
  if (field['examples']){
    let datalist = document.createElement('datalist');
    for (let index = 0; index < field['examples'].length; ++index) {
      let element = field['examples'][index];
      let option = document.createElement('option');
      option.value = element;
      datalist.appendChild(option);
    }
    datalist.id = input.name + 'listoptions';
    div.appendChild(datalist);
    input.list = input.name + 'listoptions';
  }

  if (originalvalue) {
    input.value = originalvalue;
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
