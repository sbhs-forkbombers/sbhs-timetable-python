/* sbhs-timetable-python
 * Copyright (C) 2015 James Ye, Simon Shields
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

window.EventBus = {};
(function(EventBus) {

	EventBus.listeners = {};

	EventBus.on = function _on(event, callback, priority) {
		if (!(event in this.listeners)) {
			this.listeners[event] = [callback];
		} else {
			if (priority) {
				this.listeners[event].unshift(callback);
			} else {
				this.listeners[event].push(callback);
			}
		}
	}

	EventBus.post = function _post(event, data) {
		var args = arguments;
		var that = this;
		if (!(event in this.listeners)) {
			console.warn('No listeners for', event);
			return;	
		}
		setTimeout(function() {
			var i = 0;
			for (i = 0; i < that.listeners[event].length; i++) {
				that.listeners[event][i].apply(that, args);
			}
		}, 0);
	}
})(window.EventBus);

moment.fn.fromNowCountdown = function(isCool, showDays) {
	var diff = Math.abs(moment().diff(this, 's'));
	var seconds = (diff % 60) + '';
	diff = Math.floor(diff/60);
	var minutes = (diff % 60) + '';
	diff = Math.floor(diff/60);
	if (seconds.length < 2) {
		seconds = '0' + seconds;
	}
	if (minutes.length < 2) {
		minutes = '0' + minutes;
	}
	if (showDays) {
		var hours = (diff % 24) + '';
		if (hours.length < 2) hours = '0' + hours;
		diff = Math.floor(diff / 24);
		var days = diff;
		diff = hours;
	}
	if (diff > 0) {
		if (isCool) return diff +':' + minutes + ':' + seconds;
		return (showDays ? days + 'd ' : '') + diff + 'h ' + minutes + 'm ' + seconds + 's';
	}
	return minutes + 'm ' + seconds + 's';
}
;/* global moment */
/* sbhs-timetable-python
 * Copyright (C) 2015 James Ye, Simon Shields
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

var miniMode = window.innerWidth < 800;
var belltimes = undefined;
var timeSpentWaiting = moment();
var cachedCountdownEvent;
var countdownLabel = 'Loading...';
var inLabel = '';
var forcedDayOffset = 0; // brute-forcing public holidays and whatnot
var sbhsFailed = false;
var countdownToTheEnd = window.localStorage.ctteEnabled == undefined ? true : window.localStorage.ctteEnabled == 'true'; // only in pre-holiday mode
var _ctteCache = true; // internal use only

function getNextSchoolDay() {
	if (window.belltimes) {
		var m = moment(window.belltimes.date, "YYYY-MM-DD");
		if (m.hours(15).minutes(15).isAfter(moment())) {
			return m.startOf('day');
		}
	}
	if (window.today) {
		var m = moment(window.today.date, "YYYY-MM-DD");
		if (m.hours(15).minutes(15).isAfter(moment())) { // 3:15 on the given day is after now
			return m.startOf('day');					 // so it's legit. Otherwise, outdated today.json
		}
	}
	var today = moment();
	var dow = today.days();
	var offset = forcedDayOffset;
	if (dow == 0) { // SUNDAY
		offset++;
	} else if (dow == 6) { // SATURDAY
		offset += 2;
	} else if (today.isAfter(moment().hours(15).minutes(15), 'minute')) {
		offset++;
		if (dow == 5) { // FRIDAY
			offset += 2;
		}
	}
	return today.add(offset, 'days').startOf('day');
}

function sbhsDown() {
	console.log('looks like SBHS is down.');
	$('#countdown-label').html('<img src="/api/picture.jpeg" id="real-cute"/>');
	$('#period-label').text('SBHS is taking too long!');
	$('#in-label').html('here, have a cute picture instead. <a href="javascript:void(0)" onclick="window.location = window.location">reload</a> at any time to try again. <a href="/static/sbhs-failure.html">why does this happen?</a>')
}

function getNextCountdownEvent() {
	if (!window.belltimes || !window.belltimes.status == 200) {
		if (timeSpentWaiting.diff(moment(), 'seconds') < -20 && !sbhsFailed) {
			sbhsFailed = true;
			setTimeout(sbhsDown,1000);
		}
		return timeSpentWaiting; // count up from page load time
	} else {
		if (cachedCountdownEvent && cachedCountdownEvent.isAfter(moment()) && _ctteCache == countdownToTheEnd) {
			return cachedCountdownEvent;
		}
		_ctteCache = countdownToTheEnd;
		var termEnd = moment(config.nextHolidayEvent);
		var y12End = (config.holidayEventData.term == '3' && config.holidayEventData.end && config.userData.year == '12');
		if ((moment().add(1, 'd').isAfter(termEnd) && moment().isBefore(termEnd)) || y12End) {
			hookToggleable();
			$('#in-label,#countdown-label,#period-label').addClass('toggleable');
			if (countdownToTheEnd) {
				countdownLabel = 'School ends';
				inLabel = '<sup><em>' + (y12End ? 'forever' : 'finally') + '</em></sup>in';
				cachedCountdownEvent = termEnd;
				return termEnd;
			}
		}
		if (moment().isAfter(termEnd)) {
			console.log("end: ", config.nextHolidayEvent, moment(termEnd).toString(), "now: ", moment().toString());
			window.location = window.location; // reload
		}
		var i = 0;
		var now = moment();
		var nextSchoolDay = getNextSchoolDay();
		for (i = window.startIndex || 0; i < belltimes.bells.length; i++) { // loop over bells to find the next one
			var bell = belltimes.bells[i];
			var hm = bell.time.split(':');
			if (nextSchoolDay.hours(Number(hm[0])).minutes(Number(hm[1])).isAfter(now)) {
				inLabel = 'starts in';
				countdownLabel = bell.bell.replace('Roll Call', 'School Starts').replace('End of Day', 'School Ends');
				if (countdownLabel.indexOf('School') != -1) {
					inLabel = 'in';
				}
				if (window.today && /^\d/.test(bell.bell) && window.today.timetable) {
					// period - populate data from timetable
					if (bell.bell in today.timetable) {
						countdownLabel = today.timetable[bell.bell].fullName;
					} else {
						countdownLabel = 'Free';
					}
				} else if (/^\d/.test(bell.bell)) {
					countdownLabel = 'Period ' + bell.bell;
				}
				if (countdownLabel == 'Transition' || countdownLabel == 'Recess' || countdownLabel == 'Lunch 1') {
					inLabel = 'ends in';
					var next = belltimes.bells[i-1];
					if (window.today && window.today.timetable && /^\d/.test(next.bell)) {
						if (next.bell in today.timetable) {
							countdownLabel = today.timetable[next.bell].fullName;
						} else {
							countdownLabel = 'Free';
						}
					} else if (/^\d/.test(next.bell)) {
						countdownLabel = 'Period ' + next.bell;
					} else {
						countdownLabel = next.bell;
					}
				}
				/*if (countdownLabel.startsWith('Transition') || countdownLabel === 'Lunch 2' || countdownLabel.startsWith('Recess')) {
					inLabel = 'starts in';
					var next = belltimes.bells[i+1];
					if (window.today && /^\d/.test(next.bell)) {
						if (next.bell in today.timetable) {
							countdownLabel = today.timetable[next.bell].fullName;
						} else {
							countdownLabel = 'Free';
						}
					} else if (/^\d/.test(next.bell)) {
						countdownLabel = 'Period ' + next.bell;
					} else {
						countdownLabel = next.bell;
					}
				}*/
				cachedCountdownEvent = nextSchoolDay;
				return nextSchoolDay;
			}
		}
		return now;
	}
}


