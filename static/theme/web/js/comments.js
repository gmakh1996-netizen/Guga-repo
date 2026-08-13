$(document).delegate('.ReplayButton', 'click', function(event) {
	
	var comment_id = $(this).data('id');
	
	
	var form = $('#post_comment').clone().addClass('write_replay').append('<div class="closeBtn"><i class="icofont-close"></i></div>');
	if( ! $(this).hasClass('active') ){
		form.attr('data-parent-id' , comment_id );
		if($(this).closest('.wrapp_subcommnet').length){
			$(this).closest('.reply').next('#new_comm_form').append(form);
		}else{
			$(this).closest('.comments-item').append(form);
		}
	}

	$(this).addClass('active');
});


$(document).delegate('#post_comment', 'submit', function(event) {
	event.preventDefault();

	var id 			= $(this).data('id');
	var type 		= $(this).data('type');
	var parent_id 	= $(this).data('parent-id') ? $(this).data('parent-id') : 0 ;
	var comment 	= $(this).find('#comment_text').val();
	var _this 		= $(this);
	
	if( $.trim($(_this).find('input[name="comment"]').val()).length > 0 ) {

		$.ajax({
		  url: '/profile/post_comment',
		  type: 'POST',
		  dataType: 'json',
		  data: {id:id,type:type,parent_id:parent_id,comment:comment},
		})
		.done(function(response) {
			
			if(response.errors){
				Notify(response.errors, 'danger');
				return;
			}
			if(!response.comment || !response.comment.id){
				Notify('კომენტარის დამატება ვერ მოხერხდა.', 'danger');
				return;
			}
			Notify(response.msg, 'success');
			
			var clicks = parseInt(document.getElementById("total_comments").textContent, 10);
			clicks += 1;
			document.getElementById("total_comments").innerHTML = clicks;
			
			var avatar = !(response.comment.thumb) ? base_url+response.comment.avatar : response.comment.thumb;
			$(_this).find('input[name="comment"]').val('');
			
			if( ! parent_id ){
				
				$('.comment_list').prepend(
				'<div class="comment comments-item">'+
					'<div class="comments-item__img"><figure><img src="'+ avatar +'"></figure></div>'+
					'<div class="comments-item__name">'+
						'<div class="comments-item__name-options">'+
							'<h2>'+response.comment.name +'  '+ response.comment.surname +'</h2>'+
							'<ul class="options">'+
								'<button class="CommentLike" data-action="like" data-id="'+ response.comment.id +'" title="მოწონება">'+
									'<span class="CommentCount">'+ response.comment.likes +'</span>'+
									'<svg width="18" height="16" fill="currentColor" class="fade-ready svg-icon svg-icon--heart flex-shrink-0" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M9 5.41L7.737 3.21c-.604-1.051-1.684-1.725-2.89-1.725-1.827 0-3.385 1.564-3.385 3.593 0 1.047.421 1.98 1.085 2.634l2.593 2.552H5.09l3.91 3.92 3.909-3.92h-.05l2.593-2.552a3.68 3.68 0 0 0 1.085-2.634c0-2.029-1.558-3.593-3.384-3.593-1.207 0-2.286.674-2.89 1.725L9 5.41zm.501 10.361a.674.674 0 0 1-.503.229.679.679 0 0 1-.532-.262L1.528 8.78h.001v-.001A5.093 5.093 0 0 1 .484 7.294 5.253 5.253 0 0 1 0 5.08C0 2.274 2.17 0 4.846 0A4.7 4.7 0 0 1 8.03 1.25c.38.348.708.757.97 1.212.262-.455.59-.864.97-1.212A4.7 4.7 0 0 1 13.155 0C15.83 0 18 2.274 18 5.079c0 .794-.174 1.546-.485 2.215a5.09 5.09 0 0 1-1.042 1.484h-.001l-.001.002h.002L9.5 15.77z" fill="currentColor"></path></svg>'+
								'</button>'+
								'<button class="ReplayButton" data-action="replay" data-id="'+ response.comment.id +'" title="უპასუხე">'+
									'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="24" fill="#fff" viewBox="0 0 24 24"> <path d="M12 0c-3.31 0-6.291 1.353-8.459 3.522l-2.48-2.48-1.061 7.341 7.437-.966-2.489-2.488c1.808-1.808 4.299-2.929 7.052-2.929 5.514 0 10 4.486 10 10s-4.486 10-10 10c-3.872 0-7.229-2.216-8.89-5.443l-1.717 1.046c2.012 3.803 6.005 6.397 10.607 6.397 6.627 0 12-5.373 12-12s-5.373-12-12-12z"></path> </svg>'+
								'</button>'+
								'<button class="EditComment" data-action="edit" data-id="'+ response.comment.id +'" title="რედაქტირება">'+
									'<svg fill="currentColor" height="16px" viewBox="0 -1 401.52289 401" width="16px" xmlns="http://www.w3.org/2000/svg"><path d="m370.589844 250.972656c-5.523438 0-10 4.476563-10 10v88.789063c-.019532 16.5625-13.4375 29.984375-30 30h-280.589844c-16.5625-.015625-29.980469-13.4375-30-30v-260.589844c.019531-16.558594 13.4375-29.980469 30-30h88.789062c5.523438 0 10-4.476563 10-10 0-5.519531-4.476562-10-10-10h-88.789062c-27.601562.03125-49.96875 22.398437-50 50v260.59375c.03125 27.601563 22.398438 49.96875 50 50h280.589844c27.601562-.03125 49.96875-22.398437 50-50v-88.792969c0-5.523437-4.476563-10-10-10zm0 0"/><path d="m376.628906 13.441406c-17.574218-17.574218-46.066406-17.574218-63.640625 0l-178.40625 178.40625c-1.222656 1.222656-2.105469 2.738282-2.566406 4.402344l-23.460937 84.699219c-.964844 3.472656.015624 7.191406 2.5625 9.742187 2.550781 2.546875 6.269531 3.527344 9.742187 2.566406l84.699219-23.464843c1.664062-.460938 3.179687-1.34375 4.402344-2.566407l178.402343-178.410156c17.546875-17.585937 17.546875-46.054687 0-63.640625zm-220.257812 184.90625 146.011718-146.015625 47.089844 47.089844-146.015625 146.015625zm-9.40625 18.875 37.621094 37.625-52.039063 14.417969zm227.257812-142.546875-10.605468 10.605469-47.09375-47.09375 10.609374-10.605469c9.761719-9.761719 25.589844-9.761719 35.351563 0l11.738281 11.734375c9.746094 9.773438 9.746094 25.589844 0 35.359375zm0 0"/></svg>'+
								'</button>'+
								'<button class="DeleteComment " data-action="delete" data-id="'+ response.comment.id +'" title="წაშლა">'+
									'<svg fill="currentColor" enable-background="new 0 0 512.016 512.016" height="16px" viewBox="0 0 512.016 512.016" width="18px" xmlns="http://www.w3.org/2000/svg"><g><path d="m448.199 164.387h-236.813l106.048-106.048c5.858-5.858 5.858-15.356 0-21.215l-26.872-26.872c-13.669-13.669-35.831-13.669-49.501 0l-27.63 27.631-14.144-14.144c-15.596-15.597-40.975-15.596-56.572 0l-55.158 55.158c-15.597 15.597-15.597 40.976 0 56.573l14.143 14.144-27.63 27.63c-13.669 13.669-13.669 35.831 0 49.501l26.872 26.872c5.857 5.858 15.356 5.859 21.214 0l38.021-38.021v231.416c0 35.901 29.104 65.005 65.005 65.005h158.012c35.901 0 65.005-29.104 65.005-65.005zm-325.284-35.989-14.143-14.143c-3.899-3.899-3.899-10.244 0-14.144l55.158-55.158c3.9-3.9 10.245-3.899 14.143 0l14.143 14.144zm129.533 299.612c0 8.285-6.716 15.001-15.001 15.001s-15.001-6.716-15.001-15.001v-179.616c0-8.285 6.716-15.001 15.001-15.001s15.001 6.716 15.001 15.001zm66.741 0c0 8.285-6.716 15.001-15.001 15.001s-15.001-6.716-15.001-15.001v-179.616c0-8.285 6.716-15.001 15.001-15.001s15.001 6.716 15.001 15.001zm66.741 0c0 8.285-6.716 15.001-15.001 15.001s-15.001-6.716-15.001-15.001v-179.616c0-8.285 6.716-15.001 15.001-15.001s15.001 6.716 15.001 15.001z"/><path d="m320.898 113.548c-9.151 3.19-15.571 11.361-16.631 20.842h143.932v-24.932c0-17.119-16.845-29.167-33.022-23.682l-93.968 27.672c-.101.029-.211.069-.311.1z"/></g></svg>'+
								'</button>'+
							'</ul>'+
						'</div>'+
						'<div class="comments-item__name-text" data-id="'+ response.comment.id +'"><p>'+ decodeURI(response.comment.comment) +'</p></div>'+
					'</div>'+
				'</div>');
				
			}else{
				
				$(_this).after(
				'<div class="comment comments-item reply">'+
					'<div class="comments-item__img"><figure><img src="'+ avatar +'"></figure></div>'+
					'<div class="comments-item__name">'+
						'<div class="comments-item__name-options">'+
							'<h2>'+response.comment.name +'  '+ response.comment.surname +'</h2>'+
							'<ul class="options">'+
								'<button class="CommentLike" data-action="like" data-id="'+ response.comment.id +'" title="მოწონება">'+
									'<span class="CommentCount">'+ response.comment.likes +'</span>'+
									'<svg width="18" height="16" fill="currentColor" class="fade-ready svg-icon svg-icon--heart flex-shrink-0" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M9 5.41L7.737 3.21c-.604-1.051-1.684-1.725-2.89-1.725-1.827 0-3.385 1.564-3.385 3.593 0 1.047.421 1.98 1.085 2.634l2.593 2.552H5.09l3.91 3.92 3.909-3.92h-.05l2.593-2.552a3.68 3.68 0 0 0 1.085-2.634c0-2.029-1.558-3.593-3.384-3.593-1.207 0-2.286.674-2.89 1.725L9 5.41zm.501 10.361a.674.674 0 0 1-.503.229.679.679 0 0 1-.532-.262L1.528 8.78h.001v-.001A5.093 5.093 0 0 1 .484 7.294 5.253 5.253 0 0 1 0 5.08C0 2.274 2.17 0 4.846 0A4.7 4.7 0 0 1 8.03 1.25c.38.348.708.757.97 1.212.262-.455.59-.864.97-1.212A4.7 4.7 0 0 1 13.155 0C15.83 0 18 2.274 18 5.079c0 .794-.174 1.546-.485 2.215a5.09 5.09 0 0 1-1.042 1.484h-.001l-.001.002h.002L9.5 15.77z" fill="currentColor"></path></svg>'+
								'</button>'+
								'<button class="ReplayButton" data-action="replay" data-id="'+ response.comment.id +'" title="უპასუხე">'+
									'<svg xmlns="http://www.w3.org/2000/svg" width="18" height="24" fill="#fff" viewBox="0 0 24 24"> <path d="M12 0c-3.31 0-6.291 1.353-8.459 3.522l-2.48-2.48-1.061 7.341 7.437-.966-2.489-2.488c1.808-1.808 4.299-2.929 7.052-2.929 5.514 0 10 4.486 10 10s-4.486 10-10 10c-3.872 0-7.229-2.216-8.89-5.443l-1.717 1.046c2.012 3.803 6.005 6.397 10.607 6.397 6.627 0 12-5.373 12-12s-5.373-12-12-12z"></path> </svg>'+
								'</button>'+
								'<button class="EditComment" data-action="edit" data-id="'+ response.comment.id +'" title="რედაქტირება">'+
									'<svg fill="currentColor" height="16px" viewBox="0 -1 401.52289 401" width="16px" xmlns="http://www.w3.org/2000/svg"><path d="m370.589844 250.972656c-5.523438 0-10 4.476563-10 10v88.789063c-.019532 16.5625-13.4375 29.984375-30 30h-280.589844c-16.5625-.015625-29.980469-13.4375-30-30v-260.589844c.019531-16.558594 13.4375-29.980469 30-30h88.789062c5.523438 0 10-4.476563 10-10 0-5.519531-4.476562-10-10-10h-88.789062c-27.601562.03125-49.96875 22.398437-50 50v260.59375c.03125 27.601563 22.398438 49.96875 50 50h280.589844c27.601562-.03125 49.96875-22.398437 50-50v-88.792969c0-5.523437-4.476563-10-10-10zm0 0"/><path d="m376.628906 13.441406c-17.574218-17.574218-46.066406-17.574218-63.640625 0l-178.40625 178.40625c-1.222656 1.222656-2.105469 2.738282-2.566406 4.402344l-23.460937 84.699219c-.964844 3.472656.015624 7.191406 2.5625 9.742187 2.550781 2.546875 6.269531 3.527344 9.742187 2.566406l84.699219-23.464843c1.664062-.460938 3.179687-1.34375 4.402344-2.566407l178.402343-178.410156c17.546875-17.585937 17.546875-46.054687 0-63.640625zm-220.257812 184.90625 146.011718-146.015625 47.089844 47.089844-146.015625 146.015625zm-9.40625 18.875 37.621094 37.625-52.039063 14.417969zm227.257812-142.546875-10.605468 10.605469-47.09375-47.09375 10.609374-10.605469c9.761719-9.761719 25.589844-9.761719 35.351563 0l11.738281 11.734375c9.746094 9.773438 9.746094 25.589844 0 35.359375zm0 0"/></svg>'+
								'</button>'+
								'<button class="DeleteComment " data-action="delete" data-id="'+ response.comment.id +'" title="წაშლა">'+
									'<svg fill="currentColor" enable-background="new 0 0 512.016 512.016" height="16px" viewBox="0 0 512.016 512.016" width="18px" xmlns="http://www.w3.org/2000/svg"><g><path d="m448.199 164.387h-236.813l106.048-106.048c5.858-5.858 5.858-15.356 0-21.215l-26.872-26.872c-13.669-13.669-35.831-13.669-49.501 0l-27.63 27.631-14.144-14.144c-15.596-15.597-40.975-15.596-56.572 0l-55.158 55.158c-15.597 15.597-15.597 40.976 0 56.573l14.143 14.144-27.63 27.63c-13.669 13.669-13.669 35.831 0 49.501l26.872 26.872c5.857 5.858 15.356 5.859 21.214 0l38.021-38.021v231.416c0 35.901 29.104 65.005 65.005 65.005h158.012c35.901 0 65.005-29.104 65.005-65.005zm-325.284-35.989-14.143-14.143c-3.899-3.899-3.899-10.244 0-14.144l55.158-55.158c3.9-3.9 10.245-3.899 14.143 0l14.143 14.144zm129.533 299.612c0 8.285-6.716 15.001-15.001 15.001s-15.001-6.716-15.001-15.001v-179.616c0-8.285 6.716-15.001 15.001-15.001s15.001 6.716 15.001 15.001zm66.741 0c0 8.285-6.716 15.001-15.001 15.001s-15.001-6.716-15.001-15.001v-179.616c0-8.285 6.716-15.001 15.001-15.001s15.001 6.716 15.001 15.001zm66.741 0c0 8.285-6.716 15.001-15.001 15.001s-15.001-6.716-15.001-15.001v-179.616c0-8.285 6.716-15.001 15.001-15.001s15.001 6.716 15.001 15.001z"/><path d="m320.898 113.548c-9.151 3.19-15.571 11.361-16.631 20.842h143.932v-24.932c0-17.119-16.845-29.167-33.022-23.682l-93.968 27.672c-.101.029-.211.069-.311.1z"/></g></svg>'+
								'</button>'+
							'</ul>'+
						'</div>'+
						'<div class="comments-item__name-text" data-id="'+ response.comment.id +'"><p>'+ decodeURI(response.comment.comment) +'</p></div>'+
					'</div>'+
				'</div><div id="new_comm_form"></div>');
			}
			
			if(parent_id){
				$(_this).remove();
			}
		})
		.fail(function(xhr) {
			var res = xhr.responseJSON || {};
			Notify(res.errors || 'კომენტარის დამატება ვერ მოხერხდა.', 'danger');
		});
		
		
	}
});

