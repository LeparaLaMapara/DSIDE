// --- TopoJSON Extension to Leaflet.js ---
L.TopoJSON = L.GeoJSON.extend({
  addData: function(jsonData) {
    if (jsonData.type === "Topology") {
      for (key in jsonData.objects) {
        geojson = topojson.feature(jsonData, jsonData.objects[key]);
        L.GeoJSON.prototype.addData.call(this, geojson);
      }
    }
    else {
      L.GeoJSON.prototype.addData.call(this, jsonData);
    }
  }
});
// --- Copyright (c) 2013 Ryan Clark ---

// Global plotting variables
var selectionType = "Geographic Exploration";
var provinceColourKey = {
  'Eastern Cape':1,
  'Free State':2,
  'Gauteng':10,
  'KwaZulu-Natal':4,
  'Limpopo':6,
  'Mpumalanga':3,
  'North West':6,
  'Northern Cape':8,
  'Western Cape':9
};
var municipalColourKey = {
  'Buffalo City':	1,
  'Camdeboo':	2,
  'Blue Crane Route':	3,
  'Ikwezi':	4,
  'Makana':	5,
  'Ndlambe':	6,
  'Sundays River Valley':	7,
  'Baviaans':	8,
  'Kouga':	9,
  'Kou-Kamma':	10,
  'Mbhashe':	11,
  'Mnquma':	12,
  'Great Kei':	13,
  'Amahlathi':	14,
  'Ngqushwa':	15,
  'Nkonkobe':	16,
  'Nxuba':	17,
  'Inxuba Yethemba':	18,
  'Tsolwana':	19,
  'Inkwanca':	20,
  'Lukanji':	21,
  'Intsika Yethu':	22,
  'Emalahleni':	23,
  'Engcobo':	24,
  'Sakhisizwe':	25,
  'Elundini':	26,
  'Senqu':	27,
  'Maletswai':	28,
  'Gariep':	29,
  'Ngquza Hill':	30,
  'Port St Johns':	31,
  'Nyandeni':	32,
  'Mhlontlo':	33,
  'King Sabata Dalindyebo':	34,
  'Matatiele':	35,
  'Umzimvubu':	36,
  'Mbizana':	37,
  'Ntabankulu':	38,
  'Nelson Mandela Bay':	39,
  'Letsemeng':	40,
  'Kopanong':	41,
  'Mohokare':	42,
  'Naledi':	43,
  'Masilonyana':	44,
  'Tokologo':	45,
  'Tswelopele':	46,
  'Matjhabeng':	47,
  'Nala':	48,
  'Setsoto':	49,
  'Dihlabeng':	50,
  'Nketoana':	51,
  'Maluti a Phofung':	52,
  'Phumelela':	53,
  'Mantsopa':	54,
  'Moqhaka':	55,
  'Ngwathe':	56,
  'Metsimaholo':	57,
  'Mafube':	58,
  'Mangaung':	59,
  'Ekurhuleni':	60,
  'Emfuleni':	61,
  'Midvaal':	62,
  'Lesedi':	63,
  'Mogale City':	64,
  'Randfontein':	65,
  'Westonaria':	66,
  'Merafong City':	67,
  'City of Johannesburg':	68,
  'City of Tshwane':	69,
  'eThekwini':	70,
  'Vulamehlo':	71,
  'Umdoni':	72,
  'Umzumbe':	73,
  'uMuziwabantu':	74,
  'Ezingoleni':	75,
  'Hibiscus Coast':	76,
  'uMshwathi':	77,
  'uMngeni':	78,
  'Mpofana':	79,
  'Impendle':	80,
  'The Msunduzi':	81,
  'Mkhambathini':	82,
  'Richmond':	83,
  'Emnambithi/Ladysmith':	84,
  'Indaka':	85,
  'Umtshezi':	86,
  'Okhahlamba':	87,
  'Imbabazane':	88,
  'Endumeni':	89,
  'Nqutu':	90,
  'Msinga':	91,
  'Umvoti':	92,
  'Newcastle':	93,
  'Emadlangeni':	94,
  'Dannhauser':	95,
  'eDumbe':	96,
  'uPhongolo':	97,
  'Abaqulusi':	98,
  'Nongoma':	99,
  'Ulundi':	100,
  'Umhlabuyalingana':	101,
  'Jozini':	102,
  'The Big 5 False Bay':	103,
  'Hlabisa':	104,
  'Mtubatuba':	105,
  'Mfolozi':	106,
  'uMhlathuze':	107,
  'Ntambanana':	108,
  'uMlalazi':	109,
  'Mthonjaneni':	110,
  'Nkandla':	111,
  'Mandeni':	112,
  'KwaDukuza':	113,
  'Ndwedwe':	114,
  'Maphumulo':	115,
  'Ingwe':	116,
  'Kwa Sani':	117,
  'Greater Kokstad':	118,
  'Ubuhlebezwe':	119,
  'Umzimkhulu':	120,
  'Greater Giyani':	121,
  'Greater Letaba':	122,
  'Greater Tzaneen':	123,
  'Ba-Phalaborwa':	124,
  'Maruleng':	125,
  'Musina':	126,
  'Mutale':	127,
  'Thulamela':	128,
  'Makhado':	129,
  'Blouberg':	130,
  'Aganang':	131,
  'Molemole':	132,
  'Polokwane':	133,
  'Lepele-Nkumpi':	134,
  'Thabazimbi':	135,
  'Lephalale':	136,
  'Mookgopong':	137,
  'Modimolle':	138,
  'Bela-Bela':	139,
  'Mogalakwena':	140,
  'Ephraim Mogale':	141,
  'Elias Motsoaledi':	142,
  'Makhuduthamaga':	143,
  'Fetakgomo':	144,
  'Greater Tubatse':	145,
  'Albert Luthuli':	146,
  'Msukaligwa':	147,
  'Mkhondo':	148,
  'Pixley Ka Seme':	149,
  'Lekwa':	150,
  'Dipaleseng':	151,
  'Govan Mbeki':	152,
  'Victor Khanye':	153,
  'Emalahleni':	154,
  'Steve Tshwete':	155,
  'Emakhazeni':	156,
  'Thembisile':	157,
  'Dr JS Moroka':	158,
  'Thaba Chweu':	159,
  'Mbombela':	160,
  'Umjindi':	161,
  'Nkomazi':	162,
  'Bushbuckridge':	163,
  'Moretele':	164,
  'Local Municipality of Madibeng':	165,
  'Rustenburg':	166,
  'Kgetlengrivier':	167,
  'Moses Kotane':	168,
  'Ratlou':	169,
  'Tswaing':	170,
  'Mafikeng':	171,
  'Ditsobotla':	172,
  'Ramotshere Moiloa':	173,
  'Naledi':	174,
  'Mamusa':	175,
  'Greater Taung':	176,
  'Lekwa-Teemane':	177,
  'Kagisano/Molopo':	178,
  'Ventersdorp':	179,
  'Tlokwe City Council':	180,
  'City of Matlosana':	181,
  'Maquassi Hills':	182,
  'Richtersveld':	183,
  'Nama Khoi':	184,
  'Kamiesberg':	185,
  'Hantam':	186,
  'Karoo Hoogland':	187,
  'Khï¿½i-Ma':	188,
  'Ubuntu':	189,
  'Umsombomvu':	190,
  'Emthanjeni':	191,
  'Kareeberg':	192,
  'Renosterberg':	193,
  'Thembelihle':	194,
  'Siyathemba':	195,
  'Siyancuma':	196,
  'Mier':	197,
  'Kai !Garib':	198,
  '//Khara Hais':	199,
  '!Kheis':	200,
  'Tsantsabane':	201,
  'Kgatelopele':	202,
  'Sol Plaatjie':	203,
  'Dikgatlong':	204,
  'Magareng':	205,
  'Phokwane':	206,
  'Joe Morolong':	207,
  'Ga-Segonyana':	208,
  'Gamagara':	209,
  'City of Cape Town':	210,
  'Matzikama':	211,
  'Cederberg':	212,
  'Bergrivier':	213,
  'Saldanha Bay':	214,
  'Swartland':	215,
  'Witzenberg':	216,
  'Drakenstein':	217,
  'Stellenbosch':	218,
  'Breede Valley':	219,
  'Langeberg':	220,
  'Theewaterskloof':	221,
  'Overstrand':	222,
  'Cape Agulhas':	223,
  'Swellendam':	224,
  'Kannaland':	225,
  'Hessequa':	226,
  'Mossel Bay':	227,
  'George':	228,
  'Oudtshoorn':	229,
  'Bitou':	230,
  'Knysna':	231,
  'Laingsburg':	232,
  'Prince Albert':	233,
  'Beaufort West':	234,
};