EventBus.on('bells', function(ev, bells) {
	window.belltimes = bells;
	window.cachedCountdownEvent = null;
	if (window.belltimes.status == "Error") {
		if (window.today) {
			reloadBells();
			loadNotices();
			loadBarcodeNews();
		} else {
			forcedDayOffset++;
			if (forcedDayOffset > 10) {
				// cry
				sbhsDown();
			} else {
				reloadBells();
				loadNotices();
				loadBarcodeNews();
				return;
			}
		}
	}
	cachedCountdownEvent = null;
	if (belltimes.bellsAltered) $('#top-line-notice').text('Bells changed: ' + belltimes.bellsAlteredReason);
	else $('#top-line-notice').text('');
});

function updateCountdown() {
	if (config.HOLIDAYS || sbhsFailed) return;
	$('#countdown-label').text(getNextCountdownEvent().fromNowCountdown(false, countdownToTheEnd));///*Math.abs(getNextCountdownEvent().diff(moment(), 'seconds')) + 's'*/);
	$('#in-label').html(inLabel);
	$('#period-label').text(countdownLabel);

}

function reloadBells() {
	$.getJSON('/api/belltimes', function(data) {
		EventBus.post('bells', data);
	});
}

function domReady() {
	if (document.readyState !== 'complete') return;
	if (!window.moment || !window.$ || !$.Velocity) {
		console.warn('MISSING SOME THINGS!');
		console.warn('this would go badly. so we won\'t let it go at all (▀̿Ĺ̯▀̿ ̿)');
		document.getElementById('period-label').innerHTML = 'Oops';
		document.getElementById('in-label').innerHTML = 'We couldn\'t load some things we need to run. Maybe <a href="/">try again?</a><br />or look at this picture!';
		document.getElementById('countdown-label').innerHTML = '<img src="/api/picture.jpeg"></img>';
		return;
	}
	/*if (/Android ([\d.]+);/.test(window.navigator.userAgent) && !('annoyed' in window.localStorage)) {
		var match = window.navigator.userAgent.match(/Android ([\d.]+);/)[1].split('.');
		var canInstallApp = false;
		if (match[0] == '4') {
			if (match.length >= 3) {
				if (Number(match[2]) >= 3) {
					// API 15!
					canInstallApp = true;
				}
			} else if (Number(match[1]) > 0) {
				canInstallApp = true;
			}
		} else if (Number(match[0]) > 4) {
			canInstallApp = true;
		}
		window.localStorage.annoyed = true;
		if (canInstallApp && confirm("We have an app! Install it now for offline timetable and class notifications?")) {
			window.location = 'http://play.google.com/store/apps/details?id=com.sbhstimetable.sbhs_timetable_android';
			//window.location = 'market://details?id=com.sbhstimetable.sbhs_timetable_android';
		}
	}*/
	window.belltimes = window.config.bells;
	$('#top-line-notice').text(belltimes.bellsAlteredReason);
	updateCountdown();
	reloadBells();
	// holidays
	if (config.HOLIDAYS) {
		$('#period-label,#countdown-label,.arrow,.sidebar').css({display: 'none'});
		$('#yt').css({display: 'block'}).html('<iframe src="https://www.youtube.com/embed/' + config.holidayCfg.video + '?autoplay=1&loop=1&' + config.holidayCfg.videoURIQuery +
			'" frameborder="0" allowfullscreen></iframe>');
		$('#in-label').html(config.holidayCfg.text);
		$('body').css({'background': config.holidayCfg.background});
	} else {
		loadBackgroundImage();
		if (window.config.loggedIn) {
			$('#login-status').html('<a href="/logout" title="Log out" style="text-decoration: none">Log out <span class="octicon octicon-sign-out"/></a>');
		} else {
			$('#login-status').html('<a href="/try_do_oauth" title="Log in" style="text-decoration: none">Log in <span class="octicon octicon-sign-in"/></a>');
		}
		setInterval(updateCountdown, 1000);
	}
	attachAllTheThings();
	EventBus.post('pageload', {});
}

