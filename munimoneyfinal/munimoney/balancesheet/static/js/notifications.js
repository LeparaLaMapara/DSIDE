function genericDataSend(dataType){
  $.notify({
    title: "<strong>Data request sent:</strong>",
    message: "The " + dataType+ " data which you have requested will arrive shortly"
  },{
	  animate: {
		            enter: 'animated fadeInRight',
		            exit: 'animated fadeOutRight'
	   },
  });
}

function genericDataArrival(dataType){
  $.notify({
    icon : 'glyphicon glyphicon-star',
    title: '<strong>Your ' + dataType +' data has arrived</strong>',
    message: ""},{
    type: 'success',
    animate: {
      enter: 'animated fadeInRight',
      exit:  'animated fadeOutRight'
    }
  });
}

function animateLoad(buttonIdentifier){
  if (buttonIdentifier == 'Treasury') {
    $("#TreasuryLoad").toggleClass('fa-bar-chart-o');
    $("#TreasuryLoad").toggleClass('fa-spinner');
    $("#TreasuryLoad").toggleClass('fa-spin');
  }
  if (buttonIdentifier == 'Housing') {
    $("#Housing").toggleClass('fa-home' );
    $("#Housing").toggleClass('fa-spinner' );
    $("#Housing").toggleClass('fa-spin');
    // Toggle Parent Bar-chart icon
    $("#Census").toggleClass('fa-bar-chart-o');
    $("#Census").toggleClass('fa-spinner' );
    $("#Census").toggleClass('fa-spin');
  }
  if (buttonIdentifier == 'Services') {
    $("#Services").toggleClass('fa-bolt' );
    $("#Services").toggleClass('fa-spinner' );
    $("#Services").toggleClass('fa-spin');
    // Toggle Parent Bar-chart icon
    $("#Census").toggleClass('fa-bar-chart-o');
    $("#Census").toggleClass('fa-spinner' );
    $("#Census").toggleClass('fa-spin');
  }
  if (buttonIdentifier == 'Mortality') {
    $("#Mortality").toggleClass('fa-ban' );
    $("#Mortality").toggleClass('fa-spinner' );
    $("#Mortality").toggleClass('fa-spin');
    // Toggle Parent Bar-chart icon
    $("#Census").toggleClass('fa-bar-chart-o');
    $("#Census").toggleClass('fa-spinner' );
    $("#Census").toggleClass('fa-spin');
  }
  if (buttonIdentifier == 'Education') {
    $("#Education").toggleClass('fa-book' );
    $("#Education").toggleClass('fa-spinner' );
    $("#Education").toggleClass('fa-spin');
    // Toggle Parent Bar-chart icon
    $("#Census").toggleClass('fa-bar-chart-o');
    $("#Census").toggleClass('fa-spinner' );
    $("#Census").toggleClass('fa-spin');
  }
}
