
var notificationsIntervalId = null;
var notificationsBootstrapped = false;

function scheduleNotificationPolling() {
	if (notificationsIntervalId) return;
	notificationsIntervalId = setInterval(function () {
		// Hidden tabs don't need real-time bell updates.
		if (document.hidden) return;
		count_notify();
	}, 60000);
}

function bootstrapNotificationsWidget() {
	if (notificationsBootstrapped) return;
	notificationsBootstrapped = true;

	$.get("/Api/Notifications")
		.done(function (notifications) {
			$("#notifications").html(notifications);
		})
		.always(function () {
			// Count should run only after bell markup is available.
			count_notify();
			scheduleNotificationPolling();
		});
}

var webPushState = {
	config: null,
	messaging: null,
	swReg: null,
	currentToken: '',
	foregroundBound: false
};
var webPushBindingsReady = false;
var firebaseScriptsPromise = null;

function webPushSupported() {
	return typeof window !== 'undefined'
		&& 'Notification' in window
		&& 'serviceWorker' in navigator
		&& 'fetch' in window;
}

function webPushSecureContext() {
	if (window.isSecureContext) return true;
	var host = (window.location && window.location.hostname) ? window.location.hostname : '';
	return host === 'localhost' || host === '127.0.0.1';
}

function setWebPushStatus(text, isError) {
	var $status = $('[data-push-status]');
	if (!$status.length) return;
	$status.text(text || 'სტატუსი უცნობია');
	if (isError) {
		$status.addClass('text-danger');
	} else {
		$status.removeClass('text-danger');
	}
}

function setWebPushButtonsDisabled(disabled) {
	$('[data-push-enable-btn], [data-push-disable-btn]').prop('disabled', !!disabled);
}

function loadExternalScriptOnce(src) {
	return new Promise(function (resolve, reject) {
		if (document.querySelector('script[src="' + src + '"]')) {
			resolve();
			return;
		}
		var script = document.createElement('script');
		script.src = src;
		script.async = true;
		script.onload = function () { resolve(); };
		script.onerror = function () { reject(new Error('script_load_failed')); };
		document.head.appendChild(script);
	});
}

function loadFirebaseCompatScripts() {
	if (window.firebase && typeof window.firebase.messaging === 'function') {
		return Promise.resolve();
	}
	if (firebaseScriptsPromise) return firebaseScriptsPromise;

	firebaseScriptsPromise = loadExternalScriptOnce('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js')
		.then(function () {
			return loadExternalScriptOnce('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');
		});
	return firebaseScriptsPromise;
}

async function fetchWebPushConfig(force) {
	if (webPushState.config && !force) return webPushState.config;

	var response = await fetch('/profile/push_config', {
		method: 'GET',
		credentials: 'same-origin',
		cache: 'no-store'
	});
	if (!response.ok) {
		throw new Error('push_config_http_' + response.status);
	}
	var data = await response.json();
	if (!data || data.status !== 'ok') {
		throw new Error('push_config_invalid');
	}
	webPushState.config = data;
	return data;
}

function webPushBrowserName() {
	var ua = (navigator.userAgent || '').toLowerCase();
	if (ua.indexOf('edg/') !== -1) return 'Edge';
	if (ua.indexOf('chrome/') !== -1) return 'Chrome';
	if (ua.indexOf('firefox/') !== -1) return 'Firefox';
	if (ua.indexOf('safari/') !== -1) return 'Safari';
	return 'Unknown';
}

function normalizePushUrl(url) {
	url = (url || '').toString().trim();
	if (!url) return '';
	if (url.indexOf('http://') === 0 || url.indexOf('https://') === 0) return url;
	if (url.indexOf('/') === 0) return url;
	return '';
}

function parseForegroundPushPayload(payload) {
	var notification = payload && payload.notification ? payload.notification : {};
	var data = payload && payload.data ? payload.data : {};
	var fcmOptions = payload && payload.fcmOptions ? payload.fcmOptions : {};

	var title = (notification.title || data.title || 'GE.MOVIE').toString();
	var body = (notification.body || data.body || '').toString();
	var icon = (notification.icon || data.icon || '/theme/web/img/logo.svg').toString();
	var image = (notification.image || data.image || '').toString();
	var url = normalizePushUrl(fcmOptions.link || data.url || data.click_action || '');

	return {
		title: title,
		body: body,
		icon: icon,
		image: image,
		url: url
	};
}

function showForegroundPushNotification(payload) {
	var parsed = parseForegroundPushPayload(payload);
	if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
		try {
			var options = {
				body: parsed.body,
				icon: parsed.icon,
				data: { url: parsed.url }
			};
			if (parsed.image) options.image = parsed.image;
			var note = new Notification(parsed.title, options);
			note.onclick = function () {
				if (!parsed.url) return;
				window.focus();
				window.location.href = parsed.url;
			};
			return;
		} catch (err) {}
	}

	if (typeof Notify === 'function') {
		var text = parsed.body ? (parsed.title + ' — ' + parsed.body) : parsed.title;
		Notify(text, 'success');
	}
}

async function ensureWebPushMessaging() {
	if (!webPushSupported()) throw new Error('push_not_supported');
	if (!webPushSecureContext()) throw new Error('https_required');

	var config = await fetchWebPushConfig();
	if (!config.enabled_for_web || !config.firebase) {
		throw new Error('push_not_configured');
	}

	await loadFirebaseCompatScripts();
	if (!window.firebase || typeof window.firebase.initializeApp !== 'function' || typeof window.firebase.messaging !== 'function') {
		throw new Error('firebase_unavailable');
	}

	var appName = 'moviege-webpush';
	var app = null;
	try {
		app = window.firebase.app(appName);
	} catch (e) {
		var initConfig = {
			apiKey: config.firebase.apiKey,
			projectId: config.firebase.projectId,
			messagingSenderId: config.firebase.messagingSenderId,
			appId: config.firebase.appId
		};
		if (config.firebase.measurementId) {
			initConfig.measurementId = config.firebase.measurementId;
		}
		app = window.firebase.initializeApp(initConfig, appName);
	}

	webPushState.swReg = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
	webPushState.messaging = window.firebase.messaging(app);

	if (!webPushState.foregroundBound) {
		webPushState.messaging.onMessage(function (payload) {
			showForegroundPushNotification(payload);
		});
		webPushState.foregroundBound = true;
	}

	return webPushState.messaging;
}

async function saveWebPushToken(token, permissionValue) {
	var response = await fetch('/profile/push_token_register', {
		method: 'POST',
		credentials: 'same-origin',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			token: token,
			provider: 'firebase',
			platform: navigator.platform || '',
			browser: webPushBrowserName(),
			permission: permissionValue || Notification.permission || 'granted'
		})
	});
	return response.ok ? response.json() : null;
}