document.addEventListener('readystatechange', domReady);
;/* sbhs-timetable-python
 * Copyright (C) 2014 James Ye, Simon Shields
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

function loadNotices() {
	if (!config.loggedIn) return;
	$('#top-pane .umad').html('¯\\_(ツ)_/¯ Loading ¯\\_(ツ)_/¯');
	showNoticesTimeout();
	var ds = getNextSchoolDay().format('YYYY-MM-DD');
	window.noticesLoading = true;
	updateSidebarStatus();
	$.getJSON('/api/notices.json?date='+ds, function(data) {
		window.notices = data
		window.noticesLoading = false;
		clearTimeout(window.noticesReloadPromptTimeout);
		updateSidebarStatus();
		EventBus.post('notices', data);
	});
}

function loadBarcodeNews() {
	var ds = getNextSchoolDay().format('YYYY-MM-DD');
	if (getNextSchoolDay().isAfter(moment().startOf('day'))) {
		console.log('bailing out of barcodenews');
		return;
	}
	$.getJSON('/api/barcodenews/list.json?date=' + ds, function(data) {
		window.barcodenews = data;
		EventBus.post('barcodenews', data);
	});
}

function showNoticesTimeout() {
	window.noticesReloadPromptTimeout = setTimeout(function() {
			$('#top-pane .umad').html('Loading the notices is taking a looong time... <a href="javascript:void(0)" onclick="loadNotices(); loadBarcodeNews()">Try again?</a>');
		}, 10000);
}

if (config.loggedIn) {
	EventBus.on('pageload', function() {
		showNoticesTimeout();
	});
}

loadNotices();
loadBarcodeNews();;/* sbhs-timetable-python
 * Copyright (C) 2015 James Ye, Simon Shields
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
var rightExpanded = false,
	leftExpanded = false,
	topExpanded = false;
// TODO rewrite this entire file to be better
function handleLeftPane() {
	/* Fill out the left pane */
	'use strict';
	if (!window.today || window.today.httpStatus != 200) return;
	var pane = document.getElementById('left-pane'),
		html = '<div id="day-name">' + window.today.today + ' <a href="javascript:void(0)" onclick="loadToday()" class="reload-prompt">reload?</a></span></div><table><tbody><tr><td>Subject</td><td>Teacher</td><td>Room</td></tr>',
		timetable = today.timetable,
		prefix, subj, suffix, room, teacher, fullTeacher, subjName, finalised,
		roomChanged, teacherChanged, cancelled = false;
	if (window.today.stale) {
		html = '<div class="cached-notice">This data may be outdated!</div>' + html;
	}
	for (var i = 1; i < 6; i++) {
		if (!(i in timetable) || !timetable[i].room) {
			html += '<tr class="free"><td>Free</td><td></td><td></td></tr>';
		}
		else {
			today.timetable[i].expanded = false;
			prefix = '';
			subj = '';
			suffix = '';
			subj = timetable[i].title;
			room = timetable[i].room;
			teacher = timetable[i].teacher;
			fullTeacher = timetable[i].fullTeacher;
			subjName = timetable[i].fullName;
			finalised = today.displayVariations || today.variationsFinalised || window.location.search.indexOf('Z01DB3RGGG') != -1;
			if (/\d$/.test(timetable[i].title) || /[a-z][A-Z]$/.test(timetable[i].title)) {
				suffix = timetable[i].title.substr(-1);
				subj = subj.slice(0,-1);
			}
			if (/*subj !== 'SDs' /* Software design special case  && subj.length == 3 /*|| (subj.length == 2 && suffix === '') ||*/ /^[WXYZ]/.test(subj)) { // very tentative guess that this is an elective - char 1 should be prefix
				prefix = subj[0];
				subj = subj.substr(1);
			}		
			if (subj.length == 3) {
				if (/[A-Z0-9]/.test(subj.substr(-1))) {
					suffix = subj.substr(-1);
					subj = subj.slice(0, -1);
				}
			}
			if (timetable[i].changed && finalised) {
				if (timetable[i].varies) { 
					if (timetable[i].cancelled) {
						cancelled = true;
					}
					else if (timetable[i].hasCasual) {
						teacherChanged = true;
						teacher = timetable[i].casual.toUpperCase();
						fullTeacher = timetable[i].casualDisplay.trim();
					}
				}
				if (timetable[i].roomFrom) {
					roomChanged = true;
					room = timetable[i].roomTo;
				}
			}
			var nSubj = '';
			var idx = 0;

			for (var j = 0; j < subj.length; j++) {
				var z = subjName.indexOf(subj[j+1]);
				z = z < 0 ? undefined : z;
				if (!z) {
					if (!subj[j+1]) {
						z = -1;
					} else {
						z = subjName.indexOf(subj[j+1].toLowerCase());
					}
				}
				z = z < 0 ? undefined : z;
				var mStr = subjName.substring(idx+1, z);
				nSubj += subj[j] + '<span class="subj-expand ' + (cancelled ? 'cancelled':'') + '">'+mStr+'</span>';
				idx = z;
			}
			var nTeach = '';
			idx = 0;
			var temp = teacher.toLowerCase();
			var fullTemp = fullTeacher;
			if (/^(Mr|Ms|Dr) /.test(fullTemp)) {
				fullTemp = fullTemp.split(' ').slice(1).join(' ');
			}
			if (fullTemp[0].toLowerCase() !== teacher[0].toLowerCase()) {
				// probably a split class, no expandability because otherwise it's broken
				fullTemp = teacher;
			}
			fullTemp = fullTemp.replace(' ', '&nbsp;');
			for (var k = 0; k < teacher.length; k++) {
				var y = fullTemp.toLowerCase().indexOf(temp[k+1]);
				y = y < 0 ? undefined : y;
				var extra = fullTemp.substring(idx+1, y);
				if (k !== 0) {
					nTeach += '<span class="small-caps">';
				}
				nTeach += (k === 0 ? teacher[k].toUpperCase() : teacher[k].toLowerCase()) + '<span class="teach-expand ' + (cancelled ? 'cancelled':'') + '">'+extra.toLowerCase()+'</span>';
				if (k !== 0) {
					nTeach += '</span>';
				}
				idx = y;
			}
			if (cancelled) {
				room = 'N/A';
			}
			html += '<tr'+(cancelled?' class="cancelled changed"':'')+'><td class="subject" title="'+subjName+'" onclick="expandSubject(event,'+i+')">'+timetable[i].year+prefix+'<strong>'+nSubj+'</strong>'+suffix+'</td><td class="teacher'+(teacherChanged?' changed'+(!finalised?' changeable':''):'')+'" title="'+fullTeacher+'" onclick="teacherExpand(event,'+i+')">'+nTeach+'</td><td'+(roomChanged?' class="changed' + (!finalised?' changeable"':'"'):'')+'>'+room+'</td></tr>';
			cancelled = false;
			roomChanged = false;
			teacherChanged = false;
		}
	}
	html += '</tbody></table><br/>';
	var fetch = window.today._fetchTime * 1000;
	html += '<div class="last-updated"><span class="label">Last updated:</span> ' + moment(fetch).format('ddd Do MMM hh:mm:ss a') + '</div><table><tbody>';
	pane.innerHTML = html;
}

