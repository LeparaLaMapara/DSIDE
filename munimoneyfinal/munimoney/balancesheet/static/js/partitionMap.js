function createPartitionMap(root){
  var PartDivPos = $('#partitionMap').position();

  var w = $("#partitionMap").width(),
      h = 520,
      x = d3.scale.linear().range([0, w]),
      y = d3.scale.linear().range([0, h]);

  var vis = d3.select("#partitionMap").append("div")
      .attr("class", "chart")
      .style("width", w + "px")
      .style("height", h + "px")
      .attr("id","partitionMapDiv")
      .append("svg:svg")
      .attr("width", w)
      .attr("height", h);

  var toolTip = d3.select("#partitionMap").append("div")
      .attr("class", "partitiontooltip")
      .style("opacity", 0)
      .style("left", (PartDivPos.left) + "px")
      .style("top", (PartDivPos.top) + "px");

  var partition = d3.layout.partition()
      .value(function(d) { return d.size; });

    var g = vis.selectAll("g")
        .data(partition.nodes(root))
        .enter().append("svg:g")
        .attr("transform", function(d) { return "translate(" + x(d.y) + "," + y(d.x) + ")"; })
        .on("click", click)
        .on("mouseover", function(d){
          if (d.size){
            toolTip.transition()
                    .duration(50)
                    .style("opacity", 0.9);
            toolTip.html( "<span> <b> Name: </b>" + d.name + "<br/><b> Amount: </b>" + d.size.formatRands() + "</span>");
          }else{
            toolTip.transition()
                      .duration(50)
                      .style("opacity", 0.9);
            toolTip.html( "<span> <b> Name: </b>" + d.name +  "</span>");
          }//else
        })
        .on("mouseout", function(d){
          toolTip.transition()
                    .duration(200)
                    .style("opacity", 0);
        });

    var kx = w / root.dx,
        ky = h / 1;

    g.append("svg:rect")
        .attr("width", root.dy * kx)
        .attr("height", function(d) { return d.dx * ky; })
        .attr("class", function(d) { return d.children ? "parent" : "child"; })
        .on("click", function(d){
          if (!d.children) {
              extractColorKeys(TotalTreasuryData, ['Province', 'Department', 'ActualPayments', d.parent.id]);
              var colorScale = createColourScale(provinceColourKey);
              CreateProvinceLayer ();//Method in chloromap.js
              legend.update('Provincial', colorScale);
              selectionType = d.parent.name;
            }
        });

    g.append("svg:text")
        .attr("transform", transform)
        .attr("dy", ".35em")
        .style("opacity", function(d) { return d.dx * ky > 12 ? 1 : 0; })
        .text(function(d) { return d.name; })

    d3.select(window)
        .on("click", function() { click(root); })

    function click(d) {
      if (!d.children) return;

      kx = (d.y ? w - 40 : w) / (1 - d.y);
      ky = h / d.dx;
      x.domain([d.y, 1]).range([d.y ? 40 : 0, w]);
      y.domain([d.x, d.x + d.dx]);

      var t = g.transition()
          .duration(d3.event.altKey ? 7500 : 750)
          .attr("transform", function(d) { return "translate(" + x(d.y) + "," + y(d.x) + ")"; });

      t.select("rect")
          .attr("width", d.dy * kx)
          .attr("height", function(d) { return d.dx * ky; });

      t.select("text")
          .attr("transform", transform)
          .style("opacity", function(d) { return d.dx * ky > 12 ? 1 : 0; });

      d3.event.stopPropagation();
    }

    function transform(d) {
      return "translate(8," + d.dx * ky / 2 + ")";
    }
}//createPartitionMap

function clearPartitionMap(){
  d3.select("#partitionMapDiv").remove();
}