async function unregisterWebPushToken(token) {
	var response = await fetch('/profile/push_token_unregister', {
		method: 'POST',
		credentials: 'same-origin',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			token: token || ''
		})
	});
	return response.ok ? response.json() : null;
}

async function refreshWebPushStatus() {
	if (!$('[data-push-status]').length) return;

	if (!webPushSupported()) {
		setWebPushStatus('სტატუსი: ბრაუზერი Web Push-ს არ უჭერს მხარს.', true);
		return;
	}
	if (!webPushSecureContext()) {
		setWebPushStatus('სტატუსი: საჭიროა HTTPS.', true);
		return;
	}

	try {
		var response = await fetch('/profile/push_status', {
			method: 'GET',
			credentials: 'same-origin',
			cache: 'no-store'
		});
		if (response.status === 401) {
			setWebPushStatus('სტატუსი: ჯერ გაიარე ავტორიზაცია.', true);
			return;
		}
		var data = await response.json();
		var count = parseInt(data && data.active_token_count ? data.active_token_count : 0, 10);
		if (count > 0) {
			setWebPushStatus('სტატუსი: ჩართულია (' + count + ' აქტიური token)', false);
		} else if (Notification.permission === 'denied') {
			setWebPushStatus('სტატუსი: ბრაუზერში დაბლოკილია (Permission denied).', true);
		} else {
			setWebPushStatus('სტატუსი: გამორთულია', false);
		}
	} catch (err) {
		setWebPushStatus('სტატუსი: შეცდომა სტატუსის წაკითხვაზე.', true);
	}
}

async function enableWebPushNotifications() {
	if (!webPushSupported()) {
		setWebPushStatus('Web Push ამ ბრაუზერში მიუწვდომელია.', true);
		return;
	}
	if (!webPushSecureContext()) {
		setWebPushStatus('Push-სთვის საჭიროა HTTPS.', true);
		return;
	}

	setWebPushButtonsDisabled(true);
	try {
		var config = await fetchWebPushConfig(true);
		if (!config.enabled_for_web || !config.firebase || !config.firebase.vapidKey) {
			setWebPushStatus('Push კონფიგურაცია incompleteა. შეამოწმე Admin Settings.', true);
			return;
		}

		var permission = await Notification.requestPermission();
		if (permission !== 'granted') {
			setWebPushStatus('Permission არ მიენიჭა. ბრაუზერში გაააქტიურე Notifications.', true);
			return;
		}

		var messaging = await ensureWebPushMessaging();
		var token = await messaging.getToken({
			vapidKey: config.firebase.vapidKey,
			serviceWorkerRegistration: webPushState.swReg
		});

		if (!token) {
			setWebPushStatus('Token ვერ მიიღო ბრაუზერიდან.', true);
			return;
		}

		webPushState.currentToken = token;
		console.info('[WebPush] FCM token:', token);
		var saved = await saveWebPushToken(token, permission);
		if (!saved || saved.status !== 'ok') {
			setWebPushStatus('Token backend-ში ვერ შეინახა.', true);
			return;
		}

		setWebPushStatus('სტატუსი: ჩართულია (Desktop Push აქტიურია)', false);
		await refreshWebPushStatus();
	} catch (err) {
		setWebPushStatus('Enable Notifications შეცდომა: ' + (err && err.message ? err.message : 'unknown_error'), true);
	} finally {
		setWebPushButtonsDisabled(false);
	}
}

async function disableWebPushNotifications() {
	setWebPushButtonsDisabled(true);
	try {
		var token = webPushState.currentToken || '';
		try {
			var config = await fetchWebPushConfig();
			if (!token && config && config.firebase && config.firebase.vapidKey) {
				var messaging = await ensureWebPushMessaging();
				token = await messaging.getToken({
					vapidKey: config.firebase.vapidKey,
					serviceWorkerRegistration: webPushState.swReg
				});
			}
			if (token && webPushState.messaging && typeof webPushState.messaging.deleteToken === 'function') {
				await webPushState.messaging.deleteToken(token);
			}
		} catch (err) {}

		await unregisterWebPushToken(token);
		webPushState.currentToken = '';
		setWebPushStatus('სტატუსი: გამორთულია', false);
		await refreshWebPushStatus();
	} catch (err) {
		setWebPushStatus('Disable Notifications შეცდომა.', true);
	} finally {
		setWebPushButtonsDisabled(false);
	}
}

function bindWebPushControls() {
	if (webPushBindingsReady) return;
	webPushBindingsReady = true;

	$(document).on('click', '[data-push-enable-btn]', function (e) {
		e.preventDefault();
		enableWebPushNotifications();
	});

	$(document).on('click', '[data-push-disable-btn]', function (e) {
		e.preventDefault();
		disableWebPushNotifications();
	});
}

function initWebPushForLoggedUser() {
	bindWebPushControls();
	refreshWebPushStatus();
	ensureWebPushMessaging().catch(function () {});
}

// GET PROFILE (UserArea in the header — login link or profile menu)
// `#UserArea` is duplicated across left.php + header.php for mobile views;
// use attribute selector so both get filled.
$.get("/Api/Profile", function (profile) {
	$('[id="UserArea"]').html(profile);
	if (document.querySelector('[id="UserArea"] .myprofile')) {
		bootstrapNotificationsWidget();
		initWebPushForLoggedUser();
	}
});

// Mobile profile dropdown — click-to-open (delegated; UserArea is injected dynamically)
$(document).on("click", ".myprofile--mobile .js-profile-toggle", function (e) {
	e.preventDefault();
	e.stopPropagation();
	$(this).siblings(".js-profile-menu").toggleClass("is-open");
});
$(document).on("click", function (e) {
	var $menu = $(".myprofile--mobile .js-profile-menu.is-open");
	if (!$menu.length) return;
	if ($(e.target).closest(".myprofile--mobile").length) return;
	$menu.removeClass("is-open");
});
$(document).on("keydown", function (e) {
	if (e.key === "Escape") $(".myprofile--mobile .js-profile-menu").removeClass("is-open");
});