function expandSubject(event, id) {
	'use strict';
	if (today.timetable[id].expanded) {
		$('.subj-expand', event.currentTarget.parentNode).velocity('stop').velocity('transition.slideLeftBigOut');
		today.timetable[id].expanded = false;
	}
	else {
		$('.subj-expand', event.currentTarget.parentNode).velocity('stop').velocity('transition.slideLeftBigIn');
		today.timetable[id].expanded = true;
	}
}

function teacherExpand(event, id) {
	'use strict';
	var el = event.currentTarget.parentNode;
	if (el.tagName.toLowerCase() === 'span') {
		el = el.parentNode;
	}
	if (today.timetable[id].teachExpanded) {
		$('.teach-expand', el).velocity('stop').velocity('transition.slideLeftBigOut');
		today.timetable[id].teachExpanded = false;
	}
	else {
		$('.teach-expand', el).velocity('stop').velocity('transition.slideLeftBigIn');
		today.timetable[id].teachExpanded = true;
	}
}

EventBus.on('today', handleLeftPane);


// notices
function handleTopPane() {
	'use strict';
	var entry, list, today = new Date(), res = '', j, i, date, dom, wday, month,
		weekdays = 'Sunday Monday Tuesday Wednesday Thursday Friday Saturday'.split(' '),
		months = 'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(' ');
	if (!window.notices || !window.notices.notices) {
		return;
	}
	var sorted = Object.keys(window.notices.notices).sort(function(a,b) {
		if (a >  b) {
			return -1;
		}
		return 1;
	});
	res += '<select id="notices-filter" class="animated">';
	res += '<option value="notice">All notices</option>';
	for (i = 7; i <= 12; i++) {
		res += '<option value="notice'+i+'">Year ' + i + '</option>';
	}
	res += '<option value="noticeStaff">Staff</option></select>';
	date = (window.notices.date ? window.notices.date : belltimes.date);
	date = moment(date, 'YYYY-MM-DD');
	wday = date.format('dddd');
	dom = date.format('DD');
	month = date.format('MMM');
	if (window.notices.date !== null) {
		res += '<h1 class="notices-header">Notices for ' + wday + ' ' + dom + ' ' + month + ' &mdash; Week ' + window.notices.week + '';
	} else {
		res += '<h1 class="notices-header">Notices for ' + wday + ' ' + dom + ' ' + month + ' &mdash; Week ' + belltimes.week + belltimes.weekType + '';
	}
	res += ' <span id="notices-reload"><a href="javascript:void(0)" onclick="loadNotices(); loadBarcodeNews()">Reload</a></span></h1>';
	var fetch = window.notices._fetchTime * 1000;
	res += '<div class="last-updated"><span class="label">Last updated:</span> ' + moment(fetch).format('ddd Do MMM hh:mm:ss a') + '</div><table><tbody>';
	if (window.barcodenews && window.barcodenews.content.current.length > 0) {
		res += '<tr id="barcodenews" class="notice-row barcodenews" style="line-height: 1.5">';
		res += '<td class="notice-target animated">All Students and Staff</td>';
		res += '<td class="notice-data"><h2 class="notice-title">Today\'s Barcode News</h2><div class="notices-hidden" id="nbarcodenews-hidden">';
		res += '<div id="nbarcodenews-txt" class="notice-content">';
		for (j in window.barcodenews.content.current) {
			list = window.barcodenews.content.current[j];
			res += '<strong>';
			if (list.years[0] !== 'all' && list.years.length > 1) {
				res += 'Years ' + list.years.join(', ');
			}
			else if (list.years[0] !== 'all' && list.years.length == 1) {
				res += 'Year ' + list.years[0];
			}
			else {
				res += 'Everyone';
			}
			res += '</strong>';
			res +=': ' + list.content + '<br />';
		}
		res += '</div></div></td></tr>';
	}
	for (i in sorted) {
		if (!sorted.hasOwnProperty(i)) continue;
		list = window.notices.notices[sorted[i]];
		for (j in list) {
			if (!list.hasOwnProperty(j)) continue;
			entry = list[j];
			res += '<tr id="'+entry.id+'" class="notice notice' + entry.years.join(' notice') + ' notice-row ' + (entry.isMeeting ? 'meeting' : '') + '">';
			res += '<td class="notice-target animated">'+entry.dTarget+'</td>';
			res += '<td class="notice-data"><h2 class="notice-title">'+entry.title+'</h2><div class="notice-hidden" id="n'+entry.id+'-hidden">';
			if (entry.isMeeting) {
				date = moment(entry.meetingDate, 'YYYY-MM-DD');
				wday = date.format('dddd');
				month = date.format('MMM');
				dom = date.format('DD');
				res += '<div class="notice-meeting"><strong>Meeting Date:</strong> ' + wday + ', ' + month + ' ' + dom + ' ' + date.format('YYYY') + '<br />';
				res += '<strong>Meeting Time:</strong> ' + entry.meetingTime + ' in ' + entry.meetingPlace + '<br /></div>';
			}
			res += '<div id="n'+entry.id+'-txt" class="notice-content">';
			res += entry.text + '</div><div class="notice-author">'+entry.author+'</div></div></td></tr>';
		}
	}
	res += '</tbody></table>';
	document.getElementById('top-pane').innerHTML = res;
	$('.notice-row').click(function() {
		/*jshint validthis: true*/
		var id = this.id;
		var el = $('#n'+id+'-hidden');
		if (!el.hasClass('velocity-animating')) {
			if (el.hasClass('notice-hidden')) {
				el.velocity('stop').removeClass('notice-hidden').velocity('slideDown');
			}
			else {
				el.velocity('stop').velocity('slideUp').addClass('notice-hidden');
			}
		}
	});

	$('#notices-filter').change(function() {
		/*jshint validthis: true*/
		console.log('change!');
		var val = this.value;
		$('.notice').velocity('fadeOut');
		$('.'+val).velocity('stop').velocity('fadeIn');
	});

}

