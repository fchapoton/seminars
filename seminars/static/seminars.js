// from lmfdb.js,
function cleanSubmit(id)
{
  var myForm = document.getElementById(id);
  var allInputs = myForm.getElementsByTagName('input');
  var allSelects = myForm.getElementsByTagName('select');
  var item, i, n = 0;
  for(i = 0; item = allInputs[i]; i++) {
    if (item.getAttribute('name') ) {
        // Special case count so that we strip the default value
        if (!item.value || (item.getAttribute('name') == 'count' && item.value == 50)) {
        item.setAttribute('name', '');
      } else {
        n++;
      }
    }
  }
  for(i = 0; item = allSelects[i]; i++) {
    if (item.getAttribute('name') ) {
      if (!item.value) {
        item.setAttribute('name', '');
      } else {
        n++;
      }
    }
  }
  if (!n) {
    var all = document.createElement('input');
    all.type='hidden';
    all.name='all';
    all.value='1';
    myForm.appendChild(all);
  }
}


function toggle_time(id) {
    var future = $('#future_talks');
    var past = $('#past_talks');
    if (future.is(":visible"))
    {
        if (id == "toggle_to_past") {
            $('.toggler-nav').toggleClass("toggler-active");
            future.hide();
            past.show();
        }
    } else {
        if (id == "toggle_to_future") {
            $('.toggler-nav').toggleClass("toggler-active");
            past.hide();
            future.show();
        }
    }
}


function setCookie(name,value) {
  if (navigator.cookieEnabled) {
    document.cookie = name + "=" + (value || "") + ";path=/";
  }
}
function getCookie(name) {
    if (navigator.cookieEnabled) {
      var nameEQ = name + "=";
      var ca = document.cookie.split(';');
      for(var i=0;i < ca.length;i++) {
          var c = ca[i];
          while (c.charAt(0)==' ') c = c.substring(1,c.length);
          if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length,c.length);
      }
    }
    return null;
}
function eraseCookie(name) {
    document.cookie = name+'=; Max-Age=-99999999;';
}
function addToCookie(item, cookie) {
    var cur_items = getCookie(cookie);
    if (cur_items) {
        cur_items = cur_items + "," + item;
    } else {
        cur_items = item;
    }
    setCookie(cookie, cur_items);
    return cur_items;
}
function removeFromCookie(item, cookie) {
    var cur_items = getCookie(cookie);
    cur_items = cur_items.replace(item, "").replace(",,",",");
    if (cur_items.startsWith(",")) cur_items = cur_items.slice(1);
    if (cur_items.endsWith(",")) cur_items = cur_items.slice(0, -1);
    setCookie(cookie, cur_items);
    return cur_items;
}
function setTopicCookie(topic, value) {
    var cookie = getCookie("topics_dict");
    if (cookie == null) {
        var cur_items = [];
    } else {
        var cur_items = cookie.split(",");
    }
    var new_item = topic + ":" + value.toString();
    var found = false;
    for (let i=0;i<cur_items.length;i++) {
        if (cur_items[i].startsWith(topic + ":")) {
            cur_items[i] = new_item
            found = true;
            break;
        }
    }
    if (!found) {
        cur_items.push(new_item);
    }
    setCookie(cur_items.join(","));
}
function getTopicCookie(topic) {
    var cur_items = getCookie("topics_dict").split(",");
    for (let i=0; i<cur_items.length; i++) {
        if (cur_items[i].startsWith(topic + ":")) {
            return parseInt(cur_items[i].substring(topic.length+1));
        }
    }
    return 0;
}
function getTopicCookieWithValue(value) {
    value = value.toString();
    var cur_items = getCookie("topics_dict").split(",");
    var with_value = [];
    for (var i=0; i<cur_items.length; i++) {
        if (cur_items[i].endsWith(":" + value)) {
            with_value.push(cur_items[i].substring(0, value.length+1));
        }
    }
    return with_value;
}
function subjectFiltering() {
    return $('#enable_subject_filter').is(":checked");
}
function enableSubjectFiltering() {
    setCookie("filter_subject", "1");
    $('#enable_subject_filter').prop("checked", true);
    toggleFilters(null);
}
function topicFiltering() {
    return $('#enable_topic_filter').is(":checked");
}
function enableTopicFiltering() {
    setCookie("filter_topic", "1");
    $('#enable_topic_filter').prop("checked", true);
    toggleFilters(null);
}
function languageFiltering() {
    return $('#enable_language_filter').is(":checked");
}
function enableLanguageFiltering() {
    setCookie("filter_language", "1");
    $('#enable_language_filter').prop("checked", true);
    toggleFilters(null);
}
function calFiltering() {
    return $('#enable_calendar_filter').is(":checked");
}