// GET NOTIFICATIONS
async function count_notify() {
    let url = '/profile/notifications/count';
    let data = null;
    
    try {
        data = await (await fetch(url)).json();
    } catch(e) {
        console.log('error');
    }

    if(!data) return;

		var trigger = document.querySelector(".sms-trigger");
		if (!trigger) return;
		var bell = trigger.querySelector("svg");
		if (!bell) return;
		var unread = parseInt(data.notification, 10);
		if (isNaN(unread) || unread < 0) unread = 0;

		if(unread > 0){
			var sms = trigger.querySelector("span");
			bell.setAttribute("class", "ring-bell");
			if (sms) {
				sms.innerHTML = unread;
			} else {
				var newItem = document.createElement("span");
				newItem.appendChild(document.createTextNode(unread));
				trigger.insertBefore(newItem, bell);
			}
		}else{
			var badge = trigger.querySelector("span");
			if (badge) badge.remove();
			bell.removeAttribute('class');
		}
		
		
    //document.querySelector('.sms-trigger>span').innerHTML = data.notification;
}

// count_notify() starts from the /Api/Profile callback above, only for logged-in users.

// SEEN NOTIFICATIONS
async function seen_notify() {
    let url = '/profile/notifications/seen';
    let data = null;
    
    try {
        data = await (await fetch(url)).json();
    } catch(e) {
        console.log('error');
    }
	
	if(document.querySelector(".sms-trigger>span")){
		document.querySelector(".sms-trigger>span").remove();
		document.querySelector(".sms-trigger>svg").removeAttribute('class');
	}
	
}

// LIST NOTIFICATIONS
async function data_notify() {
    let url = '/profile/notifications/data';
    let data = null;
    
    try {
        data = await (await fetch(url)).json();
    } catch(e) {
        console.log('error');
    }

    if(!data) return;

	if(data.html){
		
		let html = document.querySelector(".sms-content__list>ul")
		
		html.innerHTML = data.html;
		
		//seen_notify();
		
	}else{
		
		let html = document.querySelector(".sms-content__list>ul");
		
		html.innerHTML = '<div class="empty_state">'+
							'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24"><path d="M18.586 20H4a.5.5 0 0 1-.4-.8l.4-.533V10c0-1.33.324-2.584.899-3.687L1.393 2.808l1.415-1.415 19.799 19.8-1.415 1.414L18.586 20zM6.408 7.822A5.985 5.985 0 0 0 6 10v8h10.586L6.408 7.822zM20 15.786l-2-2V10a6 6 0 0 0-8.99-5.203L7.56 3.345A8 8 0 0 1 20 10v5.786zM9.5 21h5a2.5 2.5 0 1 1-5 0z" fill="currentColor"></path></svg>'+
							'<div>'+data.message+'</div>'+
						'</div>';
		
	}
		
		
    //document.querySelector('.sms-trigger>span').innerHTML = data.notification;
}




// OPEN NOTIFICATIONS
$(document).delegate('.sms-content__list>ul li', 'click', function(event) {
	seen_notify();
	$(this).find('.notseen').remove();
	$(this).find('.active').removeClass('active');
});

// OPEN NOTIFICATIONS
$(document).delegate('.sms-trigger>svg', 'click', function(event) {
	event.stopPropagation();
	$(".sms-content").toggleClass("show");
	data_notify();
});


// OPEN USER
$(document).delegate('.myprofile', 'click', function(event) {
	event.stopPropagation();
	$(".myprofile ul").toggleClass("show");
	data_notify();
});


$(document).on("click", function(e) {
	
	if($(e.target).closest('.myprofile>ul').length || $(e.target).closest('.sms-content').length){
		
	}else{
		$(".myprofile>ul").removeClass("show");
		$(".sms-content").removeClass("show");
	}
});













/* 
$(document).delegate('#block_soon #subscribe', 'click', function(event) {
	console.log();
});
*/


/*
if($("#block_soon #subscribe")[0]){
	
	async function home_subscribe(data = {}) {
		
		let url = '/profile/subscribe';
		
		let send_json = JSON.stringify({'action':'get','data':data})
		
		const response = await fetch(url, {
			method: 'POST', // *GET, POST, PUT, DELETE, etc.
			mode: 'cors', // no-cors, *cors, same-origin
			cache: 'no-cache', // *default, no-cache, reload, force-cache, only-if-cached
			credentials: 'same-origin', // include, *same-origin, omit
			headers: {
			  'Content-Type': 'application/json;charset=utf-8',
			  'Content-Type': 'application/x-www-form-urlencoded',
			},
			redirect: 'follow', // manual, *follow, error
			referrerPolicy: 'no-referrer', // no-referrer, *no-referrer-when-downgrade, origin, origin-when-cross-origin, same-origin, strict-origin, strict-origin-when-cross-origin, unsafe-url
			body: send_json // body data type must match "Content-Type" header
		});
		
		let result = await response.json();
		
		for(var item in result.items) {
			//$('#block_soon #subscribe [data-id="'+result.items[item].id+'"]').addClass('subscribed');
			$('#subscribe[data-id="'+result.items[item].id+'"]').addClass('subscribed');
		}
		
	}
	
	
	res_subscribe = [];
	
	$("#block_soon #subscribe").each(function() {

		item = {}
		item["id"] = $(this).attr("data-id");
		item["type"] = $(this).attr("data-type");
		
		res_subscribe.push(item)
		
	});
	
	home_subscribe(res_subscribe);
	
}
*/






// OPEN NOTIFICATIONS
$(document).delegate('#contact_us', 'click', function(event) {
	$.ajax({
		url: '/profile/contact_popup',
		type: 'GET',
	})
	.done(function(data) {
		
		$('#notify').html(data);
		
	})
});






$('#UpdateInfomartion').submit(function(event) {
	event.preventDefault();
	var data = $(this).serialize();
	var _This = $(this);
	$(this).find('input').removeClass('is-invalid')
	$(this).find('.is-text-invalid').remove();
	$(this).find('.message-valid').remove();
	
	
	$.ajax({
		url: '/update/infomation',
		type: 'POST',
		dataType: 'json',
		data: data,
	})
	.done(function(response) {
		if(response.status=='success'){
			$(_This).append('<p class="message-valid arial">'+response.message+'</p>');
			Notify( response.message, 'success');
		}else{
			$.each(response.fields, function(index, val) {
				$(_This).find('input[name="'+ index +'"]').addClass('is-invalid');
				$('<p class="is-text-invalid arial"> '+ val +' </p>').insertAfter($(_This).find('input[name="'+ index +'"]'));
			});
			$(_This).append('<p class="is-text-invalid arial">'+response.message+'</p>');
		}
	})
	.fail(function() {
		//console.log("error");
	})
	.always(function() {
		//console.log("complete");
	});
	
	
});