EventBus.on('notices', handleTopPane);
EventBus.on('barcodenews', handleTopPane);

// bells

function handleRightPane() {
	/* Fill out the right pane */
	'use strict';
	var bells = belltimes.bells, rowClass, bell, timeClass;
	var res = '<div id="bell-day">' + window.belltimes.day + ' ' + window.belltimes.weekType.replace('Z', '?') + ' <a href="javascript:void(0)" onclick="reloadBells()">reload?</a></div><br />';
	var fetch = (window.belltimes._fetchTime || -1) * 1000;
	res += '<br /><br /><table><tbody>';
	for (var i in bells) {
		if (!bells.hasOwnProperty(i)) {
			continue;
		}
		bell = bells[i].bell;
		timeClass = 'bell';
		rowClass = 'break';
		if (/^\d$/.test(bell)) {
			rowClass = 'period';
			bell = 'Period ' + bell;
		}
		if (bells[i].different) {
			timeClass += ' changed" title="normally ' + bells[i].normally;
		}
		res += '<tr class="'+rowClass+'"><td class="bell">'+bell+'</td><td class="'+timeClass+'">'+bells[i].time+'</td></tr>';
	}
	res += '</tbody></table>';
	if (fetch < 0) {
		res += '<div class="last-updated"><span class="label">Last updated:</span> never</div>';
	} else {
		res += '<div class="last-updated"><span class="label">Last updated:</span> ' + moment(fetch).format('ddd Do MMM hh:mm:ss a') + '</div>';
	}
	res += '<br><br>';
	document.getElementById('right-pane').innerHTML = res;
}

EventBus.on('bells', handleRightPane);
;/* sbhs-timetable-python
 * Copyright (C) 2015 James Ye, Simon Shields
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */
 var today = {};
 function loadToday() {
 	if (!config.loggedIn) return;
 	if (!window.today || !window.today.httpStatus) {
 		$('#left-pane .umad').html('¯\\_(ツ)_/¯ Loading ¯\\_(ツ)_/¯');
 		showTodayTimeout();
 	}
 	window.todayLoading = true;
 	updateSidebarStatus();
 	if (window.belltimes && belltimes.status == 'OK') {
 		if ((belltimes.day + belltimes.weekType) in localStorage) {
 			try {
 				var obj = JSON.parse(localStorage[belltimes.day + belltimes.weekType]);
 				if (obj.httpStatus == 200) {
 					obj.stale = true;
 					obj.displayVariations = false;
 					EventBus.post('today', obj);
 				}
 			} catch (e) {
 				console.log('couldn\'t parse json, ditching it.');
 			}
 		}
 	}
 	if (!config.loggedIn) {
 		console.log('not logged in, don\'t bother');
 		return;
 	}
 	$.getJSON('/api/today.json', function(data, status, xhr) {
 		if (data.httpStatus == 200) {
 			window.localStorage[data.today.replace(' ','')] = JSON.stringify(data);
 			if (!belltimes || belltimes.status != 'OK') {
 				reloadBells();
 			}
 			clearTimeout(window.timetableReloadPromptTimeout);
 			window.todayLoading = false;
 			updateSidebarStatus();
 			EventBus.post('today', data);
 		}
 	});

 }

 EventBus.on('today', function(ev, data) {
 	window.today = data;
 	cachedCountdownEvent = false;
 	getNextCountdownEvent();
 }, true);

 function showTodayTimeout() {
 		window.timetableReloadPromptTimeout = setTimeout(function() {
			$('#left-pane .umad').html('Loading your timetable is taking a looong time... <a href="javascript:void(0)" onclick="loadToday()">Try again?</a>');
		}, 10000);
 }
loadToday();
;/* sbhs-timetable-python
 * Copyright (C) 2015 James Ye, Simon Shields
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

// functions for collapsing and expanding the panes

var lastScreenTap = Date.now(),
	screenTapId = 0;

function collapsePane(p) {
	/* Collapses a pane */
	'use strict';
	var el = $('#'+p+'-pane');
	var cfg = {};
	cfg[p] = '-110%';
	el.velocity('finish').velocity(cfg, 750, 'ease');
	$('#'+p+'-pane-arrow').removeClass('expanded');
	window[p+'Expanded'] = false;
}

function expandPane(p) {
	/* Expands a pane */
	'use strict';
	var el = $('#'+p+'-pane');
	var cfg = {};
	cfg[p] = 0;
	el.velocity('finish').velocity(cfg, 750, 'ease');
	$('#'+p+'-pane-arrow').addClass('expanded');
	window[p+'Expanded'] = true;
}

function togglePane(which) {
	/* Toggles expand state of a pane */
	'use strict';
	if (window[which+'Expanded']) {
		collapsePane(which);
	} else {
		expandPane(which);
	}
}

function toast() {
	if ($('#toast').hasClass('visible')) {
		$('#toast').removeClass('visible').velocity('stop').velocity({'top': '110%'});
	} else {
		$('#toast').velocity('stop').velocity({'top': '80%'}).addClass('visible');
	}
}

