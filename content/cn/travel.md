---
title: "On the Road"
date: 2019-08-30T20:33:03+08:00
type: "page"
draft: false
---

<!-- HTML -->
<div id="travelmap"></div>
<a href='https://openflights.org/user/jowaywang' target='_blank'><img src='https://openflights.org/banner/jowaywang.png' width="100%"></a>

<!-- Styles -->
<style>
#travelmap {
  width: 100%;
  height: 500px;
}
.amcharts-chart-div a {
  display: none !important;
}
</style>

<!-- Resources -->
<script src="https://www.amcharts.com/lib/3/ammap.js"></script>
<script src="https://www.amcharts.com/lib/3/maps/js/worldLow.js"></script>
<script src="https://www.amcharts.com/lib/3/maps/js/worldHigh.js"></script>
<script src="https://www.amcharts.com/lib/3/themes/light.js"></script>

<!-- Chart code -->
<script>
/**
 * Define SVG path for target icon
 */
var targetSVG = "M9,0C4.029,0,0,4.029,0,9s4.029,9,9,9s9-4.029,9-9S13.971,0,9,0z M9,15.93 c-3.83,0-6.93-3.1-6.93-6.93S5.17,2.07,9,2.07s6.93,3.1,6.93,6.93S12.83,15.93,9,15.93 M12.5,9c0,1.933-1.567,3.5-3.5,3.5S5.5,10.933,5.5,9S7.067,5.5,9,5.5 S12.5,7.067,12.5,9z";

/**
 * Create the cities
 * https://www.latlong.net
 */
const cities = [
  {
    "title": "Takamatsu",
    "latitude": 34.2728006,
    "longitude": 133.9080959,
  },
  {
    "title": "Shiraz",
    "latitude": 32.8133972,
    "longitude": 52.9099841,
  },
  {
    "title": "Isfahan",
    "latitude": 34.6930788,
    "longitude": 52.3530197,
  },
  {
    "title": "Isfahan",
    "latitude": 34.6930788,
    "longitude": 52.3530197,
  },
  {
    "title": "Kashan",
    "latitude": 34.0650114,
    "longitude": 52.2084415,
  },
  {
    "title": "Tehran",
    "latitude": 33.9218242,
    "longitude": 52.9847321,
  },
  {
    "title": "Kamakura",
    "latitude": 35.303188,
    "longitude": 139.565704,
  },
  {
    "title": "Tokyo",
    "latitude": 35.689487,
    "longitude": 139.691711,
  },
  {
    "title": "Kyoto",
    "latitude": 35.011635,
    "longitude": 135.768036,
  },
  {
    "title": "Osaka",
    "latitude": 34.693737,
    "longitude": 135.502167,
  },
  {
    "title": "Pyongyang",
    "latitude": 39.0292506,
    "longitude": 125.6720718,
  },
  {
    "title": "Kaesŏng",
    "latitude": 37.9260042,
    "longitude": 126.6459934,
  },
  {
    "title": "Jiuzhai Valley",
    "latitude": 33.2600421,
    "longitude": 103.9164107,
  },
  {
    "title": "Chengdu",
    "latitude": 30.6584534,
    "longitude": 103.9354618,
  },
  {
    "title": "Praha",
    "latitude": 50.0595854,
    "longitude": 14.3255418,
  },
  {
    "title": "Wien",
    "latitude": 48.2048141,
    "longitude": 16.354304,
  },
  {
    "title": "Berlin",
    "latitude": 52.5200,
    "longitude": 13.404954,
  },
  {
    "title": "Dusseldorf",
    "latitude": 51.2277411,
    "longitude": 6.7734556,
  },
  {
    "title": "Duisburg",
    "latitude": 51.4344079,
    "longitude": 6.762329299999999,
  },
  {
    "title": "Dortmund",
    "latitude": 51.5135872,
    "longitude": 7.465298100000001,
  },
  {
    "title": "Cologne",
    "latitude": 50.937531,
    "longitude": 6.9602786,
  },
  {
    "title": "Aachen",
    "latitude": 50.7753455,
    "longitude": 6.0838868,
  },
  {
    "title": "Amsterdam",
    "latitude": 52.3702157,
    "longitude": 4.8951679,
  },
  {
    "title": "Madrid",
    "latitude": 40.4167754,
    "longitude": -3.7037902,
  },
  {
    "title": "Segovia",
    "latitude": 40.9429032,
    "longitude": -4.10880,
  },
  {
    "title": "Toledo",
    "latitude": 39.8623132,
    "longitude": -4.0117751,
  },
  {
    "title": "Granada",
    "latitude": 37.1773363,
    "longitude": -3.5985571,
  },
  {
    "title": "Sevilla",
    "latitude": 37.3890924,
    "longitude": -5.9844589,
  },
  {
    "title": "Lisbon",
    "latitude": 38.7222524,
    "longitude": -9.1393366,
  },
  {
    "title": "Paris",
    "latitude": 48.856614,
    "longitude": 2.3522219,
  },
  {
    "title": "Rome",
    "latitude": 41.9027835,
    "longitude": 12.4963655,
  },
  {
    "title": "Florence",
    "latitude": 43.7695604,
    "longitude": 11.2558136,
  },
  {
    "title": "Barcelona",
    "latitude": 41.3850639,
    "longitude": 2.1734035,
  },
  {
    "title": "Moscow",
    "latitude": 55.755826,
    "longitude": 37.6172999,
  },
  {
    "title": "Beijing",
    "latitude": 39.90419989999999,
    "longitude": 116.4073963,
  },
  {
    "title": "Canton",
    "latitude": 22.848513,
    "longitude": 111.2428405,
  },
  {
    "title": "Wuhan",
    "latitude": 30.592849,
    "longitude": 114.305539,
  },
  {
    "title": "Yangzhou",
    "latitude": 32.4173775,
    "longitude": 119.3493286,
  },
  {
    "title": "Shaoxing",
    "latitude": 29.9929308,
    "longitude": 120.5176462,
  },
  {
    "title": "Shanghai",
    "latitude": 31.2240453,
    "longitude": 121.1965663,
  },
  {
    "title": "Okinawa",
    "latitude": 25.9483597,
    "longitude": 124.8891018,
  },
  {
    "title": "Hong Kong",
    "latitude": 22.3526738,
    "longitude": 113.9876148,
  },
];
for (var i = 0; i < cities.length; ++i){
  cities[i]["zoomLevel"] = 5;
  cities[i]["scale"] = 0.5;
  cities[i]["svgPath"] = targetSVG;
  cities[i]["scale"] = 0.5;
}

