//crossfilter-DC.js Graphs
var paymentsPerYear  = {}
var paymentsPerProv  = {}
var dataCount = {}
var differencePerYear  = {}
var scatterPlot  = {}

// Helper functions
String.prototype.capataliseFirstLetter = function(){
  return this.charAt(0).toUpperCase() + this.slice(1);
}
function clipString(inputString){
  if (inputString != undefined) {
    if (inputString.length > 100){
      return inputString.toLowerCase().capataliseFirstLetter().substr(0,100);
    }
    return inputString.toLowerCase().capataliseFirstLetter();
  }
}

// Global variables
var departmentKey = {
  1:	'Agriculture',
  2:	'AGRICULTURE (NEW)',
  3:	'AGRICULTURE AND ENVIRONMENT AFFAIRS',
  4:	'Agriculture And Environmental Affairs',
  5:	'Agriculture And Land Administration',
  6:	'AGRICULTURE AND LAND ADMINISTRATION (NEW DEPT)',
  7:	'Agriculture And Land Affairs',
  8:	'AGRICULTURE AND LAND REFORM (NEW DEPT)',
  9:	'AGRICULTURE, CONSERVATION AND ENVIRONMENT',
  10:	'AGRICULTURE, CONSERVATION AND ENVIRONMENT AND LAND AFFAIRS',
  11:	'Agriculture, Conservation, Environment And Land Affairs',
  12:	'AGRICULTURE, CONSERVATION, ENVIRONMENT AND TOURISM (NEW DEPT)',
  13:	'Agriculture, Conservations And Environment',
  14:	'Agriculture, Land Reform, Environment And Conservation',
  15:	'Arts And Culture',
  16:	'ARTS, CULTURE AND TOURISM (NEW DEPT)',
  17:	'Community Safety',
  18:	'Community Safety And Liaison',
  19:	'Contingency Reserve',
  20:	'Cultural Affairs And Sport',
  21:	'CULTURAL AFFAIRS AND SPORT (NEW)',
  22:	'Culture, Sport And Recreation',
  23:	'DEPARTMENT OF THE PREMIER',
  24:	'Development Planning And Local Government',
  25:	'Developmental Local Government And Housing',
  26:	'Economic Affairs And Tourism',
  27:	'ECONOMIC AFFAIRS, AGRICULTURE AND TOURISM',
  28:	'Economic Affairs, Environment And Tourism',
  29:	'ECONOMIC DEVELOPMENT (NEW)',
  30:	'Economic Development And Planning',
  31:	'ECONOMIC DEVELOPMENT AND PLANNING (NEW DEPT)',
  32:	'Economic Development And Tourism',
  33:	'ECONOMIC DEVELOPMENT, ENVIRONMENT AND TOURISM ( NEW DEPT)',
  34:	'Economic Development, Environment And Tourism (New Dept)',
  35:	'Education',
  36:	'EDUCATION AND CULTURE',
  37:	'Environmental Affairs And Development Planning',
  38:	'ENVIRONMENTAL AFFAIRS AND DEVELOPMENT PLANNING (NEW)',
  39:	'ENVIRONMENTAL AFFAIRS AND TOURISM (NEW DEPT)',
  40:	'ENVIRONMENTAL AND CULTURAL AFFAIRS AND SPORT',
  41:	'Finance',
  42:	'FINANCE (NEW DEPT)',
  43:	'Finance And Economic Affairs',
  44:	'Finance And Economic Development',
  45:	'FINANCE AND ECONOMIC DEVELOPMENT (NEW DEPT)',
  46:	'FINANCE AND EXPENDITURE',
  47:	'FREE STATE LEGISLATURE',
  48:	'GAUTENG LEGISLATURE',
  49:	'GAUTENG SHARED SERVICE CENTRE',
  50:	'Gauteng Shared Services Centre',
  51:	'Health',
  52:	'HEALTH AND WELFARE',
  53:	'Housing',
  54:	'HOUSING AND LAND ADMINISTRATION',
  55:	'Housing And Local Government',
  56:	'HOUSING, LOCAL GOVERNMENT AND TRADITIONAL AFFAIRS',
  57:	'Housing, Local Government And Traditional Leaders',
  58:	'Legislature',
  59:	'LIMPOPO LEGISLATURE',
  60:	'Local Government',
  61:	'Local Government And Housing',
  62:	'LOCAL GOVERNMENT AND HOUSING (NEW DEPT)',
  63:	'LOCAL GOVERNMENT, TRAFFIC CONTROL AND TRAFFIC SAFETY',
  64:	'MPUMALANGA PROVINCIAL LEGISLATURE',
  65:	'Office Of The Premier',
  66:	'Parliament',
  67:	'Premier',
  68:	'PREMIER (NEW DEPT)',
  69:	'PREMIER, DIRECTOR-GENERAL AND CORPORATE SERVICES',
  70:	'PROMOTING THE RDP',
  71:	"PROMOTING THE RDP (PART OF PREMIER'S ANNUAL REPORT)",
  72:	'Provincial Administration',
  73:	'Provincial Legislature',
  74:	'Provincial Parliament',
  75:	'PROVINCIAL SAFETY AND LIAISON',
  76:	'Provincial Treasury',
  77:	'Public Safety, Security And Liaison',
  78:	'Public Transport, Roads And Works',
  79:	'Public Works',
  80:	'PUBLIC WORKS (NEW DEPT)',
  81:	'PUBLIC WORKS, ROAD AND TRANSPORT',
  82:	'Public Works, Roads And Transport',
  83:	'RDP',
  84:	'Roads And Public Works',
  85:	'Roads And Transport',
  86:	'ROADS AND TRANSPORT (NEW DEPT)',
  87:	'ROADS, AND PUBLIC WORKS',
  88:	'Royal Household',
  89:	'Safety And Liaison',
  90:	'Safety And Security',
  91:	'SAFETY AND SECURITY CIVILIAN SECRETARIAT',
  92:	'Safety, Security And Liaison',
  93:	'Social Development',
  94:	'Social Services And Population Development',
  95:	'Social Services And Poverty Alleviation',
  96:	'SOCIAL SERVICES, ARTS, CULTURE AND SPORT',
  97:	'SOCIAL SERVICES, POPULATION AND DEVELOPMENT',
  98:	'SOCIAL WELFARE AND POPULATION DEVELOPMENT',
  99:	'Sport And Recreation',
  100:	'SPORT AND RECREATION (NEW DEPT)',
  101:	'Sport, Arts And Culture',
  102:	'SPORT, ARTS AND CULTURE (NEW DEPT)',
  103:	'Sport, Arts, Culture, Science And Technology',
  104:	'Sport, Recreation, Arts And Culture',
  105:	'Sports, Arts And Culture',
  106:	'SPORTS, ARTS, CULTURE, SCIENCE AND TECHNOLOGY',
  107:	'SPORTS, RECREATION, ARTS AND CULTURE',
  108:	'THE ROYAL HOUSEHOLD',
  109:	'TOURISM, ENVIRONMENTAL AND ECONOMIC AFFAIRS',
  110:	'Tourism, Environmental And Economical Affairs',
  111:	'TRADITIONAL AND CORPORATE AFFAIRS',
  112:	'Traditional And Local Government Affairs',
  113:	'Transport',
  114:	'Transport And Public Works',
  115:	'TRANSPORT AND PUBLIC WORKS (NEW)',
  116:	'TRANSPORT AND ROADS (NEW DEPT)',
  117:	'Transport, Roads And Public Works',
  118:	'Welfare',
  119:	'Works',
  120:	'Land Affairs',
  121:	'National Treasury',
  122:	'Provincial and Local Government',
  123:	'Sport and Recreation South Africa',
  124:	'AGRICULTURE AND LAND REFORM',
  125:	'ARTS, CULTURE AND TOURISM',
  126:	'CONTINGENCY RESERVE (FINANCE)',
  127:	'ECONOMIC AFFAIRS',
  128:	'ECONOMIC DEVELOPMENT',
  129:	'ECONOMIC DEVELOPMENT, ENVIRONMENT AND TOURISM',
  130:	'FREE STATE PROVINCIAL TREASURY',
  131:	'GAUTENG PROVINCIAL LEGISLATURE',
  132:	'LIMPOPO PROVINCIAL LEGISLATURE',
  133:	'LOCAL GOVERNMENT AND TRADITIONAL AFFAIRS',
  134:	'SOCIAL SERVICES',
  135:	'TOURISM, ENVIRONMENT AND CONSERVATION',
  136:	'TRANSPORT, ROADS AND COMMUNITY SAFETY',
  137:	'TRANSPORT, ROADS AND WORKS',

};

