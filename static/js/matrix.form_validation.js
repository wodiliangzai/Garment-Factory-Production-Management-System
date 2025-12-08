
$(document).ready(function(){
	$('input[type=checkbox],input[type=radio],input[type=file]').uniform();
	
	$('select').select2();

	$.extend($.validator.messages, {
		required: "不能为空",
		email: "请输入有效的邮箱地址",
		minlength: $.validator.format("请输入不少于{0}个字符"),
		maxlength: $.validator.format("请输入不多于{0}个字符"),
		equalTo: "请再次输入相同的值"
	});
	
	// Form Validation
    $("#basic_validate").validate({
		rules:{
			required:{
				required:true
			},
			realname:{
				required:true
			},
			email:{
				required:true,
				email: true
			},
			date:{
				required:true,
				date: true
			},
			url:{
				required:true,
				url: true
			},
			pwd:{
				required: true,
				minlength:6,
				maxlength:20
			},
			pwd2:{
				required:true,
				minlength:6,
				maxlength:20,
				equalTo:"#pwd"
			}
		},
		errorClass: "help-inline",
		errorElement: "span",
		highlight:function(element, errorClass, validClass) {
-			$(element).parents('.control-group').addClass('error');
+			$(element).parents('.control-group').removeClass('success').addClass('error');
        },
        unhighlight: function(element, errorClass, validClass) {
-			$(element).parents('.control-group').removeClass('error');
-			$(element).parents('.control-group').addClass('success');
+			$(element).parents('.control-group').removeClass('error').addClass('success');
        }
	});
	
	$("#number_validate").validate({
		rules:{
			min:{
				required: true,
				min:10
			},
			max:{
				required:true,
				max:24
			},
			number:{
				required:true,
				number:true
			}
		},
		errorClass: "help-inline",
		errorElement: "span",
		highlight:function(element, errorClass, validClass) {
-			$(element).parents('.control-group').addClass('error');
+			$(element).parents('.control-group').removeClass('success').addClass('error');
        },
        unhighlight: function(element, errorClass, validClass) {
-			$(element).parents('.control-group').removeClass('error');
-			$(element).parents('.control-group').addClass('success');
+			$(element).parents('.control-group').removeClass('error').addClass('success');
        }
	});
	
	$("#password_validate").validate({
		rules:{
			pwd:{
				required: true,
				minlength:6,
				maxlength:20
			},
			pwd2:{
				required:true,
				minlength:6,
				maxlength:20,
				equalTo:"#pwd"
			}
		},
		errorClass: "help-inline",
		errorElement: "span",
		highlight:function(element, errorClass, validClass) {
-			$(element).parents('.control-group').addClass('error');
+			$(element).parents('.control-group').removeClass('success').addClass('error');
        },
        unhighlight: function(element, errorClass, validClass) {
-			$(element).parents('.control-group').removeClass('error');
-			$(element).parents('.control-group').addClass('success');
+			$(element).parents('.control-group').removeClass('error').addClass('success');
        }
	});
});
