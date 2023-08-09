
const buttons = document.querySelectorAll(".expando-button.normalizer-list-table-row");

buttons.forEach((button) => {
  const raw_task_id = button.closest('tr').getAttribute('data-task-id');
  const task_id = button.closest('tr').getAttribute('data-task-id').replace(/-/g, "");
  const json_url = location.pathname + "/" + encodeURI(task_id);

  const getJson = (url, callback) => {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'json';
    xhr.onload = function() {
      var status = xhr.status;
      if (status === 200) {
        const error_messages = button.closest('tr').nextElementSibling.querySelectorAll('.error')
        error_messages.forEach(element => {
          element.remove()
        })

        callback(xhr.response);
      } else {
        // Create HTML elements to build a snippet containing the error message.
        let error_element = document.createElement('div');
        let error_text_element = document.createElement('p');


        error_text_element.innerText= "Retrieving yielded objects resulted in a Sever Error: Status code ";
        error_element.appendChild(error_text_element);
        error_element.classList.add("error")

        // Log the error in the console.
        console.log("Server Error: Retrieving yielded objects failed. Server response: Status code " + xhr.status + " - " + xhr.statusText);

        // Insert the HTML snippet into the expando row, which is the buttons parent TR next TR-element sibling.
        button.closest('tr').nextElementSibling.querySelector('#yielded-objects-'+raw_task_id).appendChild(error_element);
      }
    };
    xhr.send();
  };


  let element = document.createElement('p');
  element.classList.add('yielded-objects-paragraph')
  button.addEventListener("click", function() {
    // Make sure there are no yielded objecst rendered, so we don't do unnecessary GET requests.
    if (!button.closest('tr').nextElementSibling.querySelector('#yielded-objects-'+raw_task_id).querySelector('.yielded-objects-paragraph')) {
      // Retrieve JSON containing yielded objects of task.
      getJson(json_url, function(data) {
        if(data.length > 0) {
          const url = location.pathname.replace('/tasks/normalizers', '');

          // Build HTML snippet for every yielded object.
          data.forEach(object => {
            element.innerHTML = "<a href='" + url + "/objects/detail/?ooi_id=" + encodeURIComponent(object) +"'>" + object + "</a>";
          });
        } else {
          element.innerText = "Normalizer task yielded no objects.";
        }
      });

      // Insert HTML snippet into the expando row, which is the buttons parent TR next TR-element sibling.
      button.closest('tr').nextElementSibling.querySelector('#yielded-objects-'+raw_task_id).appendChild(element);
    } else {
      return
    }
  });
});
