	
	
	var KEYCODE_ENTER = 13;
	var KEYCODE_ESC = 27;

	$(document).keyup(function(e) {
		if(e.keyCode == KEYCODE_ESC){ $('#close').click(); $('.closeBtn').click();};
	});


	$(document).delegate('#notify .closeBtn', 'click', function(event) {
		$('#notify').html('');
		$('body').css('overflow','');
	});

	$(document).delegate('#notify #outside_close', 'click', function(e) {
		$('#notify').html('');
		$('body').css('overflow','');
	});
	
	
	$(document).delegate('#app-popup #close', 'click', function(event) {
		$('#app-popup').remove();
		$('body').css('overflow','');
	});
	
	
	$(document).delegate('#ads', 'click', function(event) {
		
		$('#notify').html(
			'<div class="modal_overlay show">'+
				'<div id="outside_close"></div>'+
				'<div class="modal_box">'+
					'<div class="closeBtn"><i class="icofont-close"></i></div>'+
					'<h1>რეკლამის განთავსება</h1>'+
					'<div class="contact_phone">ტელ: (+995) 511-121-191</div>'+
				'</div>'+
			'</div>'
		);
		
	});

	/////////////////////
	// MAIN SLIDERS
	/////////////////////

	SliderMovie = $('#SliderMovie');

	if (SliderMovie.length > 0) {

	    $.fn.slider = function() {
	        let movie_slide = $('.movie_slide_ithem');
	        let movie_slide_length = $('ul.sliders').children('li').length;
	        var ActiveSlideIndex = 0;
	        var TimerSlide = 10000;
	        var counterUpdated = 0;
	        var _this = $(this);


	        $.each(movie_slide, function(index, element) {
	            $(element).attr('data-index', index);
	        });

	        resizeSlide();
	        let updateSlide = function() {
	            resizeSlide();
	        }




	        var UpdateDataSlide = setInterval(updateSlide, TimerSlide);

	        $('._slider_wrap').hover(function(e) {
	            clearInterval(UpdateDataSlide);
	        }, function(e) {
	            UpdateDataSlide = setInterval(updateSlide, TimerSlide);
	        });


	        $(movie_slide).click(function(e) {

	            e.preventDefault();

	            $(".SliderImage").addClass("load");
	            $(movie_slide).removeClass('active');
	            $(this).addClass('active');
	            ActiveSlideIndex = parseInt($(this).data('index'));
	            resizeSlide();


	        });


	        function resizeSlide() {
	            let ActiveSlide = $(movie_slide[ActiveSlideIndex]);
	            let SliderImage = $('.SliderImage');
	            let SliderIframe = $('.SliderIframe');
	            let SlidetTitle = $('.SlidetTitle');
	            let SliderImdb = $('.SliderImdb');
	            let SlideLink = $('.SlideLink');
	            let addWatching = $('.SlideAddWatching');
	            let GeneresMovie = $('.GeneresMovie');
	            let Image = $(ActiveSlide).attr('data-img');
	            let Iframe = $(ActiveSlide).attr('data-iframe');
	            let Type = $(ActiveSlide).attr('data-type');
	            let Title = $(ActiveSlide).data('title');
	            let Imdb = $(ActiveSlide).data('imdb');
	            let Genres = $(ActiveSlide).data('genres');
	            let Uid = $(ActiveSlide).data('uid');
	            let Link = $(ActiveSlide).data('link');
	            $(movie_slide).removeClass('active')


	            $(movie_slide[ActiveSlideIndex]).addClass('active')
	            if ($(movie_slide[ActiveSlideIndex]).has('active')) {

	                if (Type == 'iframe') {


	                    $('.hero-slider__info').css({'display':'none'});
	                    $('.movie-overlay').addClass('iframe_movie_overlay');
	                    $('.slideritems').removeClass('col-md-6');
	                    $('.main-overlay').removeClass('overlay');

	                    $(SliderIframe).attr('src', Iframe).css('display', 'block');
						
						$(SliderIframe).closest('.hero-slider__info').css('width', '100%')
						
	                } else {


	                    $(SliderIframe).attr('src', '').css('display', 'none');
	                    $(SlidetTitle).html(Title);
	                    $(SliderImage).attr('src', Image);
	                    $(SliderImdb).html(Imdb);
	                    $(GeneresMovie).html(Genres);
	                    $(SlideLink).attr('href', Link);
	                    $('.InfoWrappSlider').attr('data-href', Link);
	                    $('.hero-slider__info').css({'display':'block'}).attr('onclick', 'location.href=\'' + Link + '\';');

	                }
	            }

	            if (ActiveSlideIndex < movie_slide_length - 1) {
	                ActiveSlideIndex += 1;
	            } else if (ActiveSlideIndex >= movie_slide_length - 1) {
	                ActiveSlideIndex = 0;
	            }

	        }



	    }

	    $('#SliderMovie').slider();

	}





	/////////////////////
	// SWIPER SLIDERS
	/////////////////////
	var block_christmas = new Swiper('#block_christmas .swiper-container', {
	    slidesPerView: 5,
	    spaceBetween: 30,
	    slidesPerGroup: 5,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_christmas .next-slide',
	        prevEl: '#block_christmas .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 16,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 14,
	        },
	        2560: {
	            slidesPerView: 9,
	            spaceBetween: 30,
	            slidesPerGroup: 8,
	        },
	        1920: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1680: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1440: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1366: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_geomovies = new Swiper('#block_geomovies .swiper-container', {
	    slidesPerView: 5,
	    spaceBetween: 30,
	    slidesPerGroup: 5,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_geomovies .next-slide',
	        prevEl: '#block_geomovies .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 16,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 14,
	        },
	        2560: {
	            slidesPerView: 9,
	            spaceBetween: 30,
	            slidesPerGroup: 9,
	        },
	        1920: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1680: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1440: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1366: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_latestmovies = new Swiper('#block_latestmovies .swiper-container', {
	    slidesPerView: 5,
	    spaceBetween: 30,
	    slidesPerGroup: 5,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_latestmovies .next-slide',
	        prevEl: '#block_latestmovies .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 16,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 14,
	        },
	        2560: {
	            slidesPerView: 9,
	            spaceBetween: 30,
	            slidesPerGroup: 9,
	        },
	        1920: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1680: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1440: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1366: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_watching = new Swiper('#block_watching .swiper-container', {
	    slidesPerView: 4,
	    spaceBetween: 15,
	    slidesPerGroup: 4,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_watching .next-slide',
	        prevEl: '#block_watching .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 8,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 8,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup:6,
	        },
	        2560: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1920: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1680: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1440: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        1366: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        1260: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 2,
	            spaceBetween: 30,
	            slidesPerGroup: 2,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_geoseries = new Swiper('#block_geoseries .swiper-container', {
	    slidesPerView: 5,
	    spaceBetween: 30,
	    slidesPerGroup: 5,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_geoseries .next-slide',
	        prevEl: '#block_geoseries .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 7,
	        },
	        2560: {
	            slidesPerView: 9,
	            spaceBetween: 30,
	            slidesPerGroup: 9,
	        },
	        1920: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1680: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1440: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1366: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_latestseries = new Swiper('#block_latestseries .swiper-container', {
	    slidesPerView: 5,
	    spaceBetween: 30,
	    slidesPerGroup: 5,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_latestseries .next-slide',
	        prevEl: '#block_latestseries .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 7,
	        },
	        2560: {
	            slidesPerView: 9,
	            spaceBetween: 30,
	            slidesPerGroup: 9,
	        },
	        1920: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1680: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1440: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1366: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_dubbed = new Swiper('#block_dubbed .swiper-container', {
	    slidesPerView: 5,
	    spaceBetween: 30,
	    slidesPerGroup: 3,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_dubbed .next-slide',
	        prevEl: '#block_dubbed .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 7,
	        },
	        2560: {
	            slidesPerView: 9,
	            spaceBetween: 30,
	            slidesPerGroup: 9,
	        },
	        1920: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1680: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1440: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1366: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 3,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_turkish = new Swiper('#block_turkish .swiper-container', {
	    slidesPerView: 5,
	    spaceBetween: 30,
	    slidesPerGroup: 5,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_turkish .next-slide',
	        prevEl: '#block_turkish .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 7,
	        },
	        2560: {
	            slidesPerView: 9,
	            spaceBetween: 30,
	            slidesPerGroup: 9,
	        },
	        1920: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1680: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        1440: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1366: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});

	var block_soon = new Swiper('#block_soon .swiper-container', {
	    slidesPerView: 4,
	    spaceBetween: 20,
	    slidesPerGroup: 4,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_soon .next-slide',
	        prevEl: '#block_soon .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 3,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 3,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        2560: {
	            slidesPerView: 7,
	            spaceBetween: 15,
	            slidesPerGroup: 7,
	        },
	        1920: {
	            slidesPerView: 6,
	            spaceBetween: 15,
	            slidesPerGroup: 6,
	        },
	        1680: {
	            slidesPerView: 5,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1440: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 3,
	        },
	        1366: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        1260: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 3,
	        },
	        1024: {
	            slidesPerView: 3,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 3,
	            spaceBetween: 30,
	            slidesPerGroup: 3,
	        },
	        460: {
	            slidesPerView: 1,
	            spaceBetween: 30,
	            slidesPerGroup: 1,
	        },
	    }
	});
	
	
	var block_cinemas = new Swiper('#block_cinemas .swiper-container', {
	    slidesPerView: 6,
	    spaceBetween: 20,
	    slidesPerGroup: 6,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_cinemas .next-slide',
	        prevEl: '#block_cinemas .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 16,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 14,
	            spaceBetween: 30,
	            slidesPerGroup: 7,
	        },
	        2560: {
	            slidesPerView: 11,
	            spaceBetween: 30,
	            slidesPerGroup: 11,
	        },
			2000: {
	            slidesPerView: 10,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        1920: {
	            slidesPerView: 8,
	            spaceBetween: 25,
	            slidesPerGroup: 9,
	        },
	        1600: {
	            slidesPerView: 8,
	            spaceBetween: 10,
	            slidesPerGroup: 8,
	        },
	        1440: {
	            slidesPerView: 7,
	            spaceBetween: 10,
	            slidesPerGroup: 7,
	        },
	        1366: {
	            slidesPerView: 6,
	            spaceBetween: 8,
	            slidesPerGroup: 6,
	        },
	        1260: {
	            slidesPerView: 5,
	            spaceBetween: 35,
	            slidesPerGroup: 6,
	        },
	        1024: {
	            slidesPerView: 4,
	            spaceBetween: 50,
	            slidesPerGroup: 4,
	        },
	        768: {
	            slidesPerView: 4,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        460: {
	            slidesPerView: 4,
	            spaceBetween: 30,
	            slidesPerGroup: 4,
	        },
	    }
	    
	});

	var block_persons = new Swiper('#block_persons .swiper-container', {
	    slidesPerView: 10,
	    spaceBetween: 15,
	    slidesPerGroup: 10,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#block_persons .next-slide',
	        prevEl: '#block_persons .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 50,
	            spaceBetween: 15,
	            slidesPerGroup: 50,
	        },
	        4096: {
	            slidesPerView: 30,
	            spaceBetween: 15,
	            slidesPerGroup: 30,
	        },
	        3840: {
	            slidesPerView: 25,
	            spaceBetween: 30,
	            slidesPerGroup: 25,
	        },
	        2560: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 20,
	        },
	        1920: {
	            slidesPerView: 15,
	            spaceBetween: 15,
	            slidesPerGroup: 15,
	        },
	        1680: {
	            slidesPerView: 13,
	            spaceBetween: 15,
	            slidesPerGroup: 13,
	        },
	        1440: {
	            slidesPerView: 10,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        1366: {
	            slidesPerView: 10,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        1260: {
	            slidesPerView: 10,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        1024: {
	            slidesPerView: 8,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        768: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        460: {
	            slidesPerView: 4,
	            spaceBetween: 30,
	            slidesPerGroup: 4,
	        },
	    }
	});

	var movie_actors = new Swiper('#movie_actors .swiper-container', {
	    slidesPerView: 10,
	    spaceBetween: 15,
	    slidesPerGroup: 10,
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#movie_actors .next-slide',
	        prevEl: '#movie_actors .prev-slide',
	    },
	    breakpoints: {
	        5100: {
	            slidesPerView: 50,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        4096: {
	            slidesPerView: 30,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        3840: {
	            slidesPerView: 25,
	            spaceBetween: 30,
	            slidesPerGroup: 7,
	        },
	        2560: {
	            slidesPerView: 20,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        1920: {
	            slidesPerView: 15,
	            spaceBetween: 15,
	            slidesPerGroup: 4,
	        },
	        1680: {
	            slidesPerView: 12,
	            spaceBetween: 15,
	            slidesPerGroup: 5,
	        },
	        1440: {
	            slidesPerView: 10,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        1366: {
	            slidesPerView: 10,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        1260: {
	            slidesPerView: 10,
	            spaceBetween: 15,
	            slidesPerGroup: 10,
	        },
	        1024: {
	            slidesPerView: 8,
	            spaceBetween: 15,
	            slidesPerGroup: 8,
	        },
	        768: {
	            slidesPerView: 6,
	            spaceBetween: 30,
	            slidesPerGroup: 6,
	        },
	        460: {
	            slidesPerView: 4,
	            spaceBetween: 30,
	            slidesPerGroup: 4,
	        },
	    }
	});

	
	/////////////////////
	// BLOCK BACKGROUNDS
	/////////////////////
	
	//var list = document.querySelectorAll(".bg-image");
	/* 
	for (var i = 0; i < list.length; i++) {
	    var url = list[i].getAttribute('data-bg');
	    list[i].style.backgroundImage = "url('" + url + "')";
	}
	*/
	
	$block_dubbed = $('#block_dubbed');
	$hover_block_dubbed = $('#block_dubbed .movie-card img').hover(function() {
	    $block_dubbed.css('background-image', 'url(' + $(this).attr('bg') + ')');
	});
	
	$block_cinemas = $('#block_cinemas');
	$hover_block_soon = $('#block_cinemas .movie-card img').hover(function() {
	    $block_cinemas.css('background-image', 'url(' + $(this).attr('bg') + ')');
	});
	
	
	
	$block_soon = $('#block_soon');
	$hover_block_soon = $('#block_soon .movie-card img').hover(function() {
	    $block_soon.css('background-image', 'url(' + $(this).attr('bg') + ')');
	});
	
	$block_soon = $('#block_soon');
	$hover_block_soon = $('.soon-item__img img').hover(function() {
	    $block_soon.css('background-image', 'url(' + $(this).attr('bg') + ')');
	});
	
	first_block_soon = $('.soon-item__img img')[0];
	$('#block_soon').css('background-image', 'url(' + $(first_block_soon).attr('bg') + ')');
	
	first_block_dubbed = $('#block_dubbed .movie-card img')[0];
	$('#block_dubbed').css('background-image', 'url(' + $(first_block_dubbed).attr('bg') + ')');
	
	first_movies_full = $('#movies-full .bg-image').attr('data-bg');
	$('#movies-full .bg-image').css('background-image', 'url(' + first_movies_full + ')');
	
	

	var movie_related = new Swiper('#movie_related .swiper-container', {
	    slidesPerView: 2,
	    spaceBetween: 20,
	    slidesPerGroup: 2,
	    slidesPerColumn: 2,
	    slidesPerColumnFill: 'row',
	    loop: false,
	    lazy: true,
	    navigation: {
	        nextEl: '#movie_related .next-slide',
	        prevEl: '#movie_related .prev-slide',
	    },
	});


	


	/////////////////////
	// LOAD SELECT 2
	/////////////////////
	$(".dropdown-toggle").click(function(e) {
	    e.preventDefault();
	    e.stopPropagation();
	    if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
	    var $el = $(this).parents(".filter-item").find(".dropdown-menu").first();
	    var wasOpen = $el.hasClass('show');
	    $(".dropdown-menu").removeClass('show');
	    if (!wasOpen) {
	        $el.addClass('show');
	    }
	});

	const $dropdown = $(".dropdown-menu");

	$(document).mouseup(function(e) {
	    var $target = $(e.target);
	    var clickedInsideMenu = $dropdown.is(e.target) || $dropdown.has(e.target).length > 0;
	    var clickedToggle = $target.closest('.dropdown-toggle').length > 0;
	    if (!clickedInsideMenu && !clickedToggle) {
	        $dropdown.removeClass('show');
	    }

	});




	/////////////////////
	// NOTIFY
	/////////////////////
	Notify = function(text, style) {

	    var time = '100000';
	    var $container = $('#notify');
	    var icon = '<i class="fa fa-info-circle "></i>';

	    if (typeof style == 'undefined') style = 'success'

	    var html = $('<div class="notif_alert notif_' + style + '  hide"><p>' + text + '</p></div>');

	    $('<a>', {
	        text: '×',
	        class: 'button close',
	        style: 'padding-left: 10px;',
	        href: '#',
	        click: function(e) {
	            e.preventDefault()
	            remove_notice()
	        }
	    }).prependTo(html)

	    $container.prepend(html)
	    html.removeClass('hide').hide().fadeIn('slow')

	    function remove_notice() {
	        html.stop().fadeOut('slow').remove()
	    }

	    var timer = setInterval(remove_notice, 3000);

	    $(html).hover(function() {
	        clearInterval(timer);
	    }, function() {
	        timer = setInterval(remove_notice, time);
	    });

	    html.on('click', function() {
	        clearInterval(timer)
	        remove_notice()
	    });

	}

	

	/////////////////////////
	// POPULAR MOVIES FILTERS
	/////////////////////////
	$('.popular_filter').click(function(e) {
	    e.preventDefault();
	    var FilterType = $(this).data('type');
	    $('.popular_filter').removeClass('active');
	    $(this).addClass('active');
	    $.ajax({
	            url: '/Api/WebService/popular_movies/' + FilterType,
	            type: 'POST',
	            dataType: 'json',
	            data: { filter: FilterType },
	        }).done(function(data) {
	            if (data[0]) {
	                $('#popular_movie_list').empty();
	                $.each(data, function(index, popular_movies) {
	                    console.log(popular_movies);
						poster = popular_movies.poster
						backdrop = popular_movies.backdrop
	                    title_en = popular_movies.original_title;
	                    title_ge = popular_movies.name;
						certification = popular_movies.certification ? '<div class="certification" data-sert="'+popular_movies.certification+'">'+popular_movies.certification+'</div>':'';
						
						
	                    $('#popular_movie_list').append(

	                        '<div class="col-md-3">' +
	                        '<div class="popular-card">' +
	                        '<div class="popular-card__img">' +
	                        '<img src="' + backdrop + '" class="lazy_load">' +
	                        '<div class="play">' +
	                        '<a href="/movie/' + popular_movies.id + '/' + TitleSlug(title_en) + '" title=""><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 265.4 265.4"><style>.a{fill:#000002;}</style><path d="M194.2 123.7l-78.1-51.1c-1.9-1.3-4-1.9-6.1-1.9 -5.5 0-9.7 4.5-9.7 10.5v103.2c0 6 4.2 10.5 9.7 10.5 2.1 0 4.2-0.7 6.1-1.9l78.1-51.1c3.3-2.1 5.1-5.4 5.1-9C199.3 129.1 197.4 125.8 194.2 123.7zM115.3 175.4V90l65.3 42.7L115.3 175.4z" class="a"/><path d="M132.7 0C59.5 0 0 59.5 0 132.7c0 73.2 59.5 132.7 132.7 132.7s132.7-59.5 132.7-132.7C265.4 59.5 205.9 0 132.7 0zM132.7 250.4C67.8 250.4 15 197.6 15 132.7 15 67.8 67.8 15 132.7 15s117.7 52.8 117.7 117.7C250.4 197.6 197.6 250.4 132.7 250.4z" class="a"/></svg></a>' +
	                        '</div>' +
	                        '<div class="rates">' +
	                        '<div class="imdb">' +
	                        '<svg version="1.0" xmlns="http://www.w3.org/2000/svg" width="1521.000000pt" height="801.000000pt" viewBox="0 0 1521.000000 801.000000" preserveAspectRatio="xMidYMid meet"> <g transform="translate(0.000000,801.000000) scale(0.100000,-0.100000)" fill="#000000" stroke="none"> <path d="M734 7989 c-150 -14 -319 -86 -439 -186 -116 -97 -225 -279 -262 -438 -17 -77 -18 -210 -18 -3365 0 -3724 -9 -3352 85 -3545 105 -214 291 -365 530 -428 l85 -22 6895 0 6895 0 85 22 c296 78 515 297 593 593 l22 85 0 3290 c0 3160 -1 3293 -18 3370 -37 159 -146 341 -262 438 -125 105 -285 171 -452 187 -120 12 -13619 11 -13739 -1z m13851 -423 c77 -38 153 -114 191 -191 l29 -60 0 -3315 0 -3315 -29 -60 c-38 -77 -114 -153 -191 -191 l-60 -29 -6915 0 -6915 0 -60 29 c-77 38 -153 114 -191 191 l-29 60 0 3315 0 3315 27 55 c51 103 141 184 241 215 35 11 1230 13 6942 12 l6900 -2 60 -29z"/> <path d="M10410 4200 l0 -2200 400 0 400 0 0 100 0 100 78 -39 c277 -138 483 -181 633 -131 187 63 353 228 423 422 62 170 59 119 63 1233 5 1077 -1 1273 -37 1425 -55 224 -191 387 -379 452 -55 19 -87 23 -191 23 l-125 0 -85 -41 c-109 -53 -184 -110 -293 -223 l-87 -90 0 584 0 585 -400 0 -400 0 0 -2200z m1106 575 c26 -15 54 -43 69 -69 l25 -43 0 -858 c0 -857 0 -859 -21 -903 -33 -67 -94 -102 -178 -102 -81 0 -139 31 -176 94 l-25 43 0 863 0 863 25 43 c37 63 94 94 174 94 51 0 73 -5 107 -25z"/> <path d="M2810 4000 l0 -2000 400 0 400 0 0 2000 0 2000 -400 0 -400 0 0 -2000z"/> <path d="M4010 4000 l0 -2000 400 0 400 0 2 1402 3 1402 360 -1402 360 -1402 249 2 248 3 387 1399 386 1399 3 -1401 2 -1402 400 0 400 0 0 2000 0 2000 -597 0 -598 0 -304 -1015 c-168 -557 -307 -1012 -311 -1010 -3 2 -138 458 -300 1014 l-295 1011 -597 0 -598 0 0 -2000z"/> <path d="M8010 3999 l0 -2002 528 6 c290 4 566 11 614 17 203 23 334 62 473 142 162 92 249 177 310 303 74 153 70 60 70 1505 0 1211 -1 1300 -18 1379 -33 153 -100 285 -187 370 -51 50 -262 184 -332 212 -29 11 -84 27 -123 35 -89 18 -522 33 -982 34 l-353 0 0 -2001z m1001 1372 c75 -29 132 -80 166 -149 l28 -57 0 -1175 0 -1175 -27 -51 c-52 -99 -130 -141 -280 -151 l-88 -6 0 1398 0 1398 73 -5 c39 -3 97 -15 128 -27z"/> </g> </svg>' +
	                        '<span>' + popular_movies.tmdb_vote_average + '</span>' +
	                        '</div>' +
	                        '<div class="year">' + popular_movies.year + ' წ</div>' +
	                        '</div>' +
	                        '<div class="actions">' +
	                        certification +
	                        '<div class="audio_langs"><span>GEO</span></div>' +
	                        '</div>' +
	                        '</div>' +
	                        '<div class="popular-card__title">' +
	                        '<h2>' +
	                        '<a href="/movie/' + popular_movies.id + '/' + TitleSlug(title_en) + '">' +
	                        '<p>' + title_ge + '</p>' +
	                        '<span>' + title_en + '</span>' +
	                        '</a>' +
	                        '</h2>' +
	                        '<button class="additionals" id="items_menu" data-type="movie" data-id="' + popular_movies.id + '" data-movie_id="' + popular_movies.movie_id + '">' +
	                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 384"><circle cx="192" cy="42.7" r="42.7"/><circle cx="192" cy="192" r="42.7"/><circle cx="192" cy="341.3" r="42.7"/></svg>' +
	                        '<div id="toogle-menu"></div>' +
	                        '</button>' +
	                        '</div>' +
	                        '</div>' +
	                        '</div>'
	                    );
	                });
	            }
	        })
	        .fail(function() {
	            //console.log("error");
	        })
	        .always(function() {
	            //console.log("complete");
	        });

	});


	/////////////////////////
	// POPULAR MOVIES FILTERS
	/////////////////////////
	$('.popular_filter_serial').click(function(e) {
	    e.preventDefault();
	    var FilterType = $(this).data('type');
	    $('.popular_filter_serial').removeClass('active');
	    $(this).addClass('active');
	    $.ajax({
	            url: '/Api/WebService/popular_serials/' + FilterType,
	            type: 'POST',
	            dataType: 'json',
	            data: { filter: FilterType },
	        }).done(function(data) {
	            if (data[0]) {
	                $('#popular_serial_list').empty();
	                $.each(data, function(index, popular_serials) {
	                    console.log(popular_serials);

	                    poster = popular_serials.poster
						backdrop = popular_serials.backdrop
	                    title_en = popular_serials.original_title;
	                    title_ge = popular_serials.name;

	                    $('#popular_serial_list').append(
	                        '<div class="col-md-3">' +
	                        '<div class="serials-card">' +
	                        '<div class="serials-card__img">' +
	                        '<a href="/serial/' + popular_serials.id + '/' + TitleSlug(title_en) + '">' +
	                        '<figure>' +
	                        '<div class="imdb">' +
	                        '<svg version="1.0" xmlns="http://www.w3.org/2000/svg" width="1521.000000pt" height="801.000000pt" viewBox="0 0 1521.000000 801.000000" preserveAspectRatio="xMidYMid meet"> <g transform="translate(0.000000,801.000000) scale(0.100000,-0.100000)" fill="#000000" stroke="none"> <path d="M734 7989 c-150 -14 -319 -86 -439 -186 -116 -97 -225 -279 -262 -438 -17 -77 -18 -210 -18 -3365 0 -3724 -9 -3352 85 -3545 105 -214 291 -365 530 -428 l85 -22 6895 0 6895 0 85 22 c296 78 515 297 593 593 l22 85 0 3290 c0 3160 -1 3293 -18 3370 -37 159 -146 341 -262 438 -125 105 -285 171 -452 187 -120 12 -13619 11 -13739 -1z m13851 -423 c77 -38 153 -114 191 -191 l29 -60 0 -3315 0 -3315 -29 -60 c-38 -77 -114 -153 -191 -191 l-60 -29 -6915 0 -6915 0 -60 29 c-77 38 -153 114 -191 191 l-29 60 0 3315 0 3315 27 55 c51 103 141 184 241 215 35 11 1230 13 6942 12 l6900 -2 60 -29z"/> <path d="M10410 4200 l0 -2200 400 0 400 0 0 100 0 100 78 -39 c277 -138 483 -181 633 -131 187 63 353 228 423 422 62 170 59 119 63 1233 5 1077 -1 1273 -37 1425 -55 224 -191 387 -379 452 -55 19 -87 23 -191 23 l-125 0 -85 -41 c-109 -53 -184 -110 -293 -223 l-87 -90 0 584 0 585 -400 0 -400 0 0 -2200z m1106 575 c26 -15 54 -43 69 -69 l25 -43 0 -858 c0 -857 0 -859 -21 -903 -33 -67 -94 -102 -178 -102 -81 0 -139 31 -176 94 l-25 43 0 863 0 863 25 43 c37 63 94 94 174 94 51 0 73 -5 107 -25z"/> <path d="M2810 4000 l0 -2000 400 0 400 0 0 2000 0 2000 -400 0 -400 0 0 -2000z"/> <path d="M4010 4000 l0 -2000 400 0 400 0 2 1402 3 1402 360 -1402 360 -1402 249 2 248 3 387 1399 386 1399 3 -1401 2 -1402 400 0 400 0 0 2000 0 2000 -597 0 -598 0 -304 -1015 c-168 -557 -307 -1012 -311 -1010 -3 2 -138 458 -300 1014 l-295 1011 -597 0 -598 0 0 -2000z"/> <path d="M8010 3999 l0 -2002 528 6 c290 4 566 11 614 17 203 23 334 62 473 142 162 92 249 177 310 303 74 153 70 60 70 1505 0 1211 -1 1300 -18 1379 -33 153 -100 285 -187 370 -51 50 -262 184 -332 212 -29 11 -84 27 -123 35 -89 18 -522 33 -982 34 l-353 0 0 -2001z m1001 1372 c75 -29 132 -80 166 -149 l28 -57 0 -1175 0 -1175 -27 -51 c-52 -99 -130 -141 -280 -151 l-88 -6 0 1398 0 1398 73 -5 c39 -3 97 -15 128 -27z"/> </g> </svg>' +
	                        '<span>' + popular_serials.tmdb_vote_average + '</span>' +
	                        '</div>' +
	                        '<img src="' + backdrop + '" class="lazy_load">' +
	                        '<div class="title">' +
	                        '<h2>' + title_ge + '</br><p>' + title_en + '</p></h2>' +
	                        '<span>GEO</span>' +
	                        '</div>' +
	                        '</figure>' +
	                        '</a>' +
	                        '</div>' +
	                        '<div class="serials-card__info">' +
	                        '<div class="episodes">' +
	                        '<ul>' +
	                        '<li>'+popular_serials.season_count+' სეზონი</li>' +
	                        '<li>ეპიზოდი '+popular_serials.episode_count+'</li>' +
	                        '</ul>' +
	                        '</div>' +
	                        '<button class="additionals" id="items_menu" data-type="serial" data-id="' + popular_serials.id + '" data-serial_id="' + popular_serials.id + '">' +
	                        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 384 384"><circle cx="192" cy="42.7" r="42.7"/><circle cx="192" cy="192" r="42.7"/><circle cx="192" cy="341.3" r="42.7"/></svg>' +
	                        '<div id="toogle-menu"></div>' +
	                        '</button>' +
	                        '</div>' +
	                        '</div>' +
	                        '</div>'
	                    );
	                });
	            }
	        })
	        .fail(function() {
	            //console.log("error");
	        })
	        .always(function() {
	            //console.log("complete");
	        });

	});



	/////////////////////////
	// POPULAR COLLECTIONS FILTERS
	/////////////////////////
	$('.collection_filter').click(function(e) {
	    e.preventDefault();
	    var FilterType = $(this).data('type');
	    $('.collection_filter').removeClass('active');
	    $(this).addClass('active');
	    $.ajax({
	            url: '/Api/WebService/collections/6/' + FilterType,
	            type: 'POST',
	            dataType: 'json',
	            data: { filter: FilterType },
	        }).done(function(data) {
	            if (data.total > 0) {
	                $('#collection_list').empty();
	                $.each(data.response, function(index, filter_collections) {
						
						
	                    
						
						let coll_titles = filter_collections.titles;
						let collection = filter_collections.collection;
						
						let owner_image = collection.owner_thumb ? collection.owner_thumb : avatars[collection.owner_sex];
						let owner_avatar = owner_image ? collection.owner_avatar : avatars[collection.owner_sex];

	                    $('#collection_list').append(
	                        '<div class="col-md-4">' +
	                        '<div class="collections-card">' +
	                        '<a href="/collection/' + collection.id + '" class="collections-card__img">' +
	                        '<figure>' + 
	                        '<picture><img src="' + coll_titles[0].poster + '" alt="' + coll_titles[0].name + ' ' + coll_titles[0].original_title + '" class="lazy_load"></picture>' +
	                        '<picture><img src="' + coll_titles[1].poster + '" alt="' + coll_titles[0].name + ' ' + coll_titles[0].original_title + '" class="lazy_load"></picture>' +
	                        '<picture><img src="' + coll_titles[2].poster + '" alt="' + coll_titles[0].name + ' ' + coll_titles[0].original_title + '" class="lazy_load"></picture>' +
	                        '</figure>' +
	                        '</a>' +
	                        '<div class="collections-card__desc">' +
	                        '<a href="/collection/' + collection.id + '" class="collections-card__desc-title">' +
	                        '<h2>' + collection.name + '</h2>' +
	                        '</a>' +
	                        '<div class="collections-card__desc-author">' +
	                        '<a href="/user/watch_later/' + collection.customer_id + '">' +
	                        '<figure>' +
	                        '<img src="' + owner_avatar + '" alt="">' +
	                        '</figure>' +
	                        '<h3>' + collection.owner_first_name + ' ' + collection.owner_last_name + '</h3>' +
	                        '</a>' +
	                        '</div>' +
	                        '<div class="collections-card__desc-actions">' +
	                        '<span>' + collection.count_titles + ' ფილმი</span>' +
	                        '<p>' + collection.count_subscribers + ' გამომწერი</p>' +
	                        '</div>' +
	                        '</div>' +
	                        '</div>' +
	                        '</div>'
	                    );
	                });
	            }
	        })
	        .fail(function() {
	            console.log("error");
	        })
	        .always(function() {
	            console.log("complete");
	        });

	});

	$(document).ready(function() {
	    $('#show-down').click(function(event) {
	        event.stopPropagation();
	        $("#statuses").toggleClass("active");
	        event.preventDefault();

	    });
	    $("#show-down").on("click", function(event) {
	        event.stopPropagation();
	        event.preventDefault();
	    });
	});

	$(document).on("click", function() {
	    $("#statuses").removeClass("active");
	});


	/////////////////////////
	// ADDITIONAL FUNCTIONS
	/////////////////////////
	function TitleSlug(Text) {
	    return Text
	        .toLowerCase()
	        .replace(/[^\w ]+/g, '')
	        .replace(/ +/g, '-');
	}


	/////////////////////////
	// FILTER AND SEARCH
	/////////////////////////





var filter_si;
filter_si = document.getElementById("filter_si");

if (filter_si != null) {
	filter_si.addEventListener("input", filter_titles);

	function filter_titles(e) {
	  var filter = e.target.value.toUpperCase();

	  var list_titles = document.getElementById("list_titles");
	  var divs = list_titles.getElementsByClassName("col-md-3");
	  for (var i = 0; i < divs.length; i++) {
		var title_name = divs[i].getElementsByClassName("popular-card__title")[0];
		
		if (title_name) {
		  if (title_name.innerHTML.toUpperCase().indexOf(filter) > -1) {
			divs[i].style.display = "";
		  } else {
			divs[i].style.display = "none";
		  }
		}       
	  }

	}
}












































	
	




	function open_video(video_id, referar_url) {

	    var request = $.ajax({
	        url: '/home/video_modal/' + video_id,
	        type: 'get',
	        dataType: 'html'
	    });

	    $('#video_modal').show().html('<div>Loading...</div>');

	    request.done(function(data) {
	        window.history.replaceState({ state: 'new' }, '', '/video/' + video_id);
	        $('#video_modal').html(data);
	    });

	    request.fail(function(jqXHR, textStatus) {
	        console.log('Sorry: ' + textStatus);
	    });

	    $('body').css({ 'overflow': 'hidden' });

	}

	$("#video_modal").on("click", "#close", function() {
	    //$( this ).toggleClass( "chosen" );
	    $('body').css({ 'overflow': 'visible' });
	    $('#video_modal').hide();
	    $('#video_modal').html('');
	    window.history.replaceState({ state: 'new' }, '', '/videos');
	});



	$('.popap_contact').click(function(e) {
	    e.preventDefault();
	    var DataIDPoPup = $(this).data('id');
	    var PoPup = $('#' + DataIDPoPup).show();
	});

	$('#ContactPopup .closeBtn').click(function(event) {
	    $('#ContactPopup').hide();
	});



	$('#triler_popup').click(function(event) {
	    event.preventDefault();

	    var url = $(this).data('url');
	    var title = $(this).data('title');

	    $('#notify').html(
	        '<div class="video-overlay" style="display: block;">' +
	        '<div class="video-overlay-cont">' +
	        '<div id="outside_close"></div>' +
	        '<div class="video-overlay-in overflow-hidden">' +
	        '<div class="problem-head d-flex position-relative">' +
	        '<div class="closeBtn"><i class="icofont-close"></i></div>' +
	        '<div class="d-flex flex-column"><h1 class="arial-caps video-overlay-title text-main mb-1">' + title + '</h1></div>' +
	        '</div>' +
	        '<div class="problem-body">' +
	        '<iframe src="' + url + '" id="video_cinema" width="100%" height="355px" frameborder="0"></iframe>' +
	        '</div>' +
	        '</div>' +
	        '</div>' +
	        '</div>'
	    );
	});
	
	
	



	$('#create_collection').click(function(e) {
	    e.preventDefault();

	    $('#notify').html(
	        '<div class="collection-pop create show">' +
	        '<div id="outside_close"></div>' +
	        '<div class="collection-pop-in rounded-10 position-absolute">' +
	        '<div class="popup-head"><div class="title">ახალი კოლექცია</div><div class="closeBtn"><i class="icofont-close"></i></div></div>' +
	        '<div class="popup-body">' +
	        '<form class="d-flex flex-column align-items-end mt-3" id="addCollection" method="post">' +
	        '<div class="flex-grow-1"></div>' +
	        '<input id="collName" class="authorization-input mb-4 font-size-14 arial text-gray rounded-10 w-100" placeholder="კოლექციის სათაური" name="name">' +
	        '<div class="coll-pop-btns">' +
	        '<button class="save-btn btn" title="დამახსოვრება" type="submit">დამახსოვრება</button>' +
	        '</div>' +
	        '<div class="flex-grow-1"></div>' +
	        '</form>' +
	        '</div>' +
	        '</div>' +
	        '</div>'
	    );


	});



	$(document).ready(function() {
	    $('.PublishBtn').click(function(event) {
	        event.stopPropagation();
	        $(".selectStatus").toggle();
	    });
	    $(".selectStatus").on("click", function(event) {
	        event.stopPropagation();
	    });
	});

	$(document).on("click", function() {
	    $(".selectStatus").hide();
	});


	$('.change-status li').click(function(event) {
	    var coll_id = $(this).data('id');
	    var select_id = $(this).data('select');
	    var $_col_status = $(this).parent().parent().find('.coll_status');

	    $.post('/profile/collection_actions', { id: coll_id, status: select_id, action: 'status' }, function(response) {

	        if (response.id == 0) {
	            $_col_status.html('<i class="icofont-lock"></i> <span>პირადი <i class="icofont-thin-down"></i>');
	            Notify(response.msg, 'danger');
	        }
	        if (response.id == 1) {
	            $_col_status.html('<i class="icofont-globe"></i> <span>საჯარო <i class="icofont-thin-down"></i>');
	            Notify(response.msg);
	        }
	        $(".selectStatus").hide();
	    });
	});


	function deleteCollection(id) {

	    if (confirm("ნამდვილად გსურთ კოლექციის წაშლა?")) {

	        $.ajax({
	                url: "/profile/collection_actions",
	                type: 'POST',
	                dataType: 'json',
	                data: { id: id, action: 'delete' },
	            })
	            .done(function(results) {

	                if (results.status == true) {
	                    Notify(results.msg);
	                    setTimeout(function() { location.reload(); }, 1000);
	                }
	                if (results.errors) {
	                    Notify(results.errors, 'danger');
	                }

	            });

	    }
	    return false;
	}
	
	$(document).delegate('#unsubscribe_collection', 'click', function(event) {
	    if (confirm("ნამდვილად გსურთ გამოწერის გაუქმება?")) {

	        var coll_id = $(this).data('id');
			var action = 'unsubscribe';
			
			$.ajax({
				url: "/profile/collection_actions",
				type: 'POST',
				dataType: 'json',
				data: { id: coll_id, action: action, },
			}).done(function(results) {

				if (results.status == true) {
					Notify(results.msg);
					remove_item(coll_id);
				}
				if (results.errors) {
					Notify(results.errors, 'danger');
				}

			});

	    }
	    return false;
		
	});
	
	$(document).delegate('.collection-pop.create', 'submit', function(event) {
	    event.preventDefault();

	    var name = $('#collName').val();


	    $.ajax({
			url: "/profile/collection_actions",
			type: 'POST',
			dataType: 'json',
			data: { name: name },
		})
		.done(function(results) {

			if (results.status == true) {
				Notify(results.msg);
				setTimeout(function() { window.location = '/collection/' + results.id; }, 1000);
			}
			if (results.errors) {
				Notify(results.errors, 'danger');
			}

		});


	});




	$('.EditNameCollectionButton').click(function(event) {

	    var coll_id = $(this).data('id');
	    var coll_name = $(this).data('name');
		
		$('#notify').html(
	        '<div class="collection-pop show">' +
	        '<div id="outside_close"></div>' +
	        '<div class="collection-pop-in rounded-10 position-absolute">' +
	        '<div class="popup-head"><div class="title">კოლექციის დასახელება</div><div class="closeBtn"><i class="icofont-close"></i></div></div>' +
	        '<div class="popup-body">' +
				'<form id="ChangeNameCollection" data-id="' + coll_id + '" method="post" autocomplete="off" class="d-flex flex-column align-items-end mt-3">' +
				'<div class="flex-grow-1"></div>' +
				'<input id="collName" name="name" placeholder="კოლექციის დასახელება" value="'+coll_name+'" class="authorization-input mb-4 font-size-14 arial text-gray rounded-10 w-100">' +
				'<div class="coll-pop-btns">' +
				'<button class="save-btn btn" title="დამახსოვრება" type="submit">დამახსოვრება</button>' +
				'</div>' +
				'<div class="flex-grow-1"></div>' +
				'</form>' +
	        '</div>' +
	        '</div>' +
	        '</div>'
	    );
		
		
		
		
	    $('#ChangeNameCollection').submit(function(event) {
	        event.preventDefault();

	        var action = 'update_name';
	        var new_name = $('#collName').val();


	        $.ajax({
	                url: '/profile/collection_actions',
	                type: 'POST',
	                dataType: 'json',
	                data: { id: coll_id, action: action, name: new_name },
	            })
	            .done(function(response) {
	                if (response.status == true) {
	                    $('#notify').html('');
	                    $('#collection_name').text(response.name);
	                    $('.EditNameCollectionButton').data('name', response.name);
	                    Notify(response.msg);
	                } else {
	                    $('#notify').html('');
	                    Notify(response.msg, 'danger');

	                }

	            });

	    });
	});


	function remove_item(id) {
	    return $('[del="' + id + '"]').remove();
	}



	function deleteItem(action, id, type, item_id) {

	    //alertMsg = '';

	    if (confirm("ნამდვილად გსურთ წაშლა?")) {

	        $.ajax({
	                url: "/profile/collection_actions",
	                type: 'POST',
	                dataType: 'json',
	                data: { action: action, id: id, type: type, item_id: item_id },
	            })
	            .done(function(results) {

	                if (results.status == true) {
	                    remove_item(id);
	                    Notify(results.msg);
	                }
	                if (results.errors) {
	                    Notify(results.errors, 'danger');
	                }

	            });

	    }
	    return false;
	}


	function del(action, id, type, item_id, alertMsg = 'ნამდვილად გსურთ წაშლა?') {

	    if (confirm(alertMsg)) {

	        $.ajax({
	                url: "/profile/del",
	                type: 'POST',
	                dataType: 'json',
	                data: { action: action, id: id, type: type, item_id: item_id },
	            })
	            .done(function(results) {

	                if (results.status == true) {
	                    remove_item(id);
	                    Notify(results.msg);
	                }
	                if (results.errors) {
	                    Notify(results.errors, 'danger');
	                }

	            });

	    }
	    return false;
	}



	$('#subscribe_collection').click(function(event) {

	    var id = $(this).data('id');
	    var action = 'subscribe';
	    var _this = $(this);

	    $.ajax({
	            url: "/profile/collection_actions",
	            type: 'POST',
	            dataType: 'json',
	            data: { action: action, id: id },
	        })
	        .done(function(data) {
	            if (data.status === true) {
	                Notify(data.msg);
	                $(_this).addClass('subscribed').html(data.html)
	            }
	            if (data.status === false) {
	                Notify(data.msg, 'danger');
	                $(_this).removeClass('subscribed').removeClass('subscribe').html(data.html)
	            }
	            if (data.errors) {
	                Notify(data.errors, 'danger');
	            }
	        })
	        .fail(function(error) {
	            var response = error.responseJSON;
	            if (response.msg) Notify(response.msg, 'danger');
	        })

	});


$(document).delegate(".certification", "mouseout", function() {
	$("#sert").remove();
});

$(document).delegate(".certification", "mouseover", function() {
	var sert = $(this).data('sert');
	
	if(sert==='g' || sert==='tv-g' || sert==='tv-y'){
		$(this).append('<span id="sert">U - ყურება დაშვებულია ნებისმიერი ასაკისთვის.</span>');
	}
	if(sert==='pg'){
		$(this).append('<span id="sert">PG - რეკომენდირებულია მშობლის დასწრება.</span>');
	}
	if(sert==='r' || sert==='pg-13'){
		$(this).append('<span id="sert">PG - რეკომენდირებულია მშობლის დასწრება.</span>');
	}
	if(sert==='nc-17' || sert==='tv-ma'){
		$(this).append('<span id="sert">18+ ყურება დაშვებულია მხოლოდ ზრდასრულთათვის.</span>');
	}
});





	$('#problem_popup').click(function(e) {
	    e.preventDefault();

	    var id = $(this).data('id');
	    var type = $(this).data('type');
	    var year = $(this).data('year');
	    var title_ge = $(this).data('title_ge');
	    var title_en = $(this).data('title_en');
	    var img = $(this).data('img');

	    $.post("/profile/problem_popup", { id: id, type: type, year: year, img: img, title_ge: title_ge, title_en: title_en }, function(problem_popup) {
	        $('#notify').html(problem_popup);
	    });


	});

	$(document).delegate('#ProblemForm', 'submit', function(event) {
	    event.preventDefault();

	    var data = $(this).serialize();
	    var _this = this;


	    $.ajax({
	            url: "/profile/problem_report",
	            type: 'POST',
	            dataType: 'json',
	            data: data,
	        })
	        .done(function(results) {

	            $('.problem_general_error').remove();
	            if (results.status == true) {
	                $('.input_el_pop').removeClass('is-invalid');
	                $(_this).html('<h3 class="success">' + results.message + '</h3>');
	                $('#WarringPopap').children('.problem-overlay-in').css({ 'max-height': '250px' });
	            }
	            if (results.errors) {
	                $('.input_el_pop').removeClass('is-invalid');
	                $.each(results.errors, function(index, val) {
	                    if (index == 'general') {
	                        $('<p class="is-text-invalid arial problem_general_error">' + val + '</p>').prependTo($(_this));
	                        return;
	                    }
	                    $('.input_el_pop[name="' + index + '"]').addClass('is-invalid');
	                });
	            }

	        });


	});
	
	
	
	// quick search regex
	var qsRegex;

	// init Isotope
	var $grid = $('.ResultActorSearch').isotope({
	    itemSelector: '.movie-item',
	    layoutMode: 'fitRows',
	    filter: function() {
	        return qsRegex ? $(this).text().match(qsRegex) : true;
	    }
	});

	// use value of search field to filter
	var $quicksearch = $('#SearchMovieActor').keyup(debounce(function() {
	    qsRegex = new RegExp($quicksearch.val(), 'gi');
	    $grid.isotope();
	}, 200));

	// debounce so filtering doesn't happen every millisecond
	function debounce(fn, threshold) {
	    var timeout;
	    threshold = threshold || 100;
	    return function debounced() {
	        clearTimeout(timeout);
	        var args = arguments;
	        var _this = this;

	        function delayed() {
	            fn.apply(_this, args);
	        }
	        timeout = setTimeout(delayed, threshold);
	    };
	}



	function escapeHtml(text) {
	    var map = {
	        '"': '&quot;',
	        "'": '&#039;'
	    };

	    return text.replace(/[&<>"']/g, function(m) {
	        return map[m];
	    });
	}

	function escapeUnicode(str) {
	    return str.replace(/[^\0-~]/g, function(ch) {
	        return "\\u" + ("0000" + ch.charCodeAt().toString(16)).slice(-4);
	    });
	}
	
	var entityMap = {
	  '&': '%20',
	  '<': '%20',
	  '>': '%20',
	  '"': '%20',
	  "'": '%20',
	  '/': '%20',
	  '`': '%20',
	  '=': '%20'
	};

	function escapeHtml (string) {
	  return String(string).replace(/[&<>"'`=\/]/g, function (s) {
		return entityMap[s];
	  });
	}
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
	
function debounce(func, delay) {
    let timeout;
    return function(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delay);
    };
}

let results_status = false;

// ---- Search Suggestions (unified, scoped) -----------------------------
// LRU client-cache, AbortController, scoped per-form rendering.
// Targets BOTH #SearchMovie (header) AND .slidingDiv (sidebar) ფორმებს.
// listener-ები ერთვება input + paste event-ებზე — copy/paste იჭერს იდენტურად.
const __searchCache = new Map();
const __SEARCH_CACHE_MAX = 50;
let   __searchAbort = null;
let   __lastQuery   = '';

function __normalizeQuery(q) {
    return (q || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function __cacheGet(k) {
    if (!__searchCache.has(k)) return null;
    const v = __searchCache.get(k);
    __searchCache.delete(k);
    __searchCache.set(k, v);
    return v;
}

function __cacheSet(k, v) {
    if (__searchCache.has(k)) __searchCache.delete(k);
    __searchCache.set(k, v);
    while (__searchCache.size > __SEARCH_CACHE_MAX) {
        __searchCache.delete(__searchCache.keys().next().value);
    }
}

// container-ის (.header-top__search ან .slidingDiv) მოძებნა input-იდან
function __findSearchScope(input) {
    if (!input) return null;
    return input.closest('.header-top__search, .slidingDiv') || input.closest('form').parentNode;
}

function __renderSearchResults(results, scope) {
    if (!scope) return;
    const resultsContainer = scope.querySelector('#search_autocomplete');
    if (!resultsContainer) return;

    resultsContainer.innerHTML = "";
    results_status = false;

    if (!results || results.length === 0) return;

    const parts = [];
    for (let i = 0; i < results.length; i++) {
        const movie = results[i];
        const title_ge = movie.name || '';
        const title_en = movie.original_title || '';
        const image_bg = movie.backdrop ? movie.backdrop : '/theme/web/img/thumb.svg';
        const backdrop = image_bg.replace("/big/", "/small/");
        const res_title = movie.cats === 'trailer' ? 'თრეილერი' : (movie.is_series == 1 ? 'სერიალი' : 'ფილმი');
        const res_type  = movie.is_series == 1 ? 'serial' : 'movie';

        parts.push(
            '<div onclick="location.href=\'/' + res_type + '/' + movie.id + '/' + TitleSlug(title_en) + '\';" class="search-item">' +
                '<div class="thumb"><img src="' + backdrop + '" class="cover-img lazy_load"></div>' +
                '<div class="titles"><h3 class="title">' + title_ge + '<small>' + title_en + '</small></h3></div>' +
                '<div class="type">' + res_title + '</div>' +
            '</div>'
        );
    }
    resultsContainer.innerHTML = parts.join('');

    results_status = true;
    const input = scope.querySelector('input[name="search"]');
    if (input) input.classList.add('activeSearchInput');
    resultsContainer.classList.add('show');
    if (scope.classList.contains('header-top__search')) scope.classList.add('open');
}

async function handleSearch(input) {
    const scope = __findSearchScope(input);
    if (!scope) return;
    const resultsContainer = scope.querySelector('#search_autocomplete');

    const q = __normalizeQuery(input ? input.value : '');

    if (!q || q.length < 2) {
        if (resultsContainer) resultsContainer.innerHTML = "";
        results_status = false;
        return;
    }

    if (q === __lastQuery) {
        if (resultsContainer && !resultsContainer.innerHTML) {
            const cached = __cacheGet(q);
            if (cached) __renderSearchResults(cached, scope);
        }
        return;
    }

    const cached = __cacheGet(q);
    if (cached) {
        __lastQuery = q;
        __renderSearchResults(cached, scope);
        return;
    }

    if (__searchAbort) {
        try { __searchAbort.abort(); } catch (e) {}
    }
    __searchAbort = (typeof AbortController !== 'undefined') ? new AbortController() : null;

    try {
        const resp = await fetch('/api/search/suggestions?type=search&search=' + encodeURIComponent(q), {
            method: 'GET',
            credentials: 'same-origin',
            signal: __searchAbort ? __searchAbort.signal : undefined,
            headers: { 'Accept': 'application/json' }
        });
        if (!resp.ok) return;

        const json = await resp.json();
        const results = (json && json.data) ? json.data : [];

        __cacheSet(q, results);
        __lastQuery = q;
        __renderSearchResults(results, scope);
    } catch (err) {
        if (err && err.name === 'AbortError') return;
    } finally {
        __searchAbort = null;
    }
}

const debouncedSearch = debounce(function(input) { handleSearch(input); }, 250);

function __bindSearchInputs() {
    const inputs = document.querySelectorAll('form#SearchMovie input[name="search"], .slidingDiv input[name="search"]');
    inputs.forEach(function(el) {
        if (el.dataset.searchBound === '1') return;
        el.dataset.searchBound = '1';
        el.addEventListener('input', function() { debouncedSearch(el); });
        el.addEventListener('paste', function() {
            // paste — input ჩვეულებრივ ისედაც fire-დება, მაგრამ
            // setTimeout-ი უზრუნველყოფს რომ value უკვე განახლებული იყოს
            setTimeout(function() { debouncedSearch(el); }, 0);
        });
        el.addEventListener('focus', function() { debouncedSearch(el); });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', __bindSearchInputs);
} else {
    __bindSearchInputs();
}

window.addEventListener('click', function(e) {
    const target = e.target;
    const allScopes = document.querySelectorAll('.header-top__search, .slidingDiv');
    let inside = false;
    allScopes.forEach(function(scope) {
        if (scope.contains(target)) inside = true;
    });
    if (inside && results_status) {
        allScopes.forEach(function(scope) {
            if (scope.contains(target)) {
                const ac = scope.querySelector('#search_autocomplete');
                const inp = scope.querySelector('input[name="search"]');
                if (inp) inp.classList.add('activeSearchInput');
                if (ac) ac.classList.add('show');
                if (scope.classList.contains('header-top__search')) scope.classList.add('open');
            }
        });
    } else {
        document.querySelectorAll('#search_autocomplete').forEach(function(ac) { ac.classList.remove('show'); });
        document.querySelectorAll('form#SearchMovie input[name="search"], .slidingDiv input[name="search"]').forEach(function(inp) { inp.classList.remove('activeSearchInput'); });
        document.querySelectorAll('.header-top__search').forEach(function(s) { s.classList.remove('open'); });
    }
});
	
	
	
	

	
	
	
	
	
	
	
	
	
	
	
	
	
	
	

	function removeURLParameter(url, parameter) {
	    //prefer to use l.search if you have a location/link object
	    var urlparts = url.split('?');
	    if (urlparts.length >= 2) {

	        var prefix = encodeURI(parameter);
	        var pars = urlparts[1].split(/[&]/g);
	        //reverse iteration as may be destructive
	        for (var i = pars.length; i-- > 0;) {
	            //idiom for string.startsWith

	            if (pars[i].lastIndexOf(prefix, 0) != -1) {
	                pars.splice(i, 1);
	            }
	        }

	        return urlparts[0] + (pars.length > 0 ? '?' + pars.join('&') : '');
	    }
	    return url;
	}
	
	function queryStringUrlReplacement(uri, key, value) {
	    var re = new RegExp("([?&])" + key + "=.*?(&|$)", "i");
	    var separator = uri.indexOf('?') !== -1 ? "&" : "?";
	    if (uri.match(re)) {
	        return uri.replace(re, '$1' + key + "=" + value + '$2');
	    } else {
	        return uri + separator + key + "=" + value;
	    }
	}
	
	
	
	function hasFilterParam(var_name) {
	    var query = window.location.search.substring(1);
	    var vars = query.split("&");
	    for (var i = 0; i < vars.length; i++) {
	        var pair = vars[i].split("=");
	        if (pair[0] == var_name) {
	            return pair[1];
	        }
	    }
	    return (false);
	}


	function removeParam(key, sourceURL) {
	    var rtn = sourceURL.split("?")[0],
	        param,
	        params_arr = [],
	        queryString = (sourceURL.indexOf("?") !== -1) ? sourceURL.split("?")[1] : "";
	    if (queryString !== "") {
	        params_arr = queryString.split("&");
	        params_arr.splice(0, 1);
	        rtn = rtn + "?" + params_arr.join("&");
	    }
	    return rtn;
	}



	function RenderResultFilter(FilterElemtn, showImd = true, showYear = true) {



	    $GanresInput = $(FilterElemtn).find('.ganre_input:checked');
	    $GanresInputMob = $(FilterElemtn).find('.input_gener_mob:checked');
	    $CountryInput = $(FilterElemtn).find('.country_input:checked');
	    $CountryInputMob = $(FilterElemtn).find('.country_mob_input:checked');
	    $LangInput = $(FilterElemtn).find('.lang_input:checked');
	    $LangInputMob = $(FilterElemtn).find('.mob_lang_input:checked');
	    $StudioInput = $(FilterElemtn).find('.studio_input:checked');
	    $TypeInputMob = $(FilterElemtn).find('.input_type_mob:checked');
	    $('.ResultFitreed').empty();
	    $('.ganreMobResult').empty();
	    $('.countryMobResult').empty();
	    $('.LangMobResult').empty();
	    $('.TypeMobResult').empty();
		

	    if (hasFilterParam('imdb')) {
	        var IMDbMax = $(FilterElemtn).find('.imd_min').val();
	        var IMDbMin = $(FilterElemtn).find('.imd_max').val();
	        $('.ImdbMobResult').append('<div class="filter-item-mob rounded-5 arial text-main font-size-14">' + IMDbMin + ' - ' + IMDbMax + '</div>')
	        $('.ResultFitreed').append('<li class="chip imd_res"><a href="#">' + IMDbMin + ' - ' + IMDbMax + ' <span class="removeEleMentFilter" data-preg="imdb" title="წაშლა"><i class="icofont-close"></i></span></a></li>')
	    }

	    if (hasFilterParam('year')) {
	        var YearMin = $(FilterElemtn).find('.year_min').val();
	        var YearMax = $(FilterElemtn).find('.year_max').val();
	        $('.ResultFitreed').append('<li class="chip year_res"><a href="#">' + YearMin + ' - ' + YearMax + ' <span class="removeEleMentFilter" data-preg="year" title="წაშლა"><i class="icofont-close"></i></span></a></li>');

	        $('.YearMobResult').append('<div class="filter-item-mob rounded-5 arial text-main font-size-14">' + YearMin + ' - ' + YearMax + '</div>')
	    }

	    $GanresInput.each(function(index, val) {
	        var array_selected = [];
	        if ($(val).parent('.chip').data('index') !== $(val).val()) {
	            $('.ResultFitreed').append('<li data-index="' + $(val).val() + '" class="chip"><a href="#">' + $(val).data('val') + ' <span class="removeEleMentFilter" data-preg="genres[]" title="წაშლა"><i class="icofont-close"></i></span></a></li>');
	        }
	    });


	    $LangInput.each(function(index, val) {
	        var array_selected = [];
	        $('.ResultFitreed').append('<li data-index="' + $(val).val() + '" class="chip"><a href="#">' + $(val).data('val') + ' <span class="removeEleMentFilter" data-preg="languages" title="წაშლა"><i class="icofont-close"></i></span></a></li>')
	    });


	    $CountryInput.each(function(index, val) {
	        var array_selected = [];
	        if ($(val).parent('.chip').data('index') !== $(val).val()) {
	            $('.ResultFitreed').append('<li data-index="' + $(val).val() + '" class="chip"><a href="#">' + $(val).data('val') + ' <span class="removeEleMentFilter" data-preg="countries" title="წაშლა"><i class="icofont-close"></i></span></a></li>')
	        }
	    });

	    $StudioInput.each(function(index, val) {
	        $('.ResultFitreed').append('<li data-index="' + $(val).val() + '" class="chip"><a href="#">' + $(val).data('val') + ' <span class="removeEleMentFilter" data-preg="' + $(val).data('param') + '" title="წაშლა"><i class="icofont-close"></i></span></a></li>')
	    });


	    if ($.trim($('.ResultFitreed').html()) !== '') {
	        $('.ResultFitreed').parent('.subfilter-container').show()
	    }
	}
	
	
	$('.btn_filet_collection').click(function(e) {
	    e.preventDefault();
	    $('.btn_filet_collection').removeClass('active');
	    $(this).addClass('active');
	    var Type = $(this).data('type');
	    var route = $(this).data('route');

	    $.ajax({
	            url: route,
	            type: 'POST',
	            dataType: 'json',
	            data: {
	                type: Type,
	                '_token': token
	            },
	        })
	        .done(function(data) {
	            if (data.length > 0) {
	                $('.ResultFiltredMainCollection').empty();
	                $.each(data, function(index, val) {
	                    if (window.innerWidth > 1200) {
	                        $('.ResultFiltredMainCollection').append("<div class=\"col-xl-4 col-md-6 col-12 mb-4 collect_ithem position-relative\">\
                                    <div class=\"card serial rounded-10 overflow-hidden\">\
                                        <div class=\"row no-gutters\">\
                                            <div class=\"col-5 collection-image position-relative  overflow-hidden\">\
                                                <a href=\"" + val.link + "\">\
                                                    " + val.image + "\
                                                </a>\
                                            </div>\
                                            <div class=\"col-7 position-relative\">\
                                                <a href=\"" + val.link + "\" class=\"m-4 text-inversed arial collection-name\">\
                                                   " + val.name + "\
                                                </a>\
                                                <a href=\"" + val.author_link + "\" class=\"px-4 d-flex align-items-center mb-5\">\
                                                    <img src=\"" + val.author_avat + "\" alt=\"" + val.author + "\" class=\"user-img\">\
                                                    <div class=\"ml-2 text-gray arial font-size-12\">" + val.author + "</div>\
                                                </a>\
                                                <div class=\"text-gray font-size-12 arial position-absolute bottom left movie-quant-mob\">" + val.count_movie + " Ã¡Æ’Â¤Ã¡Æ’ËœÃ¡Æ’Å¡Ã¡Æ’â€ºÃ¡Æ’Ëœ</div>\
                                                <div class=\"d-flex align-items-center justify-content-center arial font-size-12 position-absolute bottom right collection-subs\">" + val.count_subscribe + " Ã¡Æ’â€™Ã¡Æ’ÂÃ¡Æ’â€ºÃ¡Æ’ÂÃ¡Æ’â€ºÃ¡Æ’Â¬Ã¡Æ’â€Ã¡Æ’ Ã¡Æ’Ëœ</div>\
                                            </div>\
                                        </div>\
                                    </div>\
                                </div>");
	                    } else {
	                        $('.ResultFiltredMainCollection').append("<div class=\"coll-item-mob mt-3\">\
                    <div class=\"card serial rounded-10 overflow-hidden\">\
                        <div class=\"row no-gutters\">\
                            <div class=\"collection-image position-relative overflow-hidden\">\
                                <a href=\"" + val.link + "\">\
                                " + val.image + "\
                            </a>\
                            </div>\
                            <div class=\"colls-item\">\
                            <div class=\"position-relative\">\
                                <a href=\"" + val.link + "\" class=\"m-4 text-inversed arial collection-name\">\
                                    " + val.name + "\
                                </a>\
                                <div class=\"coll-img\">\
                                <a href=\"" + val.author_link + "\" class=\"px-4 d-flex align-items-center mb-5\">\
                                    <img src=\"" + val.author_avat + "\" alt=\"" + val.author + "\" class=\"user-img\">\
                                    <div class=\"ml-2 text-gray arial font-size-12\">" + val.author + "</div>\
                                </a> </div>\
                                <div class=\"coll-stats\">\
                                <div class=\"text-gray font-size-12 arial position-absolute bottom left movie-quant-mob\">" + val.count_movie + " Ã¡Æ’Â¤Ã¡Æ’ËœÃ¡Æ’Å¡Ã¡Æ’â€ºÃ¡Æ’Ëœ</div>\
                                <div class=\"d-flex align-items-center justify-content-center arial font-size-12 position-absolute bottom right collection-subs\">" + val.count_subscribe + " Ã¡Æ’â€™Ã¡Æ’ÂÃ¡Æ’â€ºÃ¡Æ’ÂÃ¡Æ’â€ºÃ¡Æ’Â¬Ã¡Æ’â€Ã¡Æ’ Ã¡Æ’Ëœ</div>\
                                </div>\
                                </div>\
                            </div>\
                        </div>\
                    </div>\
                </div>");
	                    }
	                });
	            }
	        })
	        .fail(function() {
	            console.log("error");
	        })
	        .always(function() {
	            console.log("complete");
	        });



	});
	
	
	RenderResultFilter($('.Movie_filter'));

	$('.studio_input').change(function() {
	    $('.studio_input').not(this).prop('checked', false);
	});

	$('.Movie_filter').change(function() {
	    RenderResultFilter($(this));
	    // $(this).trigger('submit');
	});




	// Robust chip-X removal: native delegated handler so it works regardless of
	// jQuery `delegate()` quirks, click target depth (<i> vs <span>), and the
	// surrounding <a href="#"> default action.
	(function () {
	    // Removes one filter key/value pair from URL in a robust way.
	    // Handles both legacy array-style keys (e.g. languages[]) and plain keys
	    // (e.g. languages), plus percent-encoded querystrings.
	    function removeFilterParam(url, rawParamName, rawParamValue) {
	        var name = (rawParamName || '').trim();
	        if (!name) return url;
	        var value = (rawParamValue === null || typeof rawParamValue === 'undefined') ? '' : String(rawParamValue);
	        var plain = name.replace(/\[\]$/, '');
	        var names = [name];
	        if (names.indexOf(plain) === -1) names.push(plain);
	        var bracket = plain + '[]';
	        if (names.indexOf(bracket) === -1) names.push(bracket);
	        function normalize(v) {
	            if (v === null || typeof v === 'undefined') return '';
	            var out = String(v).replace(/\+/g, ' ').trim();
	            try { out = decodeURIComponent(out); } catch (e) {}
	            return out.toLowerCase();
	        }
	        var normalizedValue = normalize(value);
	        var singleSelect = (plain === 'countries' || plain === 'languages');
	        try {
	            var u = new URL(url, window.location.origin);
	            var removedAny = false;
	            names.forEach(function (k) {
	                var currentValues = u.searchParams.getAll(k);
	                if (!currentValues.length) return;
	                if (value === '') {
	                    removedAny = true;
	                    u.searchParams.delete(k);
	                    return;
	                }
	                var keep = [];
	                currentValues.forEach(function (v) {
	                    if (normalize(v) !== normalizedValue) {
	                        keep.push(v);
	                    } else {
	                        removedAny = true;
	                    }
	                });
	                u.searchParams.delete(k);
	                keep.forEach(function (v) { u.searchParams.append(k, v); });
	            });
	            // countries/languages are single-select in UI; if value format differs
	            // from URL, drop the whole param anyway so chip X always works.
	            if (!removedAny && value !== '' && singleSelect) {
	                names.forEach(function (k) { u.searchParams.delete(k); });
	            }
	            var qs = u.searchParams.toString();
	            return u.origin + u.pathname + (qs ? '?' + qs : '') + (u.hash || '');
	        } catch (err) {
	            // Fallback for older browsers/edge cases.
	            var next = url;
	            if (value === '' || singleSelect) {
	                names.forEach(function (k) { next = removeURLParameter(next, k + '='); });
	                return next;
	            }
	            names.forEach(function (k) {
	                next = removeURLParameter(next, k + '=' + value);
	                next = removeURLParameter(next, k + '=' + encodeURIComponent(value));
	            });
	            return next;
	        }
	    }

	    function chipRemoveHandler(e) {
	        var target = e.target;
	        if (!target) return;
	        var rm = target.closest ? target.closest('.removeEleMentFilter') : null;
	        if (!rm) return;
	        e.preventDefault();
	        e.stopPropagation();
	        if (typeof e.stopImmediatePropagation === 'function') e.stopImmediatePropagation();
	        var chip = rm.closest('.chip');
	        var Preg = rm.getAttribute('data-preg') || '';
	        var Index = chip ? chip.getAttribute('data-index') : null;
	        if (!Preg) return;
	        var UpdateURl = removeFilterParam(
	            window.location.href,
	            Preg,
	            (Index === null || Index === '' || typeof Index === 'undefined') ? '' : Index
	        );
	        window.location.href = UpdateURl;
	    }
	    document.addEventListener('click', chipRemoveHandler, true); // capture phase, beats <a> defaults
	})();

	$('.Movie_filter').submit(function(event) {
	    event.preventDefault();
	    var $Dataserialize = $(this).serialize();
	    var ActionUrl = $(this).attr('action');
	    var IMDbMax = $(this).find('.imd_max').val();
	    var IMDbMin = $(this).find('.imd_min').val();
	    var YearMax = $(this).find('.year_min').val();
	    var YearMin = $(this).find('.year_max').val();
	    var TypeFilter = $(this).find('input[name="type"]:checked').val();
	    console.log(TypeFilter);
	    console.log(ActionUrl);
	    ActionUrl = queryStringUrlReplacement(ActionUrl, 'type', TypeFilter);
	    var IMDbresult = "&imdb=" + IMDbMax + ";" + IMDbMin;
	    var YearResult = "&year=" + YearMax + ";" + YearMin;
	    var result = ActionUrl + "&" + $Dataserialize + IMDbresult + YearResult;

	    location.href = removeParam('type', result);
	});


	var ithemCountry = $('.country-dropdown').find('label')

	$('.country-dropdown .dropdown-search input').keyup(function(event) {
	    const term = $(this).val().toLocaleLowerCase();
	    ithemCountry.each(function(index, elem) {

	        var hasResults = false;
	        var title = $(elem).attr('title');
	        if (title.toLowerCase().indexOf(term) != -1) {
	            $(elem).removeClass('filter_hide');
	            hasResults = true;
	        } else {
	            $(elem).addClass('filter_hide');
	        }
	    });


	})


	var ithemGenre = $('.genre-dropdown').find('label')

	$('.genre-dropdown .dropdown-search input').keyup(function(event) {
	    const term = $(this).val().toLocaleLowerCase();
	    $(this).closest('.genre-dropdown').find('label').each(function(index, elem) {

	        var hasResults = false;
	        var title = $(elem).attr('title');
	        if (title.toLowerCase().indexOf(term) != -1) {
	            $(elem).removeClass('filter_hide');
	            hasResults = true;
	        } else {
	            $(elem).addClass('filter_hide');
	        }
	    });


	})


















//end
//END