function setLanguageLinks() {
    var cur_languages = getCookie("languages");
    if (cur_languages == null) {
        setCookie("languages", "");
        cur_languages = "";
        setCookie("filter_language", "0");
    } else {
        $('#enable_language_filter').prop("checked", Boolean(parseInt(getCookie("filter_languages"))));
    }
    if (cur_languages.length > 0) {
        cur_languages = cur_languages.split(",");
        for (var i=0; i<cur_languages.length; i++) {
            $("#langlink-" + cur_languages[i]).addClass("languageselected");
            $(".lang-" + cur_languages[i]).removeClass("language-filtered");
        }
    }
}

function topicFromPair(pairid) {
    return pairid.split("--")[1];
}

function setSubjectLinks() {
    var cur_subjects = getCookie("subjects");
    if (cur_subjects == null) {
        console.log("No subjects!");
        setCookie("subjects", "");
        setCookie("filter_subject", "0");
        //$("#filter-table").hide();
        //$("#welcome-popup").show();
        cur_subjects = "";
    } else {
        $('#enable_subject_filter').prop("checked", Boolean(parseInt(getCookie("filter_subject"))));
    }
    cur_subjects = cur_subjects.split(",");
    for (var i=0; i<cur_subjects.length; i++) {
        $("#subjectlink-" + cur_subjects[i]).prop("checked", true);
        $("#subjectlink-" + cur_subjects[i]).addClass("subjectselected");
        $(".talk.subject-" + cur_subjects[i]).removeClass("subject-filtered");
    }
}
function setTopicLinks() {
    var cur_topics = getCookie("topics");
    $(".talk").addClass("topic-filtered");
    if (cur_topics == null) {
        setCookie("topics", "");
        setCookie("filter_topic", "0");
        // filter_language set in setLanguageLinks(), since we added it after launch
        setCookie("filter_calendar", "0");
        // Set the following in preparation so we don't need to worry about them not existing.
        setCookie("filter_location", "0");
        setCookie("filter_time", "0");
    } else {
        $('#enable_topic_filter').prop("checked", Boolean(parseInt(getCookie("filter_topic"))));
        $('#enable_language_filter').prop("checked", Boolean(parseInt(getCookie("filter_language"))));
        $('#enable_subject_filter').prop("checked", Boolean(parseInt(getCookie("filter_subject"))));
        $('#enable_calendar_filter').prop("checked", Boolean(parseInt(getCookie("filter_calendar"))));
        cur_topics = cur_topics.split(",");
        for (var i=0; i<cur_topics.length; i++) {
            $("#topiclink-" + cur_topics[i]).addClass("topicselected");
            $(".topic-" + cur_topics[i]).removeClass("topic-filtered");
        }
    }
}

function setLinks() {
    if (navigator.cookieEnabled) {
        setSubjectLinks();
        setLanguageLinks();
        setTopicLinks();
        toggleFilters(null);
    }
}

