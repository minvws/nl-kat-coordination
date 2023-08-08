
const buttons = document.querySelectorAll(".expando-button.normalizer-list-table-row");

buttons.forEach((button) => {
  const raw_task_id = button.closest('tr').getAttribute('data-task-id');
  const task_id = button.closest('tr').getAttribute('data-task-id').replace(/-/g, "");
  const json_url = window.location.href + "/" + task_id;

  const getJson = (url, callback) => {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', url, true);
    xhr.responseType = 'json';
    xhr.onload = function() {
      var status = xhr.status;
      if (status === 200) {
        callback(null, xhr.response);
      } else {
        callback(status, xhr.response);
      }
    };
    xhr.send();
  };


  const element = document.createElement('p')
  button.addEventListener("click", () => getJson(json_url, function(err, data) {
    if (err !== null) {
      alert('Somthing went wrong: ' + err);
    } else {
      if(data.length > 0) {
        data.forEach(object => {
          const url = window.location.href.replace('/tasks/normalizers', '')
          element.innerHTML = "<a href='" + url + "/objects/detail/?ooi_id=" + object +"'>" + object + "</a>"
        });
      } else {
        const element = document.createElement('p');
        element.innerText = "Normalizer task yielded no objects.";
      }
    }
  }));
  button.closest('tr').nextElementSibling.querySelector('#yielded-objects-'+raw_task_id).appendChild(element);
});