// Slider layer functionality
var globalOpacity = 0.1;
$("#choroSlider").on("slide",function(slideEvent){
  globalOpacity = slideEvent.value;
});
// Helper functions
function getMinMax(array) {
  var min = Infinity, max = -Infinity, item;
  for (item in array){
    if (array[item] < min) min = array[item];
    if (array[item] > max) max = array[item];
  }
  return[min,max];
};

function createColourScale(colourArray){
  // Chroma.js scale
  var domain = getMinMax(colourArray);
  var colorScale = chroma
  .scale(['#3d51ff', '#ffffff', '#fb4a4a'], [0, .5, 1])
  // .scale(['#ffffff', '#f70a0a'], [0, 1])
  .domain([domain[0],domain[1]]);

  return colorScale;
}

// Mapbox background Layer
var mabboxAccessToken = 'pk.eyJ1IjoiZ2VycmFuZGoiLCJhIjoiY2lqYjc3amw3MDAzYXc5a3FkZzRlamxzciJ9.rc_DQCZVVVKBuhvBl0Hibg';

var map = L.map('chloroMap').setView([-29.748627, 25.277189], 5);

L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=' + mabboxAccessToken, {
    id: 'mapbox.pencil',
    attribution:'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
      '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
      'Imagery &copy <a href="http://mapbox.com">Mapbox</a>',
  }).addTo(map);