function toggleSubject(id, welcome=false) {
    console.log("id", id);
    var toggler = $("#" + id);
    console.log(id);
    var subject = id.substring(12); // subjectlink-*
    var talks = $(".talk.subject-" + subject);
    if (toggler.hasClass("subjectselected")) {
        toggler.removeClass("subjectselected");
        cur_subjects = removeFromCookie(subject, "subjects").split(",");
        for (i=0; i<cur_subjects.length; i++) {
            talks = talks.not(".subject-" + cur_subjects[i]);
        }
        talks.addClass("subject-filtered");
        if (subjectFiltering()) {
            talks.hide();
            apply_striping();
        }
    } else {
        toggler.addClass("subjectselected");
        cur_subjects = addToCookie(subject, "subjects").split(",");
        if (!welcome && cur_subjects.length == 1) {
            enableSubjectFiltering();
        }
        talks.removeClass("subject-filtered");
        if (subjectFiltering()) {
            // elements may be filtered by other criteria
            talks = talksToShow(talks);
            talks.show();
            apply_striping();
        }
    }
}

function toggleLanguage(id) {
    var toggler = $("#" + id);
    console.log(id);
    var lang = id.substring(9); // langlink-*
    var talks = $(".talk.lang-" + lang);
    if (toggler.hasClass("languageselected")) {
        toggler.removeClass("languageselected");
        cur_langs = removeFromCookie(lang, "languages").split(",");
        for (i=0; i<cur_langs.length; i++) {
            talks = talks.not(".lang-" + cur_langs[i]);
        }
        talks.addClass("language-filtered");
        if (languageFiltering()) {
            talks.hide();
            apply_striping();
        }
    } else {
        toggler.addClass("languageselected");
        cur_langs = addToCookie(lang, "languages").split(",");
        if (cur_langs.length == 1) {
            enableLanguageFiltering();
        }
        talks.removeClass("language-filtered");
        if (languageFiltering()) {
            // elements may be filtered by other criteria
            talks = talksToShow(talks);
            talks.show();
            apply_striping();
        }
    }
}

function toggleTopic(id) {
    var toggler = $("#" + id);
    console.log(id);
    var topic = id.substring(10); // topiclink-*
    var talks = $(".talk.topic-" + topic);
    if (toggler.hasClass("topicselected")) {
        toggler.removeClass("topicselected");
        $("#topictoggle-"+topic).prop("checked", false);
        cur_topics = removeFromCookie(topic, "topics").split(",");
        for (i=0; i<cur_topics.length; i++) {
            talks = talks.not(".topic-" + cur_topics[i]);
        }
        talks.addClass("topic-filtered");
        if (topicFiltering()) {
            talks.hide();
            apply_striping();
        }
    } else {
        toggler.addClass("topicselected");
        $("#topictoggle-"+topic).prop("checked", true);
        cur_topics = addToCookie(topic, "topics").split(",");
        if (cur_topics.length == 1) {
            enableTopicFiltering();
        }
        talks.removeClass("topic-filtered");
        if (topicFiltering()) {
            // elements may be filtered by other criteria
            talks = talksToShow(talks);
            talks.show();
            apply_striping();
        }
    }
}
function manageTopicDAG(togid) {
    var topic = topicFromPair(togid);
    var toggleval = $("#" + togid).val();
    /* Need to add/subtract values from a hidden text input for saving
       and show/hide from a visible div to give current status */
}