/**
 * Create the map
 */
var map = AmCharts.makeChart( "travelmap", {
  "type": "map",
  "projection": "mercator",
  "theme": "light",
  "imagesSettings": {
    "rollOverColor": "#089282",
    "rollOverScale": 3,
    "selectedScale": 3,
    "selectedColor": "#089282",
    "color": "#13564e",
  },
  "areasSettings": {
    autoZoom: true,
    "unlistedAreasColor": "#15A892",
    "outlineThickness": 1,
    "color": "#B4B4B7",
    "colorSolid": "#84ADE9",
    "selectedColor": "#84ADE9",
    "outlineColor": "#666666",
    "rollOverColor": "#9EC2F7",
    "rollOverOutlineColor": "#000000"
  },
  "dataProvider": {
    "map": "worldHigh",
    getAreasFromMap: true,
    "images": cities,
    areas: [{
                "id": "AT",
                "showAsSelected": true
            },
            {
                "id": "CZ",
                "showAsSelected": true
            },
            {
                "id": "FR",
                "showAsSelected": true
            },
            {
                "id": "DE",
                "showAsSelected": true
            },
            {
                "id": "IT",
                "showAsSelected": true
            },
            {
                "id": "NL",
                "showAsSelected": true
            },
            {
                "id": "PT",
                "showAsSelected": true
            },
            {
                "id": "RU",
                "showAsSelected": true
            },
            {
                "id": "ES",
                "showAsSelected": true
            },
            {
                "id": "VA",
                "showAsSelected": true
            },
            {
                "id": "CN",
                "showAsSelected": true
            },
            {
                "id": "JP",
                "showAsSelected": true
            },
            {
                "id": "IR",
                "showAsSelected": true
            }
        ],
  },
  "export": {
    "enabled": false,
  },
} );

</script>