function toggleCountdownMode() {
	countdownToTheEnd = !countdownToTheEnd;
	window.localStorage.ctteEnabled = countdownToTheEnd;
	$('#toast').text('Click now to switch to ' + (countdownToTheEnd ? 'normal' : 'hype') + ' mode');
	getNextCountdownEvent();
	updateCountdown();
}

function hookToggleable() {
	if ($('.toggleable').hasClass('hooked')) return;
	$('.toggleable').addClass('hooked').on('mouseover', toast).on('mouseleave', toast).on('click', toggleCountdownMode);
}

function toggleTop() {
	'use strict';
	if (topExpanded) {
		collapsePane('top');
		onScreenTapTimeout();
	} else {
		if (leftExpanded) {
			collapsePane('left');
		}

		if (rightExpanded) {
			collapsePane('right');
		}
		onInteract();
		expandPane('top');
	}
}

function toggleRight() {
	'use strict';
	if (rightExpanded) {
		collapsePane('right');
		onScreenTapTimeout();
	} else {
		if (topExpanded) {
			collapsePane('top');
		}

		if ((window.innerWidth <= 450) && leftExpanded) {
			collapsePane('left');
		}
		onInteract();
		expandPane('right');
	}
}

function toggleLeft() {
	'use strict';
	if (leftExpanded) {
		collapsePane('left');
		onScreenTapTimeout();
	} else {
		if (topExpanded) {
			collapsePane('top');
		}

		if ((window.innerWidth <= 450) && rightExpanded) {
			collapsePane('right');
		}
		onInteract();
		expandPane('left');
	}
}

// expand/deflate the countdown (this function is attached to the button in the top-left)
function toggleExpansion(ev) {
	/* jshint validthis: true */
	'use strict';
	if (ev.target.id == 'expand') {
		$('#countdown-label').velocity({zIndex: 0, fontSize: '10em', top: '50%', left: 0, width: '100%', marginTop: '-1em', position: 'fixed'});
		$('#period-label,#in-label,#feedback,#sidebar,.really-annoying').velocity('finish').velocity('fadeOut');
		$('#expand').css({display: 'none'});
		$('#collapse').css({'display': 'block'});
		window.localStorage.expanded = true;
	} else {
		$('#countdown-label').css({fontSize: miniMode ? '5em' : '7em', width: 'inherit', marginTop: 0, position: 'relative'})[0].setAttribute('style', '');
		$('#period-label,#in-label,#feedback,#sidebar,.really-annoying').velocity('finish').velocity('fadeIn');
		$('#collapse').css({display: 'none'});
		$('#expand').css({'display': 'block'});
		window.localStorage.expanded = false;
	}
}



function onScreenTapTimeout() {
	if ((Date.now() - lastScreenTap) > 3000) {
		if (topExpanded || rightExpanded || leftExpanded) {
			return;
		}
		$('.arrow').css({ opacity: 0 }).css({ visibility: 'hidden' });
		$('body').css({cursor: 'none'});
		$('#update,.really-annoying,#sidebar,#links').velocity('finish').velocity({ 'opacity': 0 }, { duration: 300 });
	} else {
		screenTapId = setTimeout(onScreenTapTimeout, 3000 - (Date.now() - lastScreenTap));
	}
}

function onInteract() {
	$('.arrow').css({ 'visibility': 'visible', 'opacity': 'inherit' });
	$('body').css({ 'cursor': 'default' });
	$('#update,.really-annoying,#sidebar,#links').velocity('finish').velocity({ 'opacity': 1 }, { duration: 300 });
	lastScreenTap = Date.now();
	if (screenTapId !== 0) {
		clearTimeout(screenTapId);
	}
	setTimeout(onScreenTapTimeout, 5000);
}


function snazzify(el) {
	'use strict';
	var r = Math.floor(Math.random()*255);
	var g = Math.floor(Math.random()*255);
	var b = Math.floor(Math.random()*255);
	$(el).velocity({colorRed: r, colorGreen: g, colorBlue: b});
}

