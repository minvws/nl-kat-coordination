const EnableButton = () => {
  document.getElementById("js-disabled-for-10").disabled = false;
};

setTimeout(() => EnableButton(), 180000);