function toggleTopicDAG(togid) {
    var to_show = [];
    var to_hide = [];
    console.log(togid);
    var topic = topicFromPair(togid);
    var toggle = $("#" + togid);
    var toggleval = toggle.val();
    console.log(toggleval);
    setTopicCookie(topic, toggleval);
    if (toggleval == 0) {
        $("label.sub_" + topic).css("visibility", "visible");
        $("a.sub_"+topic+",span.sub_"+topic).removeClass("not_toggleable");
        var pane = $("#"+togid+"-pane");
        var is_visible = pane.is(":visible");
        if (!is_visible) {
            var pair = togid.split("--");
            toggleTopicView(pair[0], pair[1]);
        }
        // Need to show rows corresponding to sub-topics.
        // We can't just use $("tgl.sub_"+topic).each(),
        // since some 1s may be under -1s.
        var blocking_toggles = [];
        $('input[value="-1"].tgl3way.sub_'+topic).each(function() {
            blocking_toggles.push(topicFromPair(this.id));
        });
        var show_selector = $('input[value="1"].sub_'+topic);
        for (let i=0; i<blocking_toggles.length; i++) {
            show_selector = show_selector.not(".sub_"+blocking_toggles[i]);
        }
        show_selector.each(function() {
            to_show.push(topicFromPair(this.id));
        });
    } else {
        $("label.sub_" + topic).css("visibility", "hidden");
        if (toggleval == 1) {
            to_show.push(topic);
        } else {
            $("a.sub_"+topic+",span.sub_"+topic).addClass("not_toggleable");
            to_hide.push(topic);
        }
    }
    console.log("show", to_show);
    console.log("hide", to_hide);
    if (to_show.length > 0) {
        var talks = $();
        for (let i=0; i<to_show.length; i++) {
            talks = talks.add(".talk.topic-filtered.topic-" + topic);
        }
        talks.removeClass("topic-filtered");
        if (topicFiltering()) {
            // elements may be filtered by other criteria
            talks = talksToShow(talks);
            talks.show();
            apply_striping();
        }
    }
    if (to_hide.length > 0) {
        var talks = $(".talk.topic-" + topic);
        var cur_topics = getTopicCookieWithValue(1);
        for (let i=0; i<cur_topics.length; i++) {
            talks = talks.not(".topic-" + cur_topics[i]);
        }
        talks.addClass("topic-filtered");
        if (topicFiltering()) {
            talks.hide();
            apply_striping();
        }
    }
}

function manageTopicView(pid, cid) {
    var pane = $("#"+pid+"--"+cid+"-pane");
    var is_visible = pane.is(":visible");
    $("."+pid+"-subpane").hide();
    $("."+pid+"-tlink").removeClass("active");
    if (!is_visible) {
        pane.show();
        $("#"+cid+"-filter-btn").addClass("active");
    }
}
function toggleTopicView(pid, cid) {
    console.log(pid, cid);
    var tid = "#"+pid+"--"+cid;
    var toggle = $(tid);
    var pane = $(tid+"-pane");
    var is_visible = pane.is(":visible");
    $("."+pid+"-subpane").hide();
    $("."+pid+"-tlink").removeClass("active");
    if (!is_visible) {
        pane.show();
        $("#"+cid+"-filter-btn").addClass("active");
        // We need to trigger the change event multiple times since toggleTopic is written assuming the cycle -1 -> 0 -> 1 -> -1
        $(tid).attr('data-chosen', 0);
        if (toggle.val() == "-1") {
            $(tid).val(0)
            $(tid).trigger('change');
        } else if (toggle.val() == "1") {
            $(tid).val(-1)
            $(tid).trigger('change');
            $(tid).val(0)
            $(tid).trigger('change');
        }
    }
}

