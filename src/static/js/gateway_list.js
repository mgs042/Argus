var properties = [
	'name',
	'eui',
	'address',
	's_number',
];

$.each( properties, function( i, val ) {
	
	var orderClass = '';

	$("#" + val).click(function(e){
		e.preventDefault();
		$('.filter__link.filter__link--active').not(this).removeClass('filter__link--active');
  		$(this).toggleClass('filter__link--active');
   		$('.filter__link').removeClass('asc desc');

   		if(orderClass == 'desc' || orderClass == '') {
    			$(this).addClass('asc');
    			orderClass = 'asc';
       	} else {
       		$(this).addClass('desc');
       		orderClass = 'desc';
       	}

		var parent = $(this).closest('.header__item');
    		var index = $(".header__item").index(parent);
		var $table = $('.table-content');
		var rows = $table.find('.table-row').get();
		var isSelected = $(this).hasClass('filter__link--active');
		var isNumber = $(this).hasClass('filter__link--number');
			
		rows.sort(function(a, b){

			var x = $(a).find('.table-data').eq(index).text();
    			var y = $(b).find('.table-data').eq(index).text();
				
			if(isNumber == true) {
    					
				if(isSelected) {
					return x - y;
				} else {
					return y - x;
				}

			} else {
			
				if(isSelected) {		
					if(x < y) return -1;
					if(x > y) return 1;
					return 0;
				} else {
					if(x > y) return -1;
					if(x < y) return 1;
					return 0;
				}
			}
    		});

		$.each(rows, function(index,row) {
			$table.append(row);
		});

		return false;
	});

});

$(document).ready(function () {
    $.getJSON('/gateway_data', function (data) {
        const tableContent = $('.table-content'); // Target the table content container
        tableContent.empty(); // Clear existing rows
        console.log(data)
        // Loop through JSON data and create table rows dynamically
        data.forEach(row => {
            const html = `
				<a href="/gateway?uid=${row[5]}" id="row_link">
					<div class="table-row">
						<div class="table-data" >${row[1]}</div>
						<div class="table-data">${row[2]}</div>
						<div class="table-data">${row[3]}</div>
						<div class="table-data">${row[4]}</div>
					</div>
				</a>`;
            tableContent.append(html); // Append the new row to the table
        });
    });
});