$(document).delegate('.write_replay#post_comment .closeBtn', 'click', function(event) {
	$(this).parent('.write_replay#post_comment').remove();
});


$(document).delegate('.EditComment', 'click', function(event) {
	var comment_id = $(this).data('id');
	var action = $(this).data('action');
	var _this = $(this);
	
	$.ajax({
		url: '/profile/post_comment',
		type: 'POST',
		dataType: 'json',
		data: {id:comment_id,action:action},
	})
	.done(function(data) {
		if(data.errors){
			Notify(data.errors, 'danger');
		}
		var data = data.comment
		
		$('#notify').html(
			'<div class="modal_overlay show">'+
				'<div id="outside_close"></div>'+
				'<div class="modal_box">'+
					'<div class="closeBtn"><i class="icofont-close"></i></div>'+
					'<h1>კომენტარის რედაქტირება</h1>'+
					'<form id="ChangeNameCommnet" data-action="edit" method="post" autocomplete="off">'+
						'<input class="input_1" name="comment">'+
						'<div class="form_buttons">'+
							'<button class="submit" title="დამახსოვრება" type="submit">დამახსოვრება</button>'+
						'</div>'+
					'</form>'+
				'</div>'+
			'</div>'
		);
		var form =$('.modal_box').find('form'); 
		form.data('id' , comment_id );
		
		console.log(decodeURI(data));
		
		form.find('input[name="comment"]').val(decodeURI(data));
	})
  
});