var filter_menus = ['topic', 'language'];
var filter_classes = [['.topic-filtered', topicFiltering], ['.language-filtered', languageFiltering], ['.calendar-filtered', calFiltering]];
function talksToShow(talks) {
    for (i=0; i<filter_classes.length; i++) {
        if (filter_classes[i][1]()) {
            talks = talks.not(filter_classes[i][0]);
            console.log(talks.length);
        }
    }
    return talks;
}
function filterMenuId(ftype) {
    if (ftype == "topic") {
        return "#root--topic-pane";
    } else {
        return "#"+ftype+"-filter-menu";
    }
}
function filterMenuVisible(ftype) {
    return $(filterMenuId(ftype)).is(":visible");
}
function toggleFilters(id, on_menu_open=false) {
    console.log("filters", id);
    if (id !== null) {
        console.log($('#'+id).is(":checked"));
        var is_enabled = $('#'+id).is(":checked")
        var ftype = id.split("_")[1]
        setCookie("filter_" + ftype, is_enabled ? "1" : "0");
        if (!on_menu_open && is_enabled && !filterMenuVisible(ftype) && !getCookie(ftype+"s")) {
            toggleFilterView(ftype+"-filter-btn");
        }
    }
    var talks = $('.talk');
    console.log(talks.length);
    talks.hide();
    talks = talksToShow(talks);
    talks.show();
    apply_striping();
}
function toggleFilterView(id) {
    // If this filter is not enabled, we enable it
    console.log("filterview", id);
    var ftype = id.split("-")[0];
    var is_enabled = Boolean(parseInt(getCookie("filter_"+ftype)));
    var visible = filterMenuVisible(ftype)
    if (!is_enabled && !visible) {
        var filtid = 'enable_'+ftype+'_filter';
        $('#'+filtid).prop("checked", true);
        toggleFilters(filtid, true);
    }
    if (ftype == "topic" && !visible) {
        $('#topic').attr('data-chosen', 1);
    }
    for (i=0; i<filter_menus.length; i++) {
        var menu = $(filterMenuId(filter_menus[i]));
        var link = $("#"+filter_menus[i]+"-filter-btn");
        if (ftype == filter_menus[i]) {
            menu.slideToggle(150);
            link.toggleClass("active");
        } else {
            menu.slideUp(150);
            link.removeClass("active");
        }
    }
}

function apply_striping() {
  $('#browse-talks tbody tr:visible:odd').css('background', '#E3F2FD');
  $('#browse-talks tbody tr:visible:even').css('background', 'none');
}

function tickClock() {
    var curtime = $("#curtime").text();
    var hourmin = curtime.split(":");
    hourmin[1] = parseInt(hourmin[1]) + 1;
    if (hourmin[1] == 60) {
        hourmin[1] = 0;
        hourmin[0] = parseInt(hourmin[0]) + 1;
        if (hourmin[0] == 24) hourmin[0] = 0;
        hourmin[0] = hourmin[0].toString();
    }
    hourmin[1] = hourmin[1].toString().padStart(2, '0');
    curtime = hourmin.join(":");
    $("#curtime").text(curtime);
}

var selectPureClassNames = {
    select: "select-pure__select",
    dropdownShown: "select-pure__select--opened",
    multiselect: "select-pure__select--multiple",
    label: "select-pure__label",
    placeholder: "select-pure__placeholder",
    dropdown: "select-pure__options",
    option: "select-pure__option",
    autocompleteInput: "select-pure__autocomplete",
    selectedLabel: "select-pure__selected-label",
    selectedOption: "select-pure__option--selected",
    placeholderHidden: "select-pure__placeholder--hidden",
    optionHidden: "select-pure__option--hidden",
};
function makeTopicSelector(topicOptions, initialTopics) {
    function callback_topics(value) {
        $('input[name="topics"]')[0].value = '[' + value + ']';
    }
    return new SelectPure("#topic_selector", {
        onChange: callback_topics,
        options: topicOptions,
        multiple: true,
        autocomplete: true,
        icon: "fa fa-times",
        inlineIcon: false,
        value: initialTopics,
        classNames: selectPureClassNames,
    });
}
function defaultLanguage() {
    var languages = getCookie("languages");
    if (!languages) {
        return "en";
    } else {
        languages = languages.split(",");
        if (languages.includes("en")) {
            return "en";
        } else {
            languages.sort();
            return languages[0];
        }
    }
}

