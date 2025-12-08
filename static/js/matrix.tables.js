
$(document).ready(function(){
	$('#userTable tbody td').each(function(){
		var $td = $(this);
		// 若包含 a, button, input, select, textarea, img 等元素则跳过
		if ( $td.find('a,button,input,select,textarea,img').length ) return;
		var txt = $td.text();
		txt = txt.replace(/\u00A0/g,' ')
				.replace(/\s+/g,' ')
				.trim();
		$td.text(txt);
	});
	
	$('.data-table').dataTable({
		"bJQueryUI": true,
		"sPaginationType": "full_numbers",
		"sDom": '<""l>t<"F"fp>',
		"aLengthMenu": [[10, 25, 50, 100], [10, 25, 50, 100]],
        "iDisplayLength": 10,
		"bSmart": false,
		"aoColumnDefs": [
          { "bSearchable": false, "aTargets": [ 4 ] },
          { "bSortable":  false, "aTargets": [ 4 ] } 
		],
        "oLanguage": {
            "sLengthMenu": "展示 _MENU_ /页",
            "sSearch": "搜索：",
            "sZeroRecords": "没有找到记录",
            "sInfo": "显示 _START_ 到 _END_ / 共 _TOTAL_ 条",
            "sInfoEmpty": "显示 0 到 0 / 共 0 条",
            "sInfoFiltered": "(从 _MAX_ 条中筛选)",
            "oPaginate": {
                "sFirst": "首页",
                "sPrevious": "上一页",
                "sNext": "下一页",
                "sLast": "尾页"
            }
        }
	});
	
	$('input[type=checkbox],input[type=radio],input[type=file]').uniform();
	
	$('select').select2();
	
	$("span.icon input:checkbox, th input:checkbox").click(function() {
		var checkedStatus = this.checked;
		var checkbox = $(this).parents('.widget-box').find('tr td:first-child input:checkbox');		
		checkbox.each(function() {
			this.checked = checkedStatus;
			if (checkedStatus == this.checked) {
				$(this).closest('.checker > span').removeClass('checked');
			}
			if (this.checked) {
				$(this).closest('.checker > span').addClass('checked');
			}
		});
	});	
});