$(document).delegate('#ChangeNameCommnet', 'submit', function(event) {
	event.preventDefault();
	var id = $(this).data('id');
	var action = $(this).data('action');
	var comment = $(this).find('input[name="comment"]').val();

	$.ajax({
		
		url: '/profile/post_comment',
		type: 'POST',
		dataType: 'json',
		data: {id:id,action:action,comment:comment},
		
	}).done(function(data){
		
		$('.comments-item__name-text[data-id='+ id +'] p').html(decodeURI(comment))
		$('#notify').html('');
		Notify(data.msg);
		
	})
  
});



$(document).delegate('.CloseCommnetEditName', 'click', function(event) {
	$('#notify').html('');
});



$(document).delegate('.DeleteComment', 'click', function(event) {
	var comment_id = $(this).data('id');
	var action = $(this).data('action');
	var _this = $(this);

	$.ajax({
		url: '/profile/post_comment',
		type: 'POST',
		dataType: 'json',
		data: {id:comment_id,action:action},
	})
	.done(function(data) {
		$(_this).closest('.comments-item').first().remove();
		Notify(data.msg);
		var clicks = parseInt(document.getElementById("total_comments").textContent, 10);
		clicks -= 1;
		document.getElementById("total_comments").innerHTML = clicks;
	})

});