function makeInstitutionSelector(instOptions, initialInstitutions) {
    function callback_institutions(value) {
        $('input[name="institutions"]')[0].value = '[' + value + ']';
    }
    return new SelectPure("#institution_selector", {
        onChange: callback_institutions,
        options: instOptions,
        multiple: true,
        autocomplete: true,
        icon: "fa fa-times",
        inlineIcon: false,
        value: initialInstitutions,
        classNames: selectPureClassNames,
    });
}
function makeLanguageSelector(langOptions, initialLanguage) {
    function callback_language(value) {
        $('input[name="language"]').value = value;
    }
    return new SelectPure("#language_selector", {
        onChange: callback_language,
        options: langOptions,
        autocomplete: true,
        value: initialLanguage,
        classNames: selectPureClassNames,
    });
}
function makeSubjectSelector(subjOptions, initialSubjects) {
    function callback_subjects(value) {
      // hidden inputs by default don't trigger a change event
        $('input[name="subjects"]').val('[' + value + ']').trigger('change');
    }
    return new SelectPure("#subject_selector", {
        onChange: callback_subjects,
        options: subjOptions,
        multiple: true,
        autocomplete: true,
        icon: "fa fa-times",
        inlineIcon: false,
        value: initialSubjects,
        classNames: selectPureClassNames,
    });
}

function copySourceOfId(id) {
  var copyText = $("#"+id);
  copyText.select();
  document.execCommand("copy");
  console.log("Copied!");
  copyText.notify("Copied!", {className: "success", position:"bottom right" });
}

function displayCookieBanner() {
    console.log("showing banner");
    $.notify.addStyle('banner', {
        html: "<div><div class='message' data-notify-html='message'/><div><button class='yes' data-notify-text='button'></button></div></div></div>",
    });

    //listen for click events from this style
    $(document).on('click', '.notifyjs-banner-base .yes', function() {
        //hide notification
        $(this).trigger('notify-hide');
        setCookie("cookie_banner", "nomore");
    });
    $.notify({
        message: 'This website uses cookies to improve your experience.',
        button: 'Got it!'
    }, {
        style: 'banner',
        position: 'b r',
        autoHide: false,
        clickToHide: false
    });
}

$(document).ready(function () {
    if (navigator.cookieEnabled && !document.cookie.includes('cookie_banner')) {
        displayCookieBanner();
    }

    setLinks();

    $('.toggler-nav').click(
        function (evt) {
            evt.preventDefault();
            toggle_time(this.id);
            return false;
        });
    $('.subject_toggle').click(
        function (evt) {
            evt.preventDefault();
            toggleSubject(this.id);
        });
    /*$('.welcome_toggle').click(
        function (evt) {
            evt.preventDefault();
            toggleSubject(this.id, true);
        });*/
    /*$('.topic_toggle').click(
        function (evt) {
            evt.preventDefault();
            toggleTopic(this.id);
        });*/
    $('.language_toggle').click(
        function (evt) {
            evt.preventDefault();
            toggleLanguage(this.id);
        });

    var today = new Date();
    var minute = today.getMinutes();
    var millisecond = 1000 * today.getSeconds() + today.getMilliseconds();
    var displayed_minute = parseInt($("#curtime").text().split(":")[1]);
    // We might have passed a minute barrier between the server setting the time and the page finishing loading
    // Because of weird time zones (the user time preference may not be their local clock time),
    // we only do something if the minute is offset by 1 or 2 (for a super-slow page load)
    if (minute == displayed_minute + 1) {
        tickClock();
    } else if (minute == displayed_minute + 2) {
        tickClock(); tickClock();
    }
    setTimeout(function() {
        tickClock();
        // update the clock in the top right every 60 seconds
        setInterval(function() {
          tickClock();
        }, 60000);
    }, 60000 - millisecond);
});