$('#resetPassword').submit(function(event) {
	event.preventDefault();
	var data = $(this).serialize();
	var _This = $(this);
	$(this).find('input').removeClass('is-invalid')
	$(this).find('.is-text-invalid').remove();
	$(this).find('.message-valid').remove();

	$.ajax({
		url: '/update/password',
		type: 'POST',
		dataType: 'json',
		data: data,
	})
	.done(function(response) {
		if(response.status=='success'){
			$(_This).append('<p class="message-valid arial">'+response.message+'</p>');
			$(_This).find('input[name="password"]').val("");
			$(_This).find('input[name="old_password"]').val("");
			$(_This).find('input[name="password_confirmation"]').val("");
			Notify( response.message, 'success');
		}else{
			$.each(response.fields, function(index, val) {
				$(_This).find('input[name="'+ index +'"]').addClass('is-invalid');
				$('<p class="is-text-invalid arial"> '+ val +' </p>').insertAfter($(_This).find('input[name="'+ index +'"]'));
			});
			//$(_This).append('<p class="is-text-invalid arial">'+response.message+'</p>');
		}
	})
	.fail(function() {
		//console.log("error");
	})
	.always(function() {
		//console.log("complete");
	});
	
	
});


$('#UpdateNotificaion').submit(function(event) {
	event.preventDefault();
	var data = $(this).serialize();
	var _This = $(this);
	$(this).find('input').removeClass('is-invalid')
	$(this).find('.is-text-invalid').remove();
	$(this).find('.message-valid').remove();
	
	
	$.ajax({
		url: '/update/notifications',
		type: 'POST',
		dataType: 'json',
		data: data,
	})
	.done(function(response) {
		if(response.status=='success'){
			$(_This).append('<p class="message-valid arial">'+response.message+'</p>');
			Notify( response.message, 'success');
		}else{
			$.each(response.fields, function(index, val) {
				$(_This).find('input[name="'+ index +'"]').addClass('is-invalid');
				$('<p class="is-text-invalid arial"> '+ val +' </p>').insertAfter($(_This).find('input[name="'+ index +'"]'));
			});
			$(_This).append('<p class="is-text-invalid arial">'+response.message+'</p>');
		}
	})
	.fail(function() {
		//console.log("error");
	})
	.always(function() {
		//console.log("complete");
	});
	
	
});



$('#changeCover').on('change', function(e) {
    $('.change_image_error').remove();
    var file_data = $('#changeCover').prop('files')[0];
    if (!file_data) {
        return;
    }
    var validExt = ['jpeg', 'jpg', 'png'];
    var mime = (file_data.type || '').toLowerCase();
    var extension = mime.indexOf('/') > -1 ? mime.split('/')[1] : '';
    if (!extension && file_data.name) {
        var fileParts = file_data.name.toLowerCase().split('.');
        extension = fileParts.length > 1 ? fileParts.pop() : '';
    }
    var form_data = new FormData();
    form_data.append('file', file_data);
    if (validExt.indexOf(extension) == -1) {
		
        $('<p class="is-text-invalid arial change_image_error">სურათის ფორმატი არასწორია,დაშვებულია : jpeg , jpg ,png </p> ').insertAfter(".user-prof");
    
	} else {
		
        $.ajax({
            url: '/profile/changeImage',
            dataType: 'json',
            cache: false,
            contentType: false,
            processData: false,
            data: form_data,
            type: 'post',
            success: function(response) {
				if(response.status=='success'){
					$('#ProfileImg').attr('src', response.thumb);
					$('#ProfileImage').attr('src', response.thumb);
					Notify(response.message, 'success');
				}else if(response && response.errors){
					Notify(response.errors, 'danger');
				}else{
					Notify('სურათის ატვირთვა ვერ მოხერხდა.', 'danger');
				}
				
            },
			error: function(xhr) {
				var response = xhr.responseJSON || {};
				Notify(response.errors || 'სურათის ატვირთვა ვერ მოხერხდა.', 'danger');
			}
        });
		
    }
});


$('#changeCoverCollection').on('change', function(e) {

    var coll_id = $(this).data('id');
    var file_data = $('#changeCoverCollection').prop('files')[0];
    if (!file_data) {
        return;
    }
    var form_data = new FormData();
    form_data.append('file', file_data);
	
	
	
    $.ajax({
		url: '/profile/changeImage/'+coll_id,
		dataType: 'json',
		cache: false,
		contentType: false,
		processData: false,
		data: form_data,
		type: 'post',
		success: function(response) {
			if(response.status=='success'){
				$('.CoverCollection').attr('src', response.image);
				Notify(response.message, 'success');
			}else if(response && response.errors){
				Notify(response.errors, 'danger');
			}else{
				Notify('სურათის ატვირთვა ვერ მოხერხდა.', 'danger');
			}
		},
		error: function(xhr) {
			var response = xhr.responseJSON || {};
			Notify(response.errors || 'სურათის ატვირთვა ვერ მოხერხდა.', 'danger');
		}
    });

});




var id_comments = $('#commnets_data').data('id');
var type_comments = $('#commnets_data').data('type');
/*
if(id_comments){
	
	$.post("/profile/load_comments",{id:id_comments,type:type_comments}, function( comments_form ) {
		$('#commnets_data').html(comments_form);
	});
	
}
*/



$(document).delegate('#subscribe', 'click', function(event) {

	var action = $(this).attr('id');
	var id = $(this).data('id');
	var type = $(this).data('type');
	var _this = $(this);

	$.ajax({
	url: '/profile/'+action,
	type: 'POST',
	dataType: 'json',
	data: {action:action,id:id,type:type },
	})
	.done(function(data) {
		
		if (data.status === 'add') {
			
			Notify(data.message);
			if( $(_this).hasClass('inner_btn') ){
				$(_this).addClass('active')
			}else{
				$(_this).addClass('subscribed').attr('title',data.message)
				//.html('<i class="fas fa-check mr-2"></i>' + data.message)
			}
			
		}
		
		if (data.status === 'delete') {
			
			Notify(data.message,'danger');
			if($(_this).hasClass('inner_btn')){
				$(_this).removeClass('active')
			}else{  
				$(_this).removeClass('subscribed').attr('title',data.message)
			}
			
		}
		
		if (!data.status) {
			
			Notify(data.errors,'danger');
			
		}
		
	})
	.fail(function(error) {
	var response = error.responseJSON;
		if( response.errors ) Notify( response.errors,'danger');
	})

});









$(document).on("click", function (e) {
	$('#items_menu #toogle-menu').html('');
});