// Creation of Treasury crossfilter graphs
function generateSupportingTreasuryGraphs(data,redraw){

    //Function called with invalid data
    if (data.length == 0) {
      return;
    }

    //If crossfilter dimensions/groups do not exist define them
    var ndx = crossfilter(data);

      //formating data (tells dc that data is a number)
      data.forEach(function(d){
          d.FinalAppropriation = +d.FinalAppropriation;
          d.ActualPayments = +d.ActualPayments;
      });
      var ndx = crossfilter(data);

  //Dimensions, ie x-values
      var yearDim = ndx.dimension(function(d) {return [d.YearKey];});
      var provDim = ndx.dimension(function(d) {return keyToProvince[d.ProvinceKey];});
      var scatterDim = ndx.dimension(function(d) {if(d.FinalAppropriation!=0){return [ ((d.ActualPayments/d.FinalAppropriation)*100),(d.ActualPayments<0)? 0: d.ActualPayments];} });

  //Groups, think y-axis
      var all = ndx.groupAll();
      var sumPerYear = yearDim.group().reduceSum(function(d) { return d.ActualPayments*1000 ; });
      var actSumPerProv = provDim.group().reduceSum(function(d) { return d.ActualPayments*1000 ; });
      var finalSumPerProv = provDim.group().reduceSum(function(d) { return d.FinalAppropriation*1000 ; });
      var diffPerProv = provDim.group().reduceSum(function(d) { return (d.FinalAppropriation - d.ActualPayments)*1000 ; });
      var scatter = scatterDim.group().reduceSum(function(d) { return d.ProvinceKey ; });

      // Making charts
      paymentsPerYear  = dc.numberDisplay('#paymentsPerYear');
      paymentsPerProv  = dc.pieChart('#paymentsPerProv');
      dataCount = dc.dataCount('#data-count');
      differencePerYear  = dc.barChart('#differencePerProv');
      scatterPlot  = dc.seriesChart('#scatterPlot');

    // Tooltip derivation
    function findDepartKey(provKey, finalApp){
      return $.grep(data, function(e){return (e.ProvinceKey == provKey) && (e.ActualPayments == finalApp);})[0]['DepartmentKey'];
    }


    // Individual Charts
    paymentsPerYear
      .formatNumber(customFormat.numberFormat("$,.4s"))
      .dimension(yearDim)
      .html({none:"<div class=\"none\"> %number </div>",
             some:"<div class=\"some\"> %number </div>",
             all: "<div class=\"all\"> %number </div>"})
      .group(sumPerYear);

    //PieChart
    paymentsPerProv
      .width($("#paymentsPerProv").width())
      .height(300)
      .innerRadius(30)
      .dimension(provDim)
      .group(actSumPerProv);

    // Bar-chart
    differencePerYear
      .width($('#differencePerProv').width())
      .height(300)
      .dimension(provDim)
      .group(diffPerProv)
      .elasticY(true)
      .xAxisLabel('Province')
      .yAxisLabel("Total Expenditure (R mil)")
      .clipPadding(30)
      .x(d3.scale.ordinal())
      .xUnits(dc.units.ordinal)
      .margins().left += 60;

    // Scatter plot
    var ScatterDivPos = $('#scatterPlot').position();


    var toolTip = d3.select("#scatterPlot").append("div")
        .attr("class", "scattertooltip")
        .style("opacity", 0)
        .style("left", (ScatterDivPos.left + $('#scatterPlot').width()/7) + "px")
        .style("top", (ScatterDivPos.top) + "px");

    // Define symbols for scatterplot
    var symbolScale = d3.scale.ordinal().range(d3.svg.symbolTypes);
    var symbolAccessor = function(d){return symbolScale(d.value);};
    var scatterChart = function(c){
      return dc.scatterPlot(c)
          .symbol(symbolAccessor)
          .symbolSize(8)
          .highlightedSize(10)
    };

    scatterPlot
      .width($('#scatterPlot').width())
      .height(300)
      .chart(scatterChart)
      .x(d3.scale.linear().domain([-10,200]))
      .brushOn(true)
      .mouseZoomable(false)
      .yAxisLabel("Total Expenditure (R mil)")
      .xAxisLabel("Budget Utilised (%)")
      .dimension(scatterDim)
      .group(scatter)
      .seriesAccessor(function(d){return d.value;})
      .keyAccessor(function(d){return +d.key[0];})
      .valueAccessor(function(d){return d.key[1];})
      scatterPlot.margins().left += 40;
      // Trial Code
      scatterPlot.on("renderlet.a", function(_chart){
        _chart.selectAll('path.symbol').on("mouseover", function(d){
          toolTip.transition()
                  .duration(50)
                  .style("opacity", 0.9);
          toolTip.html( "<span> <b> Department Name: </b>" + clipString(departmentKey[findDepartKey(d.value,d.key[1])]) + "<br/><b> Amount: </b>" + d.key[1].formatRands() + " <br/><b> Utilisation: </b>" + (d.key[0]/100).percentify() + "</span>");
        });//Mouseover
        _chart.selectAll('path.symbol').on("mouseout", function(d){
          toolTip.transition()
                  .duration(200)
                  .style("opacity", 0);
        });//Mouseout
      });

    // Data count object
    dataCount
      .dimension(ndx)
      .group(all);

    //Resetting Filters
    d3.selectAll('a#resetTreasury').on('click', function () {
        toolTip.selectAll("*").remove();
        dc.filterAll();
        dc.renderAll();
        generateSupportingTreasuryGraphs(TotalTreasuryData, true);
      });

    dc.renderAll();
};