function attachAllTheThings() {
	// show/hide the cached list
	if (!$.fn.velocity) {
		$.fn.velocity = function () {
			if (arguments[0] == 'finish') {
				return this;
			}
			$.fn.css.apply(this, arguments); // good enough
		}
	}
	$('#cached').click(function() {
		if ($('#dropdown-arrow').hasClass('expanded')) {
			$('#verbose-hidden').velocity('finish').velocity('slideUp', { duration: 300 });
			$('#dropdown-arrow').removeClass('expanded');
		} else {
			$('#verbose-hidden').velocity('finish').velocity('slideDown', { duration: 300 });
			$('#dropdown-arrow').addClass('expanded');
		}
	});

	// settings modal
	$('#launch-settings').click(function() {
		$('#settings-modal,#fadeout').velocity('finish').velocity('fadeIn');
	});

	$('#close-settings-modal').click(function() {
		$('#settings-modal,#fadeout').velocity('finish').velocity('fadeOut');
	});

	$('#custom-background').click(handleUpload);

	if ('cached-bg' in window.localStorage) {
		$('#custom-background').html('Clear');
	}
	var options = ['default', 'red', 'green', 'purple'];
	//$('#colourscheme-combobox')[0].selectedIndex = ((options.indexOf(config.colour) > -1) ? options.indexOf(config.colour) : 0);

	$('#colourscheme-combobox').change(function() {
		/*jshint validthis: true */
		var el = this.options[this.selectedIndex].value;
		if (/colour/.test(window.location.search)) {
			window.location.search = window.location.search.replace(/colour=.+?(\&|$)/, 'colour='+el+'&');
		}
		else {
			if (window.location.search.substr(0,1) === '?') {
				window.location.search += '&colour='+el;
			}
			else {
				window.location.search = '?colour='+el;
			}
		}
	});


	if (config.inverted) {
		$('#invert-enable')[0].checked = true;
	}

	$('#invert-enable').change(function() {
		/*jshint validthis: true */
		if (this.checked) {
			if (window.location.search.substr(0,1) === '?') {
				window.location.search = window.location.search + '&invert=1';
			}
			else {
				window.location.search = '?invert=1';
			}
		}
		else {
			window.location.search = window.location.search.replace(/.invert=.+?\&?/, '');
		}
	});
	// show/hide the panes
	$('#left-pane-arrow').click(toggleLeft);

	$('#top-pane-arrow').click(toggleTop);

	$('#right-pane-arrow').click(toggleRight);
	if ($('#left-pane-target').swipeRight) { // IE 9 doesn't support swipe functions
		$('#left-pane-target').swipeRight(toggleLeft);

		$('#right-pane-target').swipeLeft(toggleRight);

		$('#top-pane-target').swipeDown(toggleTop);

		$('#left-pane').swipeLeft(function() {
			collapsePane('left');
		});

		$('#right-pane').swipeRight(function() {
			collapsePane('right');
		});

		$('#bottom-pane-target').swipeUp(function() {
			collapsePane('top');
		});

		$('#cached').swipeDown(function() {
			$('#verbose-hidden').velocity('finish').velocity('slideDown', { duration: 300 });
			$('#dropdown-arrow').addClass('expanded');
		});

		$('#cached').swipeUp(function() {
			$('#verbose-hidden').velocity('finish').velocity('slideUp', { duration: 300 });
			$('#dropdown-arrow').removeClass('expanded');
		});
	}

	$(document).keydown(function(e) {
		if (e.which == 27) { // esc
			$('#settings-modal,#fadeout').velocity('finish').velocity('fadeOut');
		} else if (e.which == 83) { // s
			if ($('#settings-modal').css('display') !== 'block') {
				$('#settings-modal,#fadeout').velocity('finish').velocity('fadeIn');
			} else {
				$('#settings-modal,#fadeout').velocity('finish').velocity('fadeOut');
			}
		} else if (e.which == 69 || e.which == 81) { // e/q
			// fake an onClick event with an el that's either #expand or #collapse
			toggleExpansion({target: {id: (e.which == 69 ? 'expand' : 'collapse')}});
		} else if (e.which == 65 || e.which == 37) { // a/left arrow
			toggleLeft();
		} else if (e.which == 87 || e.which == 38) { // w/up arrow
			toggleTop();
		} else if (e.which == 68 || e.which == 39) { // d/right arrow
			toggleRight();
		}
	});

	if (window.PointerEvent) {
		document.addEventListener('pointerdown', onInteract);
	} else if (window.MSPointerEvent) {
		document.addEventListener('MSPointerDown', onInteract);
	}
	document.addEventListener('mousemove', onInteract);
	document.addEventListener('onclick', onInteract);
	document.addEventListener('touchstart', onInteract);
	screenTapId = setTimeout(onScreenTapTimeout, 5000);

	$('#expand,#collapse').on('click', toggleExpansion);

	if (window.localStorage.expanded === 'true') {
		$('#expand').click();
	}
	window.addEventListener('resize', function() {
		$('#ideal-image-size').html('<strong>Best size (for current window):</strong> ' + window.innerWidth + 'x' + window.innerHeight);
	});
	$('#ideal-image-size').html('<strong>Best size (for current window):</strong> ' + window.innerWidth + 'x' + window.innerHeight);

	var el = document.getElementById('bg-pos-vert-combobox');
	el.addEventListener('change', function() {
		console.log('whee change');
		window.localStorage['bg-vert'] = document.getElementById('bg-pos-vert-combobox').value;
		loadBackgroundImage();
	});
	if (localStorage['bg-vert']) {
		el.selectedIndex = ['top', 'center', 'bottom'].indexOf(localStorage['bg-vert']);
	}

	el = document.getElementById('bg-pos-horiz-combobox');
	el.addEventListener('change', function() {
		window.localStorage['bg-horiz'] = document.getElementById('bg-pos-horiz-combobox').value;
		loadBackgroundImage();
	});
	if (localStorage['bg-horiz']) {
		el.selectedIndex = ['left', 'center', 'right'].indexOf(localStorage['bg-horiz']);
	}

	el = document.getElementById('tile-toggle')
	el.addEventListener('change', function() {
		window.localStorage['bg-repeat'] = document.getElementById('tile-toggle').checked;
		loadBackgroundImage();
	});
	if (localStorage['bg-repeat'] === true) window.localStorage['bg-repeat'].checked = true;
}

function handleUpload() {
	'use strict';
	if ('cached-bg' in window.localStorage) {
		delete window.localStorage['cached-bg'];
		loadBackgroundImage();
		$('#custom-background').html('Choose...');
	}
	else {
		var input = $('<input type="file" accept="image/*">');
		input.on('change', function(e) {
			console.log('loading a file!');
			if (input[0].files && input[0].files[0]) {
				var reader = new FileReader();
				reader.onload = function(e) {
					base64Image(e.target.result, window.innerWidth, window.innerHeight, function (b64) {
						localStorage.setItem('cached-bg', b64);
						loadBackgroundImage();
					});
				};
				reader.readAsDataURL(input[0].files[0]);
				$('#custom-background').html('Clear');
			}
		});
		console.log('requesting upload...');
		input.click();
	}
}

function base64Image(url, width, height, callback) {
	'use strict';
	var img = new Image();

	img.onload = function (evt) {
		var canvas = document.createElement('canvas');

		canvas.width  = img.width; // upload the image without changing its dimensions
		canvas.height = img.height;

		var imgRatio    = img.width / img.height,
		canvasRatio = width / height,
		resultImageH, resultImageW;

		if (imgRatio < canvasRatio) {
			resultImageH = canvas.height;
			resultImageW = resultImageH * imgRatio;
		}
		else {
			resultImageW = canvas.width;
			resultImageH = resultImageW / imgRatio;
		}

		canvas.width  = resultImageW;
		canvas.height = resultImageH;
		canvas.getContext('2d').drawImage(img, 0, 0, resultImageW, resultImageH);
		callback(canvas.toDataURL());
	};

	img.src = url;
}