$(document).delegate('#items_menu', 'click', function(e) {
	
	$(this).toggleClass('open');
	
	if($(this).hasClass('open')) {
		
		
		var id = $(this).data('id');
		var movie_id = $(this).data('movie_id');
		var type = $(this).data('type');
		var $_this = $(this);
		var $_menu = $(this).find('#toogle-menu');
		
		
		$.ajax({
			url: '/profile/actions',
			type: 'POST',
			dataType: 'json',
			data: { id:id, type:type },
		}).done(function(results) {
			//console.log(results);
			if(results.errors){
				Notify( results.errors ,'danger');
			}else{
				$($_menu).html(
					'<div id="going_watches" data-type="'+type+'" data-id="'+id+'" class="'+results.going_watches.status+'">'+
						'<svg width="16" height="16" fill="currentColor" class="fade-ready svg-icon svg-icon--watch-later" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-8 6.5a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13z" fill="currentColor"></path><path d="M8.5 9V4H7v5h1.5z" fill="currentColor"></path><path d="M11.015 10.117l-3.12-2.285L7 9.055l3.12 2.285.895-1.223z" fill="currentColor"></path></svg>'+
						'<span>'+results.going_watches.message+'</span>'+
					'</div>'+
					'<div id="favorites" data-type="'+type+'" data-id="'+id+'" class="'+results.favorites.status+'">'+
						'<svg width="18" height="16" fill="currentColor" class="fade-ready svg-icon svg-icon--heart flex-shrink-0" xmlns="http://www.w3.org/2000/svg"><path fill-rule="evenodd" clip-rule="evenodd" d="M9 5.41L7.737 3.21c-.604-1.051-1.684-1.725-2.89-1.725-1.827 0-3.385 1.564-3.385 3.593 0 1.047.421 1.98 1.085 2.634l2.593 2.552H5.09l3.91 3.92 3.909-3.92h-.05l2.593-2.552a3.68 3.68 0 0 0 1.085-2.634c0-2.029-1.558-3.593-3.384-3.593-1.207 0-2.286.674-2.89 1.725L9 5.41zm.501 10.361a.674.674 0 0 1-.503.229.679.679 0 0 1-.532-.262L1.528 8.78h.001v-.001A5.093 5.093 0 0 1 .484 7.294 5.253 5.253 0 0 1 0 5.08C0 2.274 2.17 0 4.846 0A4.7 4.7 0 0 1 8.03 1.25c.38.348.708.757.97 1.212.262-.455.59-.864.97-1.212A4.7 4.7 0 0 1 13.155 0C15.83 0 18 2.274 18 5.079c0 .794-.174 1.546-.485 2.215a5.09 5.09 0 0 1-1.042 1.484h-.001l-.001.002h.002L9.5 15.77z" fill="currentColor"></path></svg>'+
						'<span>'+results.favorites.message+'</span>'+
					'</div>'+
					'<div id="subscribes" data-type="'+type+'" data-id="'+id+'" class="'+results.subscribes.status+'">'+
						'<svg fill="currentColor" viewBox="-21 0 512 512" xmlns="http://www.w3.org/2000/svg"> <path fill="currentColor" d="m453.332031 229.332031c-8.832031 0-16-7.167969-16-16 0-61.269531-23.847656-118.847656-67.15625-162.175781-6.25-6.25-6.25-16.382812 0-22.632812s16.382813-6.25 22.636719 0c49.34375 49.363281 76.519531 115.007812 76.519531 184.808593 0 8.832031-7.167969 16-16 16zm0 0"></path> <path fill="currentColor" d="m16 229.332031c-8.832031 0-16-7.167969-16-16 0-69.800781 27.179688-135.445312 76.542969-184.789062 6.25-6.25 16.386719-6.25 22.636719 0s6.25 16.386719 0 22.636719c-43.328126 43.304687-67.179688 100.882812-67.179688 162.152343 0 8.832031-7.167969 16-16 16zm0 0"></path> <path fill="currentColor" d="m234.667969 512c-44.117188 0-80-35.882812-80-80 0-8.832031 7.167969-16 16-16s16 7.167969 16 16c0 26.476562 21.523437 48 48 48 26.472656 0 48-21.523438 48-48 0-8.832031 7.167969-16 16-16s16 7.167969 16 16c0 44.117188-35.882813 80-80 80zm0 0"></path> <path fill="currentColor" d="m410.667969 448h-352c-20.589844 0-37.335938-16.746094-37.335938-37.332031 0-10.925781 4.757813-21.269531 13.058594-28.375 32.445313-27.414063 50.941406-67.261719 50.941406-109.480469v-59.480469c0-82.34375 66.988281-149.332031 149.335938-149.332031 82.34375 0 149.332031 66.988281 149.332031 149.332031v59.480469c0 42.21875 18.496094 82.066406 50.730469 109.332031 8.511719 7.253907 13.269531 17.597657 13.269531 28.523438 0 20.585937-16.746094 37.332031-37.332031 37.332031zm-176-352c-64.707031 0-117.335938 52.628906-117.335938 117.332031v59.480469c0 51.644531-22.632812 100.414062-62.078125 133.757812-.746094.640626-1.921875 1.964844-1.921875 4.097657 0 2.898437 2.433594 5.332031 5.335938 5.332031h352c2.898437 0 5.332031-2.433594 5.332031-5.332031 0-2.132813-1.171875-3.457031-1.878906-4.054688-39.488282-33.386719-62.121094-82.15625-62.121094-133.800781v-59.480469c0-64.703125-52.628906-117.332031-117.332031-117.332031zm0 0"></path> <path fill="currentColor" d="m234.667969 96c-8.832031 0-16-7.167969-16-16v-64c0-8.832031 7.167969-16 16-16s16 7.167969 16 16v64c0 8.832031-7.167969 16-16 16zm0 0"></path> </svg>'+
						'<span>'+results.subscribes.message+'</span>'+
					'</div>'
				);
			}
			
		}).fail(function(error) {
			var response = error.responseJSON;
            if( response.errors ) Notify( response.errors ,'danger');
		});
		
	}
	
	
});





