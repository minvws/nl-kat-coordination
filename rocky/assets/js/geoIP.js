const maps = document.getElementsByClassName("geoip-map");
var mapcontainers = Array.prototype.slice.call(maps);

mapcontainers.forEach(function (mapcontainer) {
  new maplibregl.Map({
    container: mapcontainer,
    style: "/static/vendors/maps/style/bright.json", // stylesheet location
    center: [4.288788, 52.078663], // starting position [lng, lat]
    zoom: 9, // starting zoom
  });
});