function loadBackgroundImage() {
	/* jshint -W041 */
	'use strict';
	var el = document.getElementById('i-dont-even');
	if (el != null) {
		document.head.removeChild(el);
	}
	if ('cached-bg' in window.localStorage) {
		var backgroundRep = true;
		console.log(window.localStorage['bg-repeat']);
		if ('bg-repeat' in window.localStorage) {
			console.log('found bg-rep');
			backgroundRep = window.localStorage['bg-repeat'] == 'true';
		}
		var backgroundVertAlign = 'center';
		if ('bg-vert' in window.localStorage) {
			backgroundVertAlign = window.localStorage['bg-vert'];
		}
		var backgroundHorizAlign = 'center';
		if ('bg-horiz' in window.localStorage) {
			backgroundHorizAlign = window.localStorage['bg-horiz'];
		}
		console.log(backgroundRep);
		var c = config.cscheme.bg.slice(1);
		var r = Number('0x'+c.substr(0,2));
		var g = Number('0x'+c.substr(2,2));
		var b = Number('0x'+c.substr(4,2));
		var rgb = 'rgba(' + r + ',' + g + ',' + b + ', 0.5)';
		$('#background-image').addClass('customBg');
		var style = document.createElement('style');
		// TODO why is this innerHTML not innerText wtf firefox
		var css = '#background-image { background: linear-gradient(' + rgb + ',' + rgb + '), #' + c + ' url(' + window.localStorage['cached-bg'] + ');';
		css += 'background-repeat: ' + (backgroundRep === true ? 'repeat' : 'no-repeat') + ';';
		css += 'background-position: ' + backgroundVertAlign + ' ' + backgroundHorizAlign + ';';
		css += '}'
		style.innerHTML = css;
		style.id = 'i-dont-even';
		document.head.appendChild(style);

	} else {
		$('#background-image').removeClass('customBg');
	}
}

	var opts = { //TODO move into updateSidebarStatus
		lines: 7, // The number of lines to draw
		length: 3, // The length of each line
		width: 3, // The line thickness
		radius: 2, // The radius of the inner circle
		scale: 1, // Scales overall size of the spinner
		corners: 1, // Corner roundness (0..1)
		color: '#fff', // #rgb or #rrggbb or array of colors
		opacity: 0.25, // Opacity of the lines
		rotate: 0, // The rotation offset
		direction: 1, // 1: clockwise, -1: counterclockwise
		speed: 1, // Rounds per second
		trail: 34, // Afterglow percentage
		fps: 20, // Frames per second when using setTimeout() as a fallback for CSS
		zIndex: 2e9, // The z-index (defaults to 2000000000)
		className: 'spinner', // The CSS class to assign to the spinner
		top: '-0.25em', // Top position relative to parent
		left: '50%', // Left position relative to parent
		shadow: true, // Whether to render a shadow
		hwaccel: true, // Whether to use hardware acceleration
		position: 'absolute' // Element positioning
	};

function updateSidebarStatus() {
	/* Show load state info for various API data */
	'use strict';
	if (document.readyState !== 'complete') {
		return;
	}
	/* Loading state symbols */
	var tick = '<span class="octicon octicon-check ok"></span>',
		cross = '<span class="octicon octicon-x failed"></span>',
		cached = '<span class="octicon octicon-alert stale"></span>',
		loading = '<span class="idk">…</span>',
		waiting = '[spinner]';
	/* Local variables */
	var belltimesOK = window.belltimes && belltimes.status == 'OK' && belltimes.httpStatus == 200,
		noticesOK = window.notices && window.notices.notices && !window.notices.notices.failure && window.notices.httpStatus == 200,
		timetableOK = window.today && today.httpStatus == 200 && today.timetable,
		belltimesClass = 'ok',
		belltimesText = 'OK',
		belltimesShortText = cross,
		timetableClass = 'failed',
		timetableText = 'Failed',
		timetableShortText = cross,
		noticesClass = 'failed',
		noticesText = 'Failed',
		noticesShortText = cross;
		

	if (belltimesOK) {
		belltimesText = 'OK';
		belltimesClass = 'ok';
		belltimesShortText = tick;
	}

	if (window.todayLoading) {
		timetableText = 'Loading...';
		timetableClass = 'stale';
		timetableShortText = waiting;
	} else if (window.today && window.today.stale) {
		timetableText = 'Cached';
		timetableClass = 'stale';
		timetableShortText = cached;
	} else if (timetableOK) {
		timetableText = 'OK';
		timetableClass = 'ok';
		timetableShortText = tick;
	}
	if (window.noticesLoading) {
		noticesText = 'Loading...';
		noticesClass = 'stale';
		noticesShortText = waiting;
	} else if (noticesOK) {
		noticesText = 'OK';
		noticesClass = 'ok';
		noticesShortText = tick;
	}

	var bells = document.getElementById('belltimes');
	bells.className = belltimesClass;
	bells.innerHTML = belltimesText;

	var timetable = document.getElementById('timetable');
	timetable.className = timetableClass;
	timetable.innerHTML = timetableText;

	var notices = document.getElementById('notices');
	notices.className = noticesClass;
	notices.innerHTML = noticesText;

	document.getElementById('belltimes-short').innerHTML = belltimesShortText;
	if (timetableShortText == waiting) {
		document.getElementById('timetable-short').innerHTML = '';
		new Spinner(opts).spin(document.getElementById('timetable-short'));
	} else {
		document.getElementById('timetable-short').innerHTML = timetableShortText;
	}
	if (noticesShortText == waiting) {
		document.getElementById('notices-short').innerHTML = '';
		new Spinner(opts).spin(document.getElementById('notices-short'));

	} else {
		document.getElementById('notices-short').innerHTML = noticesShortText
	}
	//document.getElementById('shortdata-desc').innerHTML = 'B: <span id="belltimes-short">' + belltimesShortText + '</span> ' +
	//														'T: <span id="timetable-short">' + timetableShortText + '</span> ' +
	//														'N: <span id="notices-short">' + noticesShortText + '</span>'
}

EventBus.on('notices', updateSidebarStatus);
EventBus.on('bells', updateSidebarStatus);
EventBus.on('today', updateSidebarStatus);
;