$(document).delegate('#toogle-menu div', 'click', function(e) {
	
	e.stopPropagation();
	
	var action		= $(this).attr('id');
	var type		= $(this).data('type');
	var movie_id	= $(this).data('movie_id');
	var id			= $(this).data('id');
	var _this		= $(this);
	
	$.ajax({
		url: '/profile/actions',
		type: 'POST',
		dataType: 'json',
		data: { id:id, movie_id:movie_id, action:action, type:type },
		
	}).done(function(data) {
		
		var collection_items = '';
		
		
		if(data.status=='get_list'){
			
			
			$.each( data.collections, function( key, collection ) {
				
				collection_items += 
					'<label class="m-0 py-2 overflow-hidden d-flex align-items-center">'+
						'<input class="filter-radio collection_input_check" '+ collection.status +' data-action="'+ action +'" data-type="'+ type +'" data-item="'+ id +'" data-movie_id="'+ movie_id +'" data-id="'+ collection.id +'" id="collection_id" name="collection_id" type="checkbox" value="'+ collection.id +'">'+
						'<div class="filter-custom-radio float-left mr-3"></div>'+
						'<div class="text-inversed arial font-size-14 float-left">'+ collection.name +'</div>'+
					'</label>';
			});
			
			$('#notify').html(
				'<div class="collection-pop-select justify-content-center align-items-center show" id="collectionList">'+
					'<div id="outside_close"></div>'+
					'<div class="collection-pop-in rounded-10 position-relative">'+
						'<div class="popup-head">'+
							'<div class="title">კოლექციაში დამატება</div>'+
							'<div class="closeBtn"><i class="icofont-close"></i></div>'+
						'</div>'+
						'<div class="popup-body">'+
							'<div id="collection_items">'+ collection_items +'</div>'+
						'</div>'+
					'</div>'+
				'</div>'
			);
			
			
			$('#collection_items').delegate('label #collection_id', 'click', function(event) {
				
				var action			= $(this).data('action');
				var type			= $(this).data('type');
				var item_id			= $(this).data('item');
				var movie_id		= $(this).data('movie_id');
				var collection_id	= $(this).data('id');
				
				$.ajax({
					
					url: '/profile/actions',
					type: 'POST',
					dataType: 'json',
					data: { collection_id:collection_id, movie_id:movie_id, action:action, type:type, item_id:item_id },
					
				}).done(function(data) {
					
					if(data.status === 'saved') {
						Notify(data.message);
					}
					
					if(data.status === 'deleted') {
						Notify(data.message,'danger');
					}
					
				})
				
			});
			
		}
		
		if(data.status=='create_list'){
			Notify(data.msg,'danger');
		}
		
		if(data.status === 'saved') {
			$(_this).addClass('active')
			$(_this).find('span').html(data.html)
			Notify(data.message);
		}
		if(data.status === 'deleted') {
			$(_this).removeClass('active')
			$(_this).find('span').html(data.html)
			Notify(data.message,'danger');
		}
	}).fail(function(error) {
			var response = error.responseJSON;
            if( response.errors ) Notify( response.errors ,'danger');
		});
	
});
































// START SAVE MENU - MOVIES AND SERIALS
//e.preventDefault();
//e.stopPropagation();

// duplicate handler removed — identical handler already registered above (line ~513)


var action_menu = $('#action_menu').data('id');

if(action_menu){
	
	var id			 = $('#action_menu').data('id');
	var movie_id	 = $('#action_menu').data('movie_id');
	var type		 = $('#action_menu').data('type');
	
	$('#action_menu').html(
		'<li id="going_watches" data-id="'+ movie_id +'" data-movie_id="'+ movie_id +'" data-type="movie" class="">'+
			'<span tooltip="ვაპირებ ყურებას"><svg id="Capa_1" enable-background="new 0 0 443.294 443.294" height="20" viewBox="0 0 443.294 443.294" width="20" xmlns="http://www.w3.org/2000/svg"> <path d="m221.647 0c-122.214 0-221.647 99.433-221.647 221.647s99.433 221.647 221.647 221.647 221.647-99.433 221.647-221.647-99.433-221.647-221.647-221.647zm0 415.588c-106.941 0-193.941-87-193.941-193.941s87-193.941 193.941-193.941 193.941 87 193.941 193.941-87 193.941-193.941 193.941z"></path> <path d="m235.5 83.118h-27.706v144.265l87.176 87.176 19.589-19.589-79.059-79.059z"></path> </svg></span>'+
		'</li>'+
		'<li id="favorites" data-id="'+ movie_id +'" data-movie_id="'+ movie_id +'" data-type="movie" class="">'+
			'<span tooltip="ფავორიტებში დამატება"><svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 512 512" style="enable-background:new 0 0 512 512;" xml:space="preserve"> <g> <g> <path d="M375.467,22.164c-60.061,0-99.769,32.795-119.467,54.493c-19.697-21.696-59.406-54.493-119.467-54.493 C54.581,22.164,0,98.373,0,183.744c0,63.878,32.211,188.323,247.931,304.064c5.037,2.703,11.098,2.705,16.138,0 C479.79,372.066,512,247.622,512,183.744C512,96.392,455.803,22.164,375.467,22.164z M256,453.348 C152.381,396.376,34.133,301.45,34.133,183.744c0-65.477,39.319-127.446,102.4-127.446c47.857,0,87.452,29.344,104.973,56.973 c6.679,10.743,22.365,10.732,29.017-0.046c0.352-0.569,35.938-56.928,104.944-56.928c63.551,0,102.4,62.591,102.4,127.446 C477.867,301.452,359.622,396.375,256,453.348z"></path> </g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> </svg></span>'+
		'</li>'+
		'<li id="subscribes" data-type="'+type+'" data-id="'+id+'" class="">'+
			'<span tooltip="გამოწერა"><svg viewBox="-21 0 512 512" xmlns="http://www.w3.org/2000/svg"> <path d="m453.332031 229.332031c-8.832031 0-16-7.167969-16-16 0-61.269531-23.847656-118.847656-67.15625-162.175781-6.25-6.25-6.25-16.382812 0-22.632812s16.382813-6.25 22.636719 0c49.34375 49.363281 76.519531 115.007812 76.519531 184.808593 0 8.832031-7.167969 16-16 16zm0 0"></path> <path d="m16 229.332031c-8.832031 0-16-7.167969-16-16 0-69.800781 27.179688-135.445312 76.542969-184.789062 6.25-6.25 16.386719-6.25 22.636719 0s6.25 16.386719 0 22.636719c-43.328126 43.304687-67.179688 100.882812-67.179688 162.152343 0 8.832031-7.167969 16-16 16zm0 0"></path> <path d="m234.667969 512c-44.117188 0-80-35.882812-80-80 0-8.832031 7.167969-16 16-16s16 7.167969 16 16c0 26.476562 21.523437 48 48 48 26.472656 0 48-21.523438 48-48 0-8.832031 7.167969-16 16-16s16 7.167969 16 16c0 44.117188-35.882813 80-80 80zm0 0"></path> <path d="m410.667969 448h-352c-20.589844 0-37.335938-16.746094-37.335938-37.332031 0-10.925781 4.757813-21.269531 13.058594-28.375 32.445313-27.414063 50.941406-67.261719 50.941406-109.480469v-59.480469c0-82.34375 66.988281-149.332031 149.335938-149.332031 82.34375 0 149.332031 66.988281 149.332031 149.332031v59.480469c0 42.21875 18.496094 82.066406 50.730469 109.332031 8.511719 7.253907 13.269531 17.597657 13.269531 28.523438 0 20.585937-16.746094 37.332031-37.332031 37.332031zm-176-352c-64.707031 0-117.335938 52.628906-117.335938 117.332031v59.480469c0 51.644531-22.632812 100.414062-62.078125 133.757812-.746094.640626-1.921875 1.964844-1.921875 4.097657 0 2.898437 2.433594 5.332031 5.335938 5.332031h352c2.898437 0 5.332031-2.433594 5.332031-5.332031 0-2.132813-1.171875-3.457031-1.878906-4.054688-39.488282-33.386719-62.121094-82.15625-62.121094-133.800781v-59.480469c0-64.703125-52.628906-117.332031-117.332031-117.332031zm0 0"></path> <path d="m234.667969 96c-8.832031 0-16-7.167969-16-16v-64c0-8.832031 7.167969-16 16-16s16 7.167969 16 16v64c0 8.832031-7.167969 16-16 16zm0 0"></path> </svg></span>'+
		'</li>'
	);
	/*
	$.ajax({
		url: '/profile/actions',
		type: 'POST',
		dataType: 'json',
		data: { id:id, movie_id:movie_id, type:type },
	}).done(function(results) {
		
		//console.log(results);
		
		if( !results.errors ){
		
			$('#action_menu').html(
				'<li id="going_watches" data-id="'+movie_id+'" data-movie_id="'+movie_id+'" data-type="'+type+'" class="'+results.going_watches.status+'">'+
					'<span tooltip="'+results.going_watches.message+'">'+
						'<svg id="Capa_1" enable-background="new 0 0 443.294 443.294" height="20" viewBox="0 0 443.294 443.294" width="20" xmlns="http://www.w3.org/2000/svg"> <path d="m221.647 0c-122.214 0-221.647 99.433-221.647 221.647s99.433 221.647 221.647 221.647 221.647-99.433 221.647-221.647-99.433-221.647-221.647-221.647zm0 415.588c-106.941 0-193.941-87-193.941-193.941s87-193.941 193.941-193.941 193.941 87 193.941 193.941-87 193.941-193.941 193.941z"></path> <path d="m235.5 83.118h-27.706v144.265l87.176 87.176 19.589-19.589-79.059-79.059z"></path> </svg>'+
					'</span>'+
				'</li>'+
				'<li id="favorites" data-id="'+movie_id+'" data-movie_id="'+movie_id+'" data-type="'+type+'" class="'+results.favorites.status+'">'+
					'<span tooltip="'+results.favorites.message+'">'+
						'<svg version="1.1" id="Layer_1" xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" x="0px" y="0px" viewBox="0 0 512 512" style="enable-background:new 0 0 512 512;" xml:space="preserve"> <g> <g> <path d="M375.467,22.164c-60.061,0-99.769,32.795-119.467,54.493c-19.697-21.696-59.406-54.493-119.467-54.493 C54.581,22.164,0,98.373,0,183.744c0,63.878,32.211,188.323,247.931,304.064c5.037,2.703,11.098,2.705,16.138,0 C479.79,372.066,512,247.622,512,183.744C512,96.392,455.803,22.164,375.467,22.164z M256,453.348 C152.381,396.376,34.133,301.45,34.133,183.744c0-65.477,39.319-127.446,102.4-127.446c47.857,0,87.452,29.344,104.973,56.973 c6.679,10.743,22.365,10.732,29.017-0.046c0.352-0.569,35.938-56.928,104.944-56.928c63.551,0,102.4,62.591,102.4,127.446 C477.867,301.452,359.622,396.375,256,453.348z"></path> </g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> <g> </g> </svg>'+
					'</span>'+
				'</li>'+
				'<li id="subscribes" data-type="'+type+'" data-id="'+id+'" class="'+results.subscribes.status+'">'+
					'<span tooltip="გამოწერა">'+
						'<svg viewBox="-21 0 512 512" xmlns="http://www.w3.org/2000/svg"> <path d="m453.332031 229.332031c-8.832031 0-16-7.167969-16-16 0-61.269531-23.847656-118.847656-67.15625-162.175781-6.25-6.25-6.25-16.382812 0-22.632812s16.382813-6.25 22.636719 0c49.34375 49.363281 76.519531 115.007812 76.519531 184.808593 0 8.832031-7.167969 16-16 16zm0 0"></path> <path d="m16 229.332031c-8.832031 0-16-7.167969-16-16 0-69.800781 27.179688-135.445312 76.542969-184.789062 6.25-6.25 16.386719-6.25 22.636719 0s6.25 16.386719 0 22.636719c-43.328126 43.304687-67.179688 100.882812-67.179688 162.152343 0 8.832031-7.167969 16-16 16zm0 0"></path> <path d="m234.667969 512c-44.117188 0-80-35.882812-80-80 0-8.832031 7.167969-16 16-16s16 7.167969 16 16c0 26.476562 21.523437 48 48 48 26.472656 0 48-21.523438 48-48 0-8.832031 7.167969-16 16-16s16 7.167969 16 16c0 44.117188-35.882813 80-80 80zm0 0"></path> <path d="m410.667969 448h-352c-20.589844 0-37.335938-16.746094-37.335938-37.332031 0-10.925781 4.757813-21.269531 13.058594-28.375 32.445313-27.414063 50.941406-67.261719 50.941406-109.480469v-59.480469c0-82.34375 66.988281-149.332031 149.335938-149.332031 82.34375 0 149.332031 66.988281 149.332031 149.332031v59.480469c0 42.21875 18.496094 82.066406 50.730469 109.332031 8.511719 7.253907 13.269531 17.597657 13.269531 28.523438 0 20.585937-16.746094 37.332031-37.332031 37.332031zm-176-352c-64.707031 0-117.335938 52.628906-117.335938 117.332031v59.480469c0 51.644531-22.632812 100.414062-62.078125 133.757812-.746094.640626-1.921875 1.964844-1.921875 4.097657 0 2.898437 2.433594 5.332031 5.335938 5.332031h352c2.898437 0 5.332031-2.433594 5.332031-5.332031 0-2.132813-1.171875-3.457031-1.878906-4.054688-39.488282-33.386719-62.121094-82.15625-62.121094-133.800781v-59.480469c0-64.703125-52.628906-117.332031-117.332031-117.332031zm0 0"></path> <path d="m234.667969 96c-8.832031 0-16-7.167969-16-16v-64c0-8.832031 7.167969-16 16-16s16 7.167969 16 16v64c0 8.832031-7.167969 16-16 16zm0 0"></path> </svg>'+
					'</span>'+
				'</li>'
			);
		}
	});
	*/
	
	$(document).delegate('#action_menu li', 'click', function(e) {
		
		e.stopPropagation();
		
		var action		= $(this).attr('id');
		var type		= $(this).data('type');
		var movie_id	= $(this).data('movie_id');
		var id			= $(this).data('id');
		var _this		= $(this);
		
		$.ajax({
			url: '/profile/actions',
			type: 'POST',
			dataType: 'json',
			data: { id:id, movie_id:movie_id, action:action, type:type },
			
		}).done(function(data) {
			
			var collection_items = '';
			
			if(data.status=='get_list'){
				
				
				$.each( data.collections, function( key, collection ) {
					
					collection_items += 
						'<label class="m-0 py-2 overflow-hidden d-flex align-items-center">'+
							'<input class="filter-radio collection_input_check" '+ collection.status +' data-action="'+ action +'" data-type="'+ type +'" data-item="'+ id +'" data-movie_id="'+ movie_id +'" data-id="'+ collection.id +'" id="collection_id" name="collection_id" type="checkbox" value="'+ collection.id +'">'+
							'<div class="filter-custom-radio float-left mr-3"></div>'+
							'<div class="text-inversed arial font-size-14 float-left">'+ collection.name +'</div>'+
						'</label>';
				});
				
				$('#notify').html(
					'<div class="collection-pop-select justify-content-center align-items-center show" id="collectionList">'+
						'<div id="outside_close"></div>'+
						'<div class="collection-pop-in rounded-10 position-relative">'+
							'<div class="popup-head">'+
								'<div class="title">კოლექციაში დამატება</div>'+
								'<div class="closeBtn"><i class="icofont-close"></i></div>'+
							'</div>'+
							'<div class="popup-body">'+
								'<div id="collection_items">'+ collection_items +'</div>'+
							'</div>'+
						'</div>'+
					'</div>'
				);
				
				
				$('#collection_items').delegate('label #collection_id', 'click', function(event) {
					
					var action			= $(this).data('action');
					var type			= $(this).data('type');
					var item_id			= $(this).data('item');
					var movie_id		= $(this).data('movie_id');
					var collection_id	= $(this).data('id');
					
					$.ajax({
						
						url: '/profile/actions',
						type: 'POST',
						dataType: 'json',
						data: { collection_id:collection_id, movie_id:movie_id, action:action, type:type, item_id:item_id },
						
					}).done(function(data) {
						
						if(data.status === 'saved') {
							Notify(data.message);
						}
						
						if(data.status === 'deleted') {
							Notify(data.message,'danger');
						}
						
					})
					
				});
				
			}
			
			if(data.status=='create_list'){
				Notify(data.msg,'danger');
			}
			
			if(data.status === 'saved') {
				$(_this).addClass('active')
				$(_this).find('span').attr('tooltip',data.html)
				Notify(data.message);
			}
			
			if(data.status === 'deleted') {
				$(_this).removeClass('active')
				$(_this).find('span').attr('tooltip',data.html)
				Notify(data.message,'danger');
			}
			
			if(data.errors){
				Notify(data.errors,'danger');
			}
			
		}).fail(function(error) {
			var response = error.responseJSON;
            if( response.errors ) Notify( response.errors ,'danger');
		});
		
	});
	
	

}else{
	
	
	
}







