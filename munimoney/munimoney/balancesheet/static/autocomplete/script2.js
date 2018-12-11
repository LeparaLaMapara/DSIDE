(function($){
    'use strict';

    // The JSON list url
	//{% load staticfiles %}
    var capitals = "country_capitals.json";

    /**
     * Create the options from the capitals array
     * @param {Array} capitals
     */
    function createList(capitals) {
        // get the datalist element
        var datalist = $("#capitallist");

        // Fill it with the capitals array
        for(var i=0; i<capitals.length; i++){
            $('<option>'+capitals[i]+'</option>').appendTo(datalist);
        }
    }


    /**
     * Load data and call callback function
     * @param {Function} callback
     */
    function loadDatas( callback ){

        // Make the ajax call
        $.getJSON(capitals, function(list){
            // create the Capitals array
            var capitals =[];
            for(var i=0; i<list.length; i++){
                capitals.push(list[i].CapitalName);
            }
            // Call the function that will create the options
            // But sort the array first (for better user experience)
            callback(capitals.sort());
        });
    }

    // jQuery OnLoad ...
    $(function(){
        loadDatas( createList );
    });

})(jQuery);