$(document).delegate('.CommentLike', 'click', function(event) {
	var comment_id = $(this).data('id');
	var action = $(this).data('action');
	var _this = $(this);

	$.ajax({
		url: '/profile/post_comment',
		type: 'POST',
		dataType: 'json',
		data: {id:comment_id,action:action},
	})
	.done(function(data) {
		
		if(data.errors){
			Notify(data.errors, 'danger');
			$(_this).removeClass('active')
			$(_this).find('.CommentCount').addClass('active').html(data.comment.likes)
		}else{
			Notify(data.msg);
			$(_this).addClass('active')
			$(_this).find('.CommentCount').addClass('active').html(data.comment.likes)
		}
	})
	
});



var id_comments = $('#commnets_data').data('id');
var type_comments = $('#commnets_data').data('type');

if(id_comments){
	
	$.post("/profile/load_comments",{id:id_comments,type:type_comments}, function( comments_form ) {
		$('#commnets_data').html(comments_form);
	});
	
}



var page_comms = 0;
$(document).delegate('#more_comments', 'click', function(event) {
	page_comms+=5;
	$.post("/profile/load_comments",{id:id_comments,type:type_comments,page:page_comms}, function( more_comments ) {
		$('#commnets_data').append(more_comments);
	});
	$(this).remove();
});