$(document).ready(function() {
  dr = $("input[name='daterange']")
  var beginningoftime = 'January 1, 2020';
  var endoftime = 'January 1, 2050';
  var start = moment();
  var end = moment().add(6, 'days');
  if( dr.length > 0 ) {
    var drval = dr[0].value;
    if( drval.includes('-') ) {
      var se = drval.split('-');
      start = se[0].trim();
      end = se[1].trim();
    } else {
      start = beginningoftime;
      end = endoftime;
    }
    if(start == '') {
      start = beginningoftime;
    }
    if(end == '') {
      end = endoftime;
    }
  }


  function cd(start, end, label) {
      if(start.format('MMMM D, YYYY') == beginningoftime){
        start = '';
      } else {
        start = start.format('MMMM D, YYYY')
      }
      if(end.format('MMMM D, YYYY') == endoftime) {
        end = '';
      } else {
        end =  end.format('MMMM D, YYYY')
      }
      // everything is a string from now on
      if(start == "Invalid date") {
        start = ''
      }
      if(end == "Invalid date") {
        end = ''
      }
      if(start == '' && end == '') {
        $('#daterange').val('');
      } else {
        $('#daterange').val(start + ' - ' + end);
      }
    };


  $('input[name="daterange"]').on('cancel.daterangepicker', function(ev, picker) {
      $(this).val('');
  });

    $('#daterange').daterangepicker({
        startDate: start,
        endDate: end,
        autoUpdateInput: false,
        opens: "center",
        drops: "down",
        ranges: {
           'No restriction': [beginningoftime, endoftime],
           'Future': [moment(), endoftime],
           'Past': [beginningoftime, moment()],
           'Today': [moment(), moment()],
           'Next 7 Days': [moment(), moment().add(6, 'days')],
           'Next 30 Days': [moment(), moment().add(29, 'days')],
        },
        locale: {
          format: "MMMM D, YYYY",
        },
      },
      cd
    );

    //cb(start, end);


});



//handling subscriptions
$(document).ready(function(){
    $("input.subscribe").change(function(evt) {
        var elem = $(this);
        function success(msg) {
          // this is the row
          var row = elem[0].parentElement.parentElement;
          $(row).notify(msg, {className: "success", position:"right" });
          //evt.stopPropagation();
          var name = elem[0].name;
          // is a seminar
          if( ! name.includes('/') ){
            // apply the same thing to the talks of that seminar
            foo = $('input.subscribe[id^="tlg' + name +'--"]');
            $('input.subscribe[id^="tlg' + name +'--"]').val(elem.val());
            $('input.subscribe[id^="tlg' + name +'--"]').attr('data-chosen', elem.val());
          } else {
            // for the browse page
            if( elem.val() == "1" ) {
              $(row).removeClass("calendar-filtered");
            } else {
              $(row).addClass("calendar-filtered");
            }
          }
        }
        function error(xhr) {
          // this is the row
          var msg = xhr.responseText
          console.log(msg);
          $(elem[0].parentElement.parentElement).notify(msg, {className: "error", position:"right" });
          // revert
          evt.stopPropagation();
          elem.val(-parseInt(elem.val()));
          elem.attr('data-chosen', elem.val());
        }
        console.log($(this).val());
        if($(this).val() == "1") {
            $.ajax({
              url: '/user/subscribe/' +  $(this)[0].name,
              success: success,
              error: error
            });
              console.log('/user/subscribe/' +  $(this)[0].name);
        } else {
          $.ajax({
            url: '/user/unsubscribe/' +  $(this)[0].name,
            success: success,
            error: error
          });
            console.log('/user/unsubscribe/' +  $(this)[0].name);
        }
    });
});



function checkpw() {
  var match = "Too short";
  if($("#pw1").val().length < 8){
    "Too short (less than 8 characters)";
    $("#pw1status").html("Too short (less than 8 characters)");
    $("#pw2status").html("");
  } else {
    $("#pw1status").html("");
  }

  if($("#pw1").val() == $("#pw2").val()) {
    $("#pw2status").html("");
  } else {
    $("#pw2status").html("Not matching");
  }
}