var action = $('.movies-full__inside-rates #stars').data('action');
if(action=='get_rating'){
	
	var action		= $('.movies-full__inside-rates #stars').data('action');
	var id			= $('.movies-full__inside-rates #stars').data('id');
	var type		= $('.movies-full__inside-rates #stars').data('type');
	
	
	$.ajax({
		url: '/profile/rating',
		type: 'POST',
		dataType: 'json',
		data: { id:id, type:type, action:action },
	}).done(function(results) {
		
		$('.movies-full__inside-rates #stars>li').each(function(){
			li = $(this).data('value');
			if(results.my_rating){
				if(li <= results.my_rating){
					$(this).addClass('selected');
				}
			}else{
				if(li <= results.rating){
					$(this).addClass('active');
				}
			}
		});
		
		$('.movies-full__inside-rates .rating_count').text(results.rating);
		$('.movies-full__inside-rates .users_count span').text(results.all_rating);
	});
	
	
	$('.movies-full__inside-rates #stars li').on('mouseover', function(){
		
		var onStar = parseInt($(this).data('value'), 10);

		$(this).parent().children('li.star').each(function(e){
			if (e < onStar) {
				$(this).addClass('hover');
			}else{
				$(this).removeClass('hover');
			}
		});

	}).on('mouseout', function(){
		$(this).parent().children('li.star').each(function(e){
			$(this).removeClass('hover');
		});
	});
	
	
	$('.movies-full__inside-rates #stars li').on('click', function(){
		
		var onStar = parseInt($(this).data('value'), 10);
		var stars = $(this).parent().children('li.star');

		for (i = 0; i < stars.length; i++) {
			$(stars[i]).removeClass('selected');
		}

		for (i = 0; i < onStar; i++) {
			$(stars[i]).addClass('selected');
		}

		var ratingValue = parseInt($('#stars li.selected').last().data('value'), 10);
		var msg = "";
		
		if (ratingValue > 1) {

			msg = "Thanks! You rated this " + ratingValue + " stars.";
			action = 'set_rating';
			$.ajax({
				url: '/profile/rating',
				type: 'POST',
				dataType: 'json',
				data: { id: parseInt(id),type: type, rating: ratingValue, action:action },
			}).done(function(data){
				
				if(data.msg){
					users_count = $('.users_count span').text();
					
					$('.users_count span').html(data.all_rating);
					$('.rating_count').html(data.rating);
					Notify(data.msg);
				}else{
					Notify(data.errors, 'danger');
				}
				
			}).fail(function(error){
				var response = error.responseJSON;
				if( response.errors ) Notify( response.errors ,'danger');
			});

		}
	});

}

var rated_list = $('#rated_list').attr('id');

if(rated_list=='rated_list'){
	
	$("#rated_list #rated_item").each(function() {

		var _this		= $(this);
		var action		= $(this).find('#stars').data('action');
		var id			= $(this).find('#stars').data('id');
		var type		= $(this).find('#stars').data('type');
		
		
		$.ajax({
			url: '/profile/rating',
			type: 'POST',
			dataType: 'json',
			data: { id:id, type:type, action:action },
		}).done(function(results) {
			
			_this.find('.rating_count').text(results.rating);
			_this.find('.user_ratecount span').text(results.all_rating);
			
			
			_this.find('#stars > li').each(function(){
				li = $(this).data('value');
				if(results.rating){
					if(li < results.rating){
						$(this).addClass('selected');
					}else{
						$(this).removeClass('selected');
					}
				}else{
					/* if(li < results.rating){
						$(this).removeClass('selected');
					} */
				}
			});
			
			
		});
		
	});
	
}