var topoLayer = new L.TopoJSON();

function CreateProvinceLayer (){
  var topoLayer = new L.TopoJSON();
  $.getJSON('data/provinces.topojson')
    .done(addTopoData);
    function addTopoData(topoData){
      topoLayer.addData(topoData);
      topoLayer.addTo(map);
      topoLayer.eachLayer(handleProvinceLayer);
    }
}//CreateProvinceLAyer


CreateProvinceLayer();

function CreateMunicipalLayer (){
  var topoLayer = new L.TopoJSON();
  $.getJSON('data/municipalities.topojson')
    .done(addTopoData);
    function addTopoData(topoData){
      topoLayer.addData(topoData);
      topoLayer.addTo(map);
      topoLayer.eachLayer(handleMunicipalLayer);
    }
}//CreateMunicipalLayer

function clearMap (){
  var topoLayer = new L.TopoJSON();
  map.eachLayer(function(layer){
      map.removeLayer(layer);
    })

    L.tileLayer('https://api.tiles.mapbox.com/v4/{id}/{z}/{x}/{y}.png?access_token=' + mabboxAccessToken, {
        id: 'mapbox.pencil',
        attribution:'Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors, ' +
          '<a href="http://creativecommons.org/licenses/by-sa/2.0/">CC-BY-SA</a>, ' +
          'Imagery � <a href="http://mapbox.com">Mapbox</a>',
    }).addTo(map);
    legend.reset();
  } //Clear Map

function handleProvinceLayer(layer){
    var colorScale = createColourScale(provinceColourKey);
    if (provinceColourKey[layer.feature.properties.PROVINCE] == 0) {
      var fillColor = '';
    }else {
      var fillColor = colorScale(provinceColourKey[layer.feature.properties.PROVINCE]).hex();
    }
    layer.setStyle({
      fillColor: fillColor,
      fillOpacity: globalOpacity,
      color: 'rgb(50, 49, 50)',
      weight:1.5,
      dashArray:'0',
      opacity: 0.7
    });

    layer.on({
      mouseover: enterLayer,
      mouseout: leaveLayer,
      click: zoomToFeature
    });
}//handleProvinceLayer

