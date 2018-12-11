// Initilise Websock
var Websocket = io();
// Receivice SQL Data Push
Websocket.on('SearchResult', function(data){
  if (data[0] == 'Province_selected'){
    genericDataArrival('provincial');
    clearPartitionMap();
    createPartitionMap(data[1]);
  }

  if (data[0] == 'Expenditure_All'){
    genericDataArrival('provincial expenditure');
    var extractOptions = ['Province', 'Total','ActualPayments',''];
    extractColorKeys(data[1], extractOptions);
    var colorScale = createColourScale(provinceColourKey);
    CreateProvinceLayer ();//Method in chloromap.js
    legend.update('Provincial', colorScale);
    selectionType = "Actual Expenditure"
    animateLoad('Treasury');
  }

  if (data[0] == 'Budget_All') {
    genericDataArrival('provincial budget');
    var extractOptions = ['Province', 'Total','FinalAppropriation',''];
    extractColorKeys(data[1], extractOptions);
    var colorScale = createColourScale(provinceColourKey);
    CreateProvinceLayer ();//Method in chloromap.js
    legend.update('Provincial', colorScale);
    selectionType = "Budget Allocation";
    animateLoad('Treasury');
  }
});

// ---===Total data retrievals===---
Websocket.on('TotalTreasury',function(receivedData){
  genericDataArrival('total budget');
  TotalTreasuryData = receivedData;
  generateSupportingTreasuryGraphs(TotalTreasuryData,false);
});

Websocket.on('Municipal_Housing', function(receivedData){
  genericDataArrival('total housing type');
  TotalHousingTypeData = receivedData[0];
  if (receivedData[1] == 'Informal') {
    var extractOptions = ['Municipality', 'HousingType', '', [7,8]];
    extractColorKeys(TotalHousingTypeData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Living in Informal Housing";
    legend.update('Municipal', colorScale);
    animateLoad('Housing');
  }
  if (receivedData[1] == 'Traditional') {
    var extractOptions = ['Municipality', 'HousingType', '', [2,15]];
    extractColorKeys(TotalHousingTypeData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Living in Traditional Housing";
    legend.update('Municipal', colorScale);
    animateLoad('Housing');
  }
});

Websocket.on('Municipal_Services', function(receivedData){
  genericDataArrival('total housing services');
  TotalHousingServicesData = receivedData[0];
  if (receivedData[1] == 'Water') {
    var extractOptions = ['Municipality', 'HousingServices', 'WaterKey', [7,8,9]];
    extractColorKeys(TotalHousingServicesData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "No Water Access";
    legend.update('Municipal', colorScale);
    animateLoad('Services');
  }
  if (receivedData[1] == 'Electricity') {
    var extractOptions = ['Municipality', 'HousingServices', 'EnergyKey', [3,4,5,6,7,8]];
    extractColorKeys(TotalHousingServicesData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "No Electricity Access";
    legend.update('Municipal', colorScale);
    animateLoad('Services');
  }
  if (receivedData[1] == 'Telephone') {
    var extractOptions = ['Municipality', 'HousingServices', 'TelephoneKey', [4,6,7,8,10,11]];
    extractColorKeys(TotalHousingServicesData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "No Telephone Access";
    legend.update('Municipal', colorScale);
    animateLoad('Services');
  }
  if (receivedData[1] == 'Toilet') {
    var extractOptions = ['Municipality', 'HousingServices', 'ToiletKey', [4,5,6,7,8]];
    extractColorKeys(TotalHousingServicesData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "No Ablution Facilities";
    legend.update('Municipal', colorScale);
    animateLoad('Services');
  }
});

Websocket.on('Municipal_Mortality', function(receivedData){
  genericDataArrival('total mortality');
  TotalMortalityData = receivedData[0];
  if (receivedData[1] == 'Infant') {
    var extractOptions = ['Municipality', 'Mortality', '', [1,2]];
    extractColorKeys(TotalMortalityData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Infants without Parents";
    legend.update('Municipal', colorScale);
    animateLoad('Mortality');
  }
  if (receivedData[1] == 'Youth') {
    var extractOptions = ['Municipality', 'Mortality', '', [3,4]];
    extractColorKeys(TotalMortalityData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Youth without Parents";
    legend.update('Municipal', colorScale);
    animateLoad('Mortality');
  }
  if (receivedData[1] == 'Young Adult') {
    var extractOptions = ['Municipality', 'Mortality', '', [5,6,7,8]];
    extractColorKeys(TotalMortalityData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Young Adults without Parents";
    legend.update('Municipal', colorScale);
    animateLoad('Mortality');
  }
});

Websocket.on('Municipal_Education', function(receivedData){
  genericDataArrival('total Education');
  TotalEducationData = receivedData[0];
  if (receivedData[1] == 'None') {
    var extractOptions = ['Municipality', 'Education', '', [1]];
    extractColorKeys(TotalEducationData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Individuals with No Formal Schooling";
    legend.update('Municipal', colorScale);
    animateLoad('Education');
  }
  if (receivedData[1] == 'Grade 7') {
    var extractOptions = ['Municipality', 'Education', '', [9]];
    extractColorKeys(TotalEducationData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Highest qualification: Grade 7";
    legend.update('Municipal', colorScale);
    animateLoad('Education');
  }
  if (receivedData[1] == 'Matric') {
    var extractOptions = ['Municipality', 'Education', '', [16,17,18]];
    extractColorKeys(TotalEducationData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Highest qualification: Matric";
    legend.update('Municipal', colorScale);
    animateLoad('Education');
  }
  if (receivedData[1] == 'University') {
    var extractOptions = ['Municipality', 'Education', '', [19,20,21,22,23,24]];
    extractColorKeys(TotalEducationData, extractOptions);
    var colorScale = createColourScale(municipalColourKey);
    CreateMunicipalLayer();
    selectionType = "Highest qualification: Tertiary";
    legend.update('Municipal', colorScale);
    animateLoad('Education');
  }
});