function handleMunicipalLayer(layer){
    var colorScale = createColourScale(municipalColourKey);
    var fillColor = colorScale(municipalColourKey[layer.feature.properties.MUNICNAME]).hex();
    layer.setStyle({
      fillColor: fillColor,
      fillOpacity: globalOpacity,
      color: 'rgb(50, 49, 50)',
      weight:1.5,
      dashArray:'0',
      opacity: 0.7
    });

    layer.on({
      mouseover: enterLayer,
      mouseout: leaveLayer,
      click: zoomToFeature
    });
}//handleLayer

// --- click functionality ---
function zoomToFeature(e){
  map.fitBounds(e.target.getBounds());
  if (typeof provinceColourKey[e.target.feature.properties.PROVINCE] === 'undefined'){
    Websocket.emit('Municipality_selected', e.target.feature.properties.MUNICNAME);
  }else {
    Websocket.emit('Province_selected', e.target.feature.properties.PROVINCE);
  }
}
// -------

// ----Interactive tooltip: Leaflet Control-----
var info = L.control();
info.onAdd = function(map){
  this._div = L.DomUtil.create('div','info');
  info.update();
  return this._div;
};
info.update = function (province,municipality) {
  var infoString = "";
  if (typeof provinceColourKey[province]  === "undefined"){
    if (municipalColourKey[municipality] == undefined) {
      infoString = "N/A"
    }else {
      infoString = municipalColourKey[municipality].percentify();
    }
  } else {
    infoString = provinceColourKey[province].formatRands();
    municipality = "N/A";
  }
  this._div.innerHTML = '<h4> ' + selectionType + ' </h4>' + (province ? '<b> Province: </b>' + province + ' </br> </br> <b> Municipality: </b>' + municipality  + '</br> </br> <b> Proportion: </b> <h4>' + infoString + '</h4>':'Hover over a Province');
};
info.addTo(map);
// --------------

// ----Value Legend------
  var legend = L.control({position: 'bottomright'});
  legend.onAdd = function (map){
    this._div = L.DomUtil.create('div', 'info legend');
    grades = [];
    for (var i = 0; i < grades.length; i++) {
      this._div.innerHTML +=
      '<i style="background:' + colorScale(grades[i]).hex() + '"></i> ' + grades[i] + (grades[i + 1]? '&ndash;' + grades[i + 1] + '<br>': '+');
    }
    return this._div;
  };
  legend.update = function(updateType, colorScale){
    this._div.innerHTML = "";
    var grades = [], range = [], numLedgendKeys = 6;
    if (updateType == 'Provincial'){
      range = getMinMax(provinceColourKey);
    }
    if (updateType == 'Municipal'){
      range = getMinMax(municipalColourKey);
    }
    var base = range[0];
    var increment = (range[1]-range[0])/numLedgendKeys;
    for (var i = 0; i < numLedgendKeys; i++){
      grades.push(base);
      base += increment;
    }
    if (updateType == 'Provincial') {
      for (var i = 0; i < grades.length; i++) {
        this._div.innerHTML +=
          '<i style="background:' + colorScale(grades[i]).hex() + '"></i> ' + grades[i].formatRands() + (grades[i + 1]? ' &ndash; ' + grades[i + 1].formatRands() + '<br>': '+');
      }
    }//if Provincial
    if (updateType == 'Municipal') {
      for (var i = 0; i < grades.length; i++) {
        this._div.innerHTML +=
          '<i style="background:' + colorScale(grades[i]).hex() + '"></i> ' + grades[i].percentify() + (grades[i + 1]? ' &ndash; ' + grades[i + 1].percentify() + ' <br>': '');
      }
    }

  };
  legend.reset = function(){
    this._div.innerHTML = "";
  }
  legend.addTo(map);
// ----------------------

// --- Map hover functionality ---
function enterLayer(){
  var MunicName = this.feature.properties.MUNICNAME;
  var AreaName = this.feature.properties.PROVINCE;
  this.bringToFront();
  this.setStyle({
    weight:3,
    opacity:1,
    dashArray:'0',
    color: 'rgb(255, 255, 255)',
    fillOpacity:0.5
  });
  info.update(AreaName, MunicName);
}

function leaveLayer(){
  this.setStyle({
    fillOpacity: globalOpacity,
    color: 'rgb(50, 49, 50)',
    weight:1.5,
    dashArray:'0',
    opacity: 0.7
  });
  info.update();
}
