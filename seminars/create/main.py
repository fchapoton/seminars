# -*- coding: utf-8 -*-
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user
from seminars.users.main import email_confirmed_required
from seminars import db
from seminars.create import create
from seminars.utils import (
    adapt_datetime,
    clean_language,
    clean_subjects,
    clean_topics,
    flash_warning,
    format_errmsg,
    format_input_errmsg,
    localize_time,
    process_user_input,
    sanity_check_times,
    short_weekdays,
    show_input_errors,
    timezones,
    weekdays,
    midnight,
    daytime_minutes,
    daytimes_early,
    daytimes_long,
    date_and_daytimes_to_times,
    maxlength,
    similar_urls,
    format_warning,
)
from seminars.seminar import (
    WebSeminar,
    can_edit_seminar,
    seminars_lookup,
    seminars_search,
)
from seminars.talk import (
    WebTalk,
    can_edit_talk,
    talks_lookup,
    talks_lucky,
    talks_max,
    talks_search,
)
from seminars.institution import (
    WebInstitution,
    can_edit_institution,
    clean_institutions,
    institution_known,
    institution_types,
    institutions,
)
from seminars.lock import get_lock
from seminars.users.pwdmanager import ilike_query, ilike_escape, userdb
from lmfdb.utils import flash_error
from lmfdb.backend.utils import IdentifierWrapper
from psycopg2.sql import SQL
from datetime import datetime, timedelta
from math import ceil
from dateutil.parser import parse as parse_time
import pytz

SCHEDULE_LEN = 15  # Number of weeks to show in edit_seminar_schedule


@create.route("manage/")
@email_confirmed_required
def index():
    # TODO: use a join for the following query
    seminars = {}
    conferences = {}
    deleted_seminars = []
    deleted_talks = []

    def key(elt):
        role_key = {"organizer": 0, "curator": 1, "creator": 3}
        return (role_key[elt[1]], elt[0].name)

    for rec in db.seminar_organizers.search({"email": ilike_query(current_user.email)}, ["seminar_id", "curator"]):
        seminar_id = rec["seminar_id"]
        role = "curator" if rec["curator"] else "organizer"
        # don't waste time loading deleted talks
        if not seminars_lookup(seminar_id, projection="shortname", objects=False):
            continue
        seminar = WebSeminar(seminar_id)
        pair = (seminar, role)
        if seminar.is_conference:
            conferences[seminar_id] = pair
        else:
            seminars[seminar_id] = pair
    role = "creator"
    for seminar_id in seminars_search({"owner": ilike_query(current_user.email)}, "shortname", include_deleted=True):
        if seminar_id not in seminars and seminar_id not in conferences:
            seminar = WebSeminar(seminar_id, deleted=True)  # allow deleted
            pair = (seminar, role)
            if seminar.deleted:
                deleted_seminars.append(seminar)
            elif seminar.is_conference:
                conferences[seminar_id] = pair
            else:
                seminars[seminar_id] = pair
    seminars = sorted(seminars.values(), key=key)
    conferences = sorted(conferences.values(), key=key)
    deleted_seminars.sort(key=lambda sem: sem.name)
    for seminar_id, seminar_ctr in db._execute(
        # ~~* is case insensitive amtch
        SQL(
            """
SELECT DISTINCT ON ({Ttalks}.{Cseminar_id}, {Ttalks}.{Cseminar_ctr}) {Ttalks}.{Cseminar_id}, {Ttalks}.{Cseminar_ctr}
FROM {Ttalks} INNER JOIN {Tsems} ON {Ttalks}.{Cseminar_id} = {Tsems}.{Csname} INNER JOIN {Torgs} ON {Ttalks}.{Cseminar_id} = {Torgs}.{Cseminar_id}
WHERE ({Tsems}.{Cowner} ~~* %s OR {Torgs}.{Cemail} ~~* %s) AND {Ttalks}.{Cdel} = %s AND {Tsems}.{Cdel} = %s
            """
        ).format(
            Ttalks=IdentifierWrapper("talks"),
            Tsems=IdentifierWrapper("seminars"),
            Torgs=IdentifierWrapper("seminar_organizers"),
            Cseminar_id=IdentifierWrapper("seminar_id"),
            Cseminar_ctr=IdentifierWrapper("seminar_ctr"),
            Csname=IdentifierWrapper("shortname"),
            Cowner=IdentifierWrapper("owner"),
            Cemail=IdentifierWrapper("email"),
            Cdel=IdentifierWrapper("deleted"),
        ),
        [ilike_escape(current_user.email), ilike_escape(current_user.email), True, False],
    ):
        talk = WebTalk(seminar_id, seminar_ctr, deleted=True)
        deleted_talks.append(talk)
    deleted_talks.sort(key=lambda talk: (talk.seminar.name, talk.start_time))

    manage = "Manage" if current_user.is_organizer else "Create"
    return render_template(
        "create_index.html",
        seminars=seminars,
        conferences=conferences,
        deleted_seminars=deleted_seminars,
        deleted_talks=deleted_talks,
        institution_known=institution_known,
        institutions=institutions(),
        maxlength=maxlength,
        section=manage,
        subsection="home",
        title=manage,
        user_is_creator=current_user.is_creator,
    )


@create.route("edit/seminar/", methods=["GET", "POST"])
@email_confirmed_required
def edit_seminar():
    if request.method == "POST":
        data = request.form
    else:
        data = request.args
    shortname = data.get("shortname", "")
    new = data.get("new") == "yes"
    notsimilar = data.get("similar") == "no"
    resp, seminar = can_edit_seminar(shortname, new)
    if resp is not None:
        return resp
    title = "Create series" if new else "Edit series"
    manage = "Manage" if current_user.is_organizer else "Create"
    if new:
        errmsgs = []
        subjects = clean_subjects(data.get("subjects"))
        if not subjects:
            errmsgs.append("Please select at least one subject")
        seminar.name = data.get("name", "")
        if not seminar.name:
            errmsgs.append("Seminar name is required.")
        elif len(seminar.name) < 3:
            errmsgs.append(format_errmsg("Seminar name %s is too short, at least three chracters are required.", seminar.name))
        if errmsgs:
            return show_input_errors(errmsgs)
        seminar.is_conference = process_user_input(data.get("is_conference"), "is_conference", "boolean", False)
        seminar.subjects = subjects
        seminar.institutions = clean_institutions(data.get("institutions"))
        if seminar.institutions:
            seminar.timezone = db.institutions.lookup(seminar.institutions[0], "timezone")
        if not notsimilar:
            query = {'is_conference': seminar.is_conference, 'name': {"$ilike": '%' + seminar.name + '%'}}
            similar = [s for s in seminars_search(query)]
            # When checking for simialr series, don't require an exact match on subjects/institutions
            # match anything with institutions not set or with an institution in common, and only require a subject in common
            if seminar.institutions:
                similar = [s for s in similar if not s.institutions or set(seminar.institutions).intersection(set(s.institutions))]
            if seminar.subjects:
                similar = [s for s in similar if set(seminar.subjects).intersection(set(s.subjects))]
            if similar:
                return render_template(
                    "show_similar.html",
                    newseminar=seminar,
                    title=title,
                    section=manage,
                    subsection="home",
                    similar=similar,
                )

    lock = get_lock(shortname, data.get("lock"))
    return render_template(
        "edit_seminar.html",
        seminar=seminar,
        title=title,
        section=manage,
        subsection="editsem",
        institutions=institutions(),
        short_weekdays=short_weekdays,
        timezones=timezones,
        maxlength=maxlength,
        lock=lock,
    )


@create.route("delete/seminar/<shortname>", methods=["GET", "POST"])
@email_confirmed_required
def delete_seminar(shortname):
    try:
        seminar = WebSeminar(shortname, deleted=True)
    except ValueError as err:
        flash_error(str(err))
        return redirect(url_for(".index"), 302)
    manage = "Manage" if current_user.is_organizer else "Create"
    lock = get_lock(shortname, request.args.get("lock"))

    def failure():
        return render_template(
            "edit_seminar.html",
            seminar=seminar,
            title="Edit series",
            section=manage,
            subsection="editsem",
            institutions=institutions(),
            weekdays=weekdays,
            timezones=timezones,
            maxlength=maxlength,
            lock=lock,
        )

    if not seminar or not seminar.user_can_delete():
        flash_error("Only the owner of the seminar can delete it")
        return failure()

    raw_data = request.form if request.method == "POST" else {}
    if seminar.deleted:
        if raw_data.get("submit") == "revive":
            return redirect(url_for(".revive_seminar", shortname=shortname), 302)
        if raw_data.get("submit") == "permdelete":
            return redirect(url_for(".permdelete_seminar", shortname=shortname), 302)
    else:
        if raw_data.get("submit") == "cancel":
            return redirect(url_for(".edit_seminar", shortname=shortname), 302)
        if raw_data.get("submit") == "delete":
            if seminar.delete():
                flash("%s %s deleted." % (seminar.series_type, shortname))
            else:
                flash_error("You do not have permission to delete the %s %s."% (seminar.series_type, seminar.name))
                return failure()
        if raw_data.get("submit") == "permdelete":
            return redirect(url_for(".permdelete_seminar", shortname=shortname), 302)
    if seminar.deleted:
        talks = list(talks_search({"seminar_id": shortname, "deleted_with_seminar": True}, sort=["start_time"], include_deleted=True))
    else:
        talks = list(talks_search({"seminar_id": shortname}, sort=["start_time"]))

    return render_template(
        "deleted_seminar.html",
        shortname=shortname,
        seminar=seminar,
        talks=talks,
        title="Delete series",
        section="Manage",
    )


@create.route("deleted/seminar/<shortname>")
@email_confirmed_required
def deleted_seminar(shortname):
    try:
        seminar = WebSeminar(shortname, deleted=True)
    except ValueError as err:
        flash_error(str(err))
        return redirect(url_for(".index"), 302)
    return render_template("deleted_seminar.html", seminar=seminar, title="Deleted")


@create.route("revive/seminar/<shortname>")
@email_confirmed_required
def revive_seminar(shortname):
    seminar = seminars_lookup(shortname, include_deleted=True)

    if seminar is None:
        flash_error("Series %s does not exist (it may have been deleted permanently).", shortname)
        return redirect(url_for(".index"), 302)
    if not current_user.is_subject_admin(seminar) and seminar.owner != current_user:
        flash_error("You do not have permission to revive %s %s", seminar.series_type, shortname)
        return redirect(url_for(".index"), 302)
    if not seminar.deleted:
        flash_error("%s %s does not need to be revived, it is not marked as deleted.", seminar.series_type.capitalize(), shortname)
    else:
        db.seminars.update({"shortname": shortname}, {"deleted": False})
        db.talks.update({"seminar_id": shortname, "deleted_with_seminar":True}, {"deleted": False})
        flash(
            "%s %s revived.  Note that any users that were subscribed no longer are."
            % (seminar.series_type, shortname)
        )
    return redirect(url_for(".edit_seminar", shortname=shortname), 302)


@create.route("permdelete/seminar/<shortname>")
@email_confirmed_required
def permdelete_seminar(shortname):
    seminar = seminars_lookup(shortname, include_deleted=True)

    if seminar is None:
        flash_error("%s %s not found (it may have already been permanently deleted).", seminar.series_type.capitalize(), shortname)
        return redirect(url_for(".index"), 302)
    if not current_user.is_subject_admin(seminar) and seminar.owner != current_user:
        flash_error("Only the owner of the %s %s can permanently delete it.", seminar.series_type, shortname)
        return redirect(url_for(".index"), 302)
    db.seminars.delete({"shortname": shortname})
    db.seminar_organizers.delete({"seminar_id": shortname})
    db.talks.delete({"seminar_id": shortname})
    flash("%s %s deleted." % (seminar.series_type, shortname))
    return redirect(url_for(".index"), 302)


@create.route("delete/talk/<seminar_id>/<int:seminar_ctr>", methods=["GET", "POST"])
@email_confirmed_required
def delete_talk(seminar_id, seminar_ctr):
    try:
        talk = WebTalk(seminar_id, seminar_ctr, deleted=True)
    except ValueError as err:
        flash_error(str(err))
        return redirect(url_for(".edit_seminar_schedule", shortname=seminar_id), 302)

    def failure():
        return render_template(
            "edit_talk.html",
            talk=talk,
            seminar=talk.seminar,
            title="Edit talk",
            section="Manage",
            subsection="edittalk",
            institutions=institutions(),
            timezones=timezones,
            maxlength=maxlength,
        )

    if not talk.user_can_delete():
        flash_error("Only the organizers of a seminar can delete talks in it")
        return failure()

    raw_data = request.form if request.method == "POST" else {}

    if talk.deleted:
        if raw_data.get("submit") == "revive":
            return redirect(url_for(".revive_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr), 302)
        if raw_data.get("submit") == "permdelete":
            return redirect(url_for(".permdelete_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr), 302)
    else:
        if raw_data.get("submit") == "cancel":
            return redirect(url_for(".edit_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr), 302)
        if raw_data.get("submit") == "delete":
            if talk.delete():
                flash("Talk deleted.")
            else:
                flash_error("You do not have permission to delete this talk.")
                return failure()
        if raw_data.get("submit") == "permdelete":
            return redirect(url_for(".permdelete_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr), 302)

    return render_template(
        "deleted_talk.html",
        seminar_id=seminar_id,
        seminar_ctr=seminar_ctr,
        seminar=talk.seminar,
        talk=talk,
        title="Delete talk",
        section="Manage",
    )


@create.route("revive/talk/<seminar_id>/<int:seminar_ctr>")
@email_confirmed_required
def revive_talk(seminar_id, seminar_ctr):
    talk = talks_lookup(seminar_id, seminar_ctr, include_deleted=True)

    if talk is None:
        flash_error("Talk %s/%s does not exist (perhaps it was permanently deleted).", seminar_id, seminar_ctr)
        return redirect(url_for(".edit_seminar_schedule", shortname=seminar_id), 302)
    if not talk.user_can_delete():
        flash_error("You do not have permission to revive this talk.")
        return redirect(url_for(".index"), 302)
    if not talk.deleted:
        flash_error("Talk %s/%s does not need to be revived, it is not marked as deleted.", seminar_id, seminar_ctr)
        return redirect(url_for(".edit_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr), 302)
    else:
        db.talks.update({"seminar_id": seminar_id, "seminar_ctr": seminar_ctr}, {"deleted": False})
        flash("Talk revived.  Note that any users who were subscribed no longer are.")
        return redirect(url_for(".edit_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr), 302)


@create.route("permdelete/talk/<seminar_id>/<int:seminar_ctr>")
@email_confirmed_required
def permdelete_talk(seminar_id, seminar_ctr):
    talk = talks_lookup(seminar_id, seminar_ctr, include_deleted=True)

    if talk is None:
        flash_error("Talk %s/%s does not exist (perhaps it was permanently deleted).", seminar_id, seminar_ctr)
        return redirect(url_for(".edit_seminar_schedule", shortname=seminar_id), 302)
    if not talk.user_can_delete():
        flash_error("You do not have permission to permanently delete this talk.")
        return redirect(url_for(".index"), 302)
    if not talk.deleted:
        flash_error("You must delete talk %s/%s first.", seminar_id, seminar_ctr)
        return redirect(url_for(".edit_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr), 302)
    else:
        db.talks.delete({"seminar_id": seminar_id, "seminar_ctr": seminar_ctr})
        flash("Talk %s/%s has been permanently deleted." % (seminar_id, seminar_ctr))
        return redirect(url_for(".edit_seminar_schedule", shortname=seminar_id), 302)


@create.route("save/seminar/", methods=["POST"])
@email_confirmed_required
def save_seminar():
    raw_data = request.form
    shortname = raw_data["shortname"]
    new = raw_data.get("new") == "yes"
    resp, seminar = can_edit_seminar(shortname, new)
    if resp is not None:
        return resp
    if raw_data.get("submit") == "cancel":
        if new:
            return redirect(url_for(".index"), 302)
        flash("Changes discarded")
        return redirect(url_for(".edit_seminar", shortname=shortname), 302)
    if raw_data.get("submit") == "delete":
        return redirect(url_for(".delete_seminar", shortname=shortname), 302)

    errmsgs = []
    if seminar.new:
        data = {
            "shortname": shortname,
            "display": current_user.is_creator,
            "owner": current_user.email,
        }
    else:
        data = {
            "shortname": shortname,
            "display": seminar.display,
            "owner": seminar.owner,
        }
    # Have to get time zone first
    data["timezone"] = tz = raw_data.get("timezone")
    tz = pytz.timezone(tz)
    for col in db.seminars.search_cols:
        if col in data:
            continue
        typ = db.seminars.col_type[col]
        ### Hack to be removed ###
        if col.endswith("time") and typ == "timestamp with time zone":
            typ = "time"
        try:
            val = raw_data.get(col, "")
            data[col] = None  # make sure col is present even if process_user_input fails
            data[col] = process_user_input(val, col, typ, tz)
        except Exception as err:  # should only be ValueError's but let's be cautious
            errmsgs.append(format_input_errmsg(err, val, col))
    if not data["name"]:
        errmsgs.append("The name cannot be blank")
    elif len(data["name"]) < 3:
        errmsgs.append("Name too short, must be at least three characters.")
    if data["is_conference"] and data["start_date"] and data["end_date"] and data["end_date"] < data["start_date"]:
        errmsgs.append("End date cannot precede start date")
    if data["per_day"] is not None and data["per_day"] < 1:
        errmsgs.append(format_input_errmsg("integer must be positive", data["per_day"], "per_day"))
    if data["is_conference"] and (not data["start_date"] or not data["end_date"]):
        errmsgs.append("Please specify the start and end dates of your conference (you can change these later if needed).")

    if data["is_conference"] and not data["per_day"]:
        errmsgs.append("Please specify the typical number of talks on each day of your conference (a rough guess is fine).")

    data["institutions"] = clean_institutions(data.get("institutions"))
    data["topics"] = clean_topics(data.get("topics"))
    data["language"] = clean_language(data.get("language"))
    data["subjects"] = clean_subjects(data.get("subjects"))
    if not data["subjects"]:
        errmsgs.append(format_errmsg("Please select at least one subject."))
    if not data["timezone"] and data["institutions"]:
        # Set time zone from institution
        data["timezone"] = WebInstitution(data["institutions"][0]).timezone
    data["weekdays"] = []
    data["time_slots"] = []
    if data["frequency"]:
        for i in range(maxlength["time_slots"]):
            weekday = daytimes = None
            try:
                col = "weekday" + str(i)
                val = raw_data.get(col, "")
                weekday = process_user_input(val, col, "weekday_number", tz)
                col = "time_slot" + str(i)
                val = raw_data.get(col, "")
                daytimes = process_user_input(val, col, "daytimes", tz)
            except Exception as err:  # should only be ValueError's but let's be cautious
                errmsgs.append(format_input_errmsg(err, val, col))
            if weekday is not None and daytimes is not None:
                data["weekdays"].append(weekday)
                data["time_slots"].append(daytimes)
                if daytimes_early(daytimes):
                    flash_warning(
                        "Time slot %s includes early AM hours, please correct if this is not intended (use 24-hour time format).",
                        daytimes,
                    )
                elif daytimes_long(daytimes):
                    flash_warning(
                        "Time slot %s is longer than 8 hours, please correct if this is not intended.",
                        daytimes,
                )
        if not data["weekdays"]:
            errmsgs.append('You must specify at least one time slot (or set periodicty to "no fixed schedule").')
        if len(data["weekdays"]) > 1:
            x = sorted(
                list(zip(data["weekdays"], data["time_slots"])),
                key=lambda t: t[0] * 24 * 60 + daytime_minutes(t[1].split("-")[0]),
            )
            data["weekdays"], data["time_slots"] = [t[0] for t in x], [t[1] for t in x]
    else:
        data["weekdays"] = []
        data["time_slots"] = []
    organizer_data = []
    contact_count = 0
    for i in range(10):
        D = {"seminar_id": seminar.shortname}
        for col in db.seminar_organizers.search_cols:
            if col in D:
                continue
            name = "org_%s%s" % (col, i)
            typ = db.seminar_organizers.col_type[col]
            try:
                val = raw_data.get(name, "")
                D[col] = None  # make sure col is present even if process_user_input fails
                D[col] = process_user_input(val, col, typ, tz)
            except Exception as err:  # should only be ValueError's but let's be cautious
                errmsgs.append(format_input_errmsg(err, val, col))
        if D["homepage"] or D["email"] or D["full_name"]:
            if not D["full_name"]:
                errmsgs.append(format_errmsg("Organizer name cannot be left blank"))
            D["order"] = len(organizer_data)
            # WARNING the header on the template says organizer
            # but it sets the database column curator, so the
            # boolean needs to be inverted
            D["curator"] = not D["curator"]
            if not errmsgs and D["display"] and D["email"] and not D["homepage"]:
                flash_warning(
                    "The email address %s of organizer %s will be publicly visible.<br>%s",
                    D["email"],
                    D["full_name"],
                    "Set homepage or disable display to prevent this.",
                ),
            if D["email"]:
                r = db.users.lookup(D["email"])
                if r and r["email_confirmed"]:
                    if D["full_name"] != r["name"]:
                        flash_warning(
                            format_warning(
                                "Organizer name %s does not match the name %s of the account with email address %s.<br>Please verify that you have spelled the name correctly.",
                                D["full_name"],
                                r["name"],
                                D["email"],
                            )
                        )
                    if D["homepage"] and r["homepage"] and not similar_urls(D["homepage"], r["homepage"]):
                        flash_warning(
                            "The homepage %s does not match the homepage %s of the account with email address %s, please correct if unintended.",
                            D["homepage"],
                            r["homepage"],
                            D["email"],
                        )
                    if D["display"]:
                        contact_count += 1

            organizer_data.append(D)
    if contact_count == 0:
        errmsgs.append(
            format_errmsg(
                "There must be at least one displayed organizer or curator with a %s so that there is a contact for this listing.<br>%s<br>%s",
                "confirmed email",
                "This email will not be visible if homepage is set or display is not checked, it is used only to identify the organizer's account.",
                "If none of the organizers has a confirmed account, add yourself and leave the organizer box unchecked.",
            )
        )
    # Don't try to create new_version using invalid input
    if errmsgs:
        return show_input_errors(errmsgs)
    else:  # to make it obvious that these two statements should be together
        new_version = WebSeminar(shortname, data=data, organizer_data=organizer_data)

    # Warnings
    if not data["topics"]:
        flash_warning(
            "This series has no topics selected; don't forget to set the topics for each new talk individually."
        )
    if seminar.new or new_version != seminar:
        new_version.save()
        edittype = "created" if new else "edited"
        flash("Series %s successfully!" % edittype)
    elif seminar.organizer_data == new_version.organizer_data:
        flash("No changes made to series.")
    if seminar.new or seminar.organizer_data != new_version.organizer_data:
        new_version.save_organizers()
        if not seminar.new:
            flash("Series organizers updated!")
    return redirect(url_for(".edit_seminar", shortname=shortname), 302)


@create.route("edit/institution/", methods=["GET", "POST"])
@email_confirmed_required
def edit_institution():
    if request.method == "POST":
        data = request.form
    else:
        data = request.args
    shortname = data.get("shortname", "")
    if data.get("cancel") == "yes":
        flash("Changes discarded.")
    new = data.get("new") == "yes"
    name = data.get("name", "")
    resp, institution = can_edit_institution(shortname, name, new)
    if resp is not None:
        return resp
    if new:
        institution.name = data.get("name", "")
    # Don't use locks for institutions since there's only one non-admin able to edit.
    title = "Create institution" if new else "Edit institution"
    return render_template(
        "edit_institution.html",
        institution=institution,
        institution_types=institution_types,
        timezones=timezones,
        title=title,
        section="Manage",
        subsection="editinst",
        maxlength=maxlength,
    )


@create.route("save/institution/", methods=["POST"])
@email_confirmed_required
def save_institution():
    raw_data = request.form
    shortname = raw_data["shortname"]
    new = raw_data.get("new") == "yes"
    name = raw_data.get("name", "")
    resp, institution = can_edit_institution(shortname, name, new)
    if resp is not None:
        return resp
    if raw_data.get("submit") == "cancel":
        if new:
            return redirect(url_for("list_institutions"), 302)
        flash("Changes discarded")
        return redirect(url_for(".edit_institution", shortname=shortname), 302)

    data = {}
    data["timezone"] = tz = raw_data.get("timezone", "UTC")
    tz = pytz.timezone(tz)
    errmsgs = []
    for col in db.institutions.search_cols:
        if col in data:
            continue
        typ = db.institutions.col_type[col]
        try:
            val = raw_data.get(col, "")
            data[col] = None  # make sure col is present even if process_user_input fails
            data[col] = process_user_input(val, col, typ, tz)
            if col == "admin":
                userdata = userdb.lookup(data[col])
                if userdata is None:
                    if not data[col]:
                        errmsgs.append("You must specify the email address of the maintainer.")
                        continue
                    else:
                        errmsgs.append(format_errmsg("User %s does not have an account on this site", data[col]))
                        continue
                elif not userdata["creator"]:
                    errmsgs.append(format_errmsg("User %s has not been endorsed", data[col]))
                    continue
                if not userdata["homepage"]:
                    if current_user.email == userdata["email"]:
                        flash_warning("Your email address will become public if you do not set your homepage in your user profile.")
                    else:
                        flash_warning(
                            "The email address %s of maintainer %s will be publicly visible.<br>%s",
                            userdata["email"],
                            userdata["name"],
                            "The homepage on the maintainer's user account should be set prevent this.",
                        )
        except Exception as err:  # should only be ValueError's but let's be cautious
            errmsgs.append(format_input_errmsg(err, val, col))
    if not data["name"]:
        errmsgs.append("Institution name cannot be blank.")
    if not errmsgs and not data["homepage"]:
        errmsgs.append("Institution homepage cannot be blank.")
    if new and db.institutions.count({'name':data["name"]}):
        errmsgs.append(format_errmsg("An institution named %s already exists.  Please add disambiguating information to the name.", data["name"]))
    if not new and data["name"] != institution.name and db.institutions.count({'name':data["name"]}):
        errmsgs.append(format_errmsg("Unable to change institution name to %s, there is another insituttion with the same name.", data["name"]))
    # Don't try to create new_version using invalid input
    if errmsgs:
        return show_input_errors(errmsgs)
    new_version = WebInstitution(shortname, data=data)
    if new_version == institution:
        flash("No changes made to institution.")
    else:
        new_version.save()
        edittype = "created" if new else "edited"
        flash("Institution %s successfully!" % edittype)
    return redirect(url_for(".edit_institution", shortname=shortname), 302)


@create.route("edit/talk/<seminar_id>/<seminar_ctr>/<token>")
def edit_talk_with_token(seminar_id, seminar_ctr, token):
    # For emailing, where encoding ampersands in a mailto link is difficult
    return redirect(url_for(".edit_talk", seminar_id=seminar_id, seminar_ctr=seminar_ctr, token=token), 302,)


@create.route("edit/talk/", methods=["GET", "POST"])
def edit_talk():
    if request.method == "POST":
        data = request.form
    else:
        data = request.args
    token = data.get("token", "")
    resp, talk = can_edit_talk(data.get("seminar_id", ""), data.get("seminar_ctr", ""), token)
    if resp is not None:
        return resp
    if token:
        # Also want to override top menu
        from seminars.utils import top_menu

        menu = top_menu()
        menu[2] = (url_for("create.index"), "", "Manage")
        extras = {"top_menu": menu}
    else:
        extras = {}
    # The seminar schedule page adds in a date and times
    if data.get("date", "").strip():
        tz = talk.seminar.tz
        date = process_user_input(data["date"], "date", "date", tz)
        try:
            # TODO: clean this up
            start_time = process_user_input(data.get("start_time"), "start_time", "time", tz)
            end_time = process_user_input(data.get("end_time"), "end_time", "time", tz)
            start_time = localize_time(datetime.combine(date, start_time), tz)
            end_time = localize_time(datetime.combine(date, end_time), tz)
        except ValueError:
            return redirect(url_for(".edit_seminar_schedule", shortname=talk.seminar_id), 302)
        talk.start_time = start_time
        talk.end_time = end_time
    # lock = get_lock(seminar_id, data.get("lock"))
    title = "Create talk" if talk.new else "Edit talk"
    return render_template(
        "edit_talk.html",
        talk=talk,
        seminar=talk.seminar,
        title=title,
        section="Manage",
        subsection="edittalk",
        institutions=institutions(),
        timezones=timezones,
        maxlength=maxlength,
        token=token,
        **extras
    )


@create.route("save/talk/", methods=["POST"])
def save_talk():
    raw_data = request.form
    token = raw_data.get("token", "")
    resp, talk = can_edit_talk(raw_data.get("seminar_id", ""), raw_data.get("seminar_ctr", ""), token)
    if resp is not None:
        return resp
    if raw_data.get("submit") == "cancel":
        flash("Changes discarded")
        return redirect(url_for(".edit_talk", seminar_id=talk.seminar_id, seminar_ctr=talk.seminar_ctr), 302)
    if raw_data.get("submit") == "delete":
        return redirect(url_for(".delete_talk", seminar_id=talk.seminar_id, seminar_ctr=talk.seminar_ctr), 302)

    errmsgs = []
    data = {
        "seminar_id": talk.seminar_id,
        "token": talk.token,
        "display": talk.display,  # could be being edited by anonymous user
    }
    if talk.new:
        curmax = talks_max("seminar_ctr", {"seminar_id": talk.seminar_id}, include_deleted=True)
        if curmax is None:
            curmax = 0
        data["seminar_ctr"] = curmax + 1
    else:
        data["seminar_ctr"] = talk.seminar_ctr
    default_tz = talk.seminar.timezone
    if not default_tz:
        default_tz = "UTC"
    data["timezone"] = tz = raw_data.get("timezone", default_tz)
    tz = pytz.timezone(tz)
    for col in db.talks.search_cols:
        if col in data:
            continue
        typ = db.talks.col_type[col]
        try:
            val = raw_data.get(col, "")
            data[col] = None  # make sure col is present even if process_user_input fails
            data[col] = process_user_input(val, col, typ, tz)
            if col == "access" and data[col] not in ["open", "users", "endorsed"]:
                errmsgs.append(format_errmsg("Access type %s invalid", data[col]))
        except Exception as err:  # should only be ValueError's but let's be cautious
            errmsgs.append(format_input_errmsg(err, val, col))
    if not data["speaker"]:
        errmsgs.append("Speaker name cannot be blank -- use TBA if speaker not chosen.")
    if data["start_time"] is None or data["end_time"] is None:
        errmsgs.append("Talks must have both a start and end time.")
    data["topics"] = clean_topics(data.get("topics"))
    data["language"] = clean_language(data.get("language"))
    data["subjects"] = clean_subjects(data.get("subjects"))
    if not data["subjects"]:
        errmsgs.append("Please select at least one subject")

    # Don't try to create new_version using invalid input
    if errmsgs:
        return show_input_errors(errmsgs)
    else:  # to make it obvious that these two statements should be together
        new_version = WebTalk(talk.seminar_id, data=data)

    # Warnings
    sanity_check_times(new_version.start_time, new_version.end_time)
    if "zoom" in data["video_link"] and not "rec" in data["video_link"]:
        flash_warning(
            "Recorded video link should not be used for Zoom meeting links; be sure to use Livestream link for meeting links."
        )
    if not data["topics"]:
        flash_warning(
            "This talk has no topics, and thus will only be visible to users when they disable their topics filter."
        )
    if new_version == talk:
        flash("No changes made to talk.")
    else:
        new_version.save()
        edittype = "created" if talk.new else "edited"
        flash("Talk successfully %s!" % edittype)
    edit_kwds = dict(seminar_id=new_version.seminar_id, seminar_ctr=new_version.seminar_ctr)
    if token:
        edit_kwds["token"] = token
    else:
        edit_kwds.pop("token", None)
    return redirect(url_for(".edit_talk", **edit_kwds), 302)


def layout_schedule(seminar, data):
    """ Returns a list of schedule slots in specified date range (date, daytime-interval, talk)
        where talk is a WebTalk or none.  Picks default dates if none specified
    """
    tz = seminar.tz

    def parse_date(key):
        date = data.get(key)
        if date:
            try:
                return process_user_input(date, "date", "date", tz)
            except ValueError:
                flash_warning ("Invalid date %s ignored, please use a format like mmm dd, yyyy or dd-mmm-yyyy or mm/dd/yyyy", date)

    def slot_start_time(s):
        # put slots with no time specified at the end of the day
        return date_and_daytimes_to_times(parse_time(s[0]), s[1] if s[1] else "23:59-23:59", tz)[0]

    begin = parse_date("begin")
    end = parse_date("end")
    shortname = seminar.shortname
    now = datetime.now(tz=tz)
    today = now.date()
    day = timedelta(days=1)
    if seminar.is_conference and (seminar.start_date is None or seminar.end_date is None):
        flash_warning ("You have not specified the start and end dates of your conference (we chose a date range to layout your schedule).")
    if seminar.is_conference and not seminar.per_day:
        seminar.per_day = 4
    begin = seminar.start_date if begin is None and seminar.is_conference else begin
    begin = today if begin is None else begin
    end = seminar.end_date if end is None and seminar.is_conference else end
    if end is None:
        if seminar.is_conference:
            end = begin + day * ceil(SCHEDULE_LEN / seminar.per_day)
        else:
            if seminar.frequency:
                end = begin + day * ceil(SCHEDULE_LEN * seminar.frequency / len(seminar.time_slots))
            else:
                end = begin + 14 * day
    if end < begin:
        end = begin
    data["begin"] = seminar.show_input_date(begin)
    data["end"] = seminar.show_input_date(end)
    midnight_begin = midnight(begin, tz)
    midnight_end = midnight(end, tz)
    query = {"$gte": midnight_begin, "$lt": midnight_end + day}
    talks = list(talks_search({"seminar_id": shortname, "start_time": query}, sort=["start_time"]))
    slots = [(t.show_date(tz), t.show_daytimes(tz), t) for t in talks]
    if seminar.is_conference:
        per_day = seminar.per_day if seminar.per_day else 4
        newslots = []
        d = midnight_begin
        while d < midnight_end + day:
            newslots += [(seminar.show_schedule_date(d), "", None) for i in range(per_day)]
            d += day
        for t in slots:
            if (t[0], "", None) in newslots:
                newslots.remove((t[0], "", None))
        slots = sorted(slots + newslots, key=lambda t: slot_start_time(t))
        return slots
    if not seminar.frequency:
        for i in range(max(SCHEDULE_LEN - len(slots), 3)):
            slots.append(("", "", None))
    else:
        # figure out week to start in.
        # use the week of the first seminar after begin if any, otherwise last seminar before begin, if any
        # otherwise just use the week containing begin
        t = talks_lucky({"seminar_id": shortname, "start_time": {"$gte": midnight_begin}}, sort=[("start_time", 1)])
        if not t:
            t = talks_lucky({"seminar_id": shortname, "start_time": {"$lt": midnight_begin}}, sort=[("start_time", -1)])
        if t:
            t = adapt_datetime(t.start_time, newtz=tz)
            w = t - t.weekday() * day
            while w > midnight_begin:
                w -= day * seminar.frequency
            while w + day * seminar.frequency < midnight_begin:
                w += day * seminar.frequency
        else:
            w = midnight_begin - midnight_begin.weekday() * day
        # make a list of all seminar time slots in [begin,end)
        newslots = []
        while w < midnight_end:
            for i in range(len(seminar.weekdays)):
                d = w + day * seminar.weekdays[i]
                if d >= midnight_begin and d < midnight_end + day:
                    newslots.append((seminar.show_schedule_date(d), seminar.time_slots[i], None))
            w = w + day * seminar.frequency
        # remove slots that for which there is an existing talk on the same day
        # remove one slot for each talk in order, rather than trying to match times
        # this works better in situations where the times vary
        for t in slots:
            sameday = [s for s in newslots if s[0] == t[0]]
            if sameday:
                newslots.remove(sameday[0])
        slots = sorted(slots + newslots, key=lambda t: slot_start_time(t))
    return slots


@create.route("edit/schedule/", methods=["GET", "POST"])
@email_confirmed_required
def edit_seminar_schedule():
    # It would be good to have a version of this that worked for a conference, but that's a project for later
    if request.method == "POST":
        data = dict(request.form)
    else:
        data = dict(request.args)
    shortname = data.get("shortname", "")
    resp, seminar = can_edit_seminar(shortname, new=False)
    if resp is not None:
        return resp
    if not seminar.topics:
        flash_warning(
            "This series has no topics selected; don't forget to set the topics for each new talk individually."
        )
    schedule = layout_schedule(seminar, data)
    return render_template(
        "edit_seminar_schedule.html",
        seminar=seminar,
        raw_data=data,
        title="Edit schedule",
        schedule=schedule,
        section="Manage",
        subsection="schedule",
        maxlength=maxlength,
    )


required_cols = ["date", "time", "speaker"]
optional_cols = ["speaker_affiliation", "speaker_email", "title", "hidden"]


@create.route("save/schedule/", methods=["POST"])
@email_confirmed_required
def save_seminar_schedule():
    raw_data = request.form
    shortname = raw_data["shortname"]
    resp, seminar = can_edit_seminar(shortname, new=False)
    if resp is not None:
        return resp
    if raw_data.get("submit") == "cancel":
        flash("Changes discarded")
        return redirect(url_for(".edit_seminar_schedule", shortname=shortname), 302)
    frequency = raw_data.get("frequency")
    try:
        frequency = int(frequency)
    except Exception:
        pass
    slots = int(raw_data["slots"])
    curmax = talks_max("seminar_ctr", {"seminar_id": shortname})
    if curmax is None:
        curmax = 0
    ctr = curmax + 1
    updated = 0
    warned = False
    errmsgs = []
    tz = seminar.tz
    to_save = []
    for i in list(range(slots)):
        seminar_ctr = raw_data.get("seminar_ctr%s" % i)
        speaker = process_user_input(raw_data.get("speaker%s" % i, ""), "speaker", "text", tz)
        if not speaker:
            if not warned and any(raw_data.get("%s%s" % (col, i), "").strip() for col in optional_cols):
                warned = True
                flash_warning("Talks are only saved if you specify a speaker")
            elif (
                not warned
                and seminar_ctr
                and not any(raw_data.get("%s%s" % (col, i), "").strip() for col in optional_cols)
            ):
                warned = True
                flash_warning("To delete an existing talk, click Details and then click delete on the Edit talk page")
            continue
        date = start_time = end_time = None
        dateval = raw_data.get("date%s" % i).strip()
        timeval = raw_data.get("time%s" % i).strip()
        if dateval and timeval:
            try:
                date = process_user_input(dateval, "date", "date", tz)
            except Exception as err:  # should only be ValueError's but let's be cautious
                errmsgs.append(format_input_errmsg(err, dateval, "date"))
            if date:
                try:
                    interval = process_user_input(timeval, "time", "daytimes", tz)
                    start_time, end_time = date_and_daytimes_to_times(date, interval, tz)
                except Exception as err:  # should only be ValueError's but let's be cautious
                    errmsgs.append(format_input_errmsg(err, timeval, "time"))
        if not date or not start_time or not end_time:
            errmsgs.append(format_errmsg("You must specify a date and time for the talk by %s", speaker))

        # we need to flag date and time errors before we go any further
        if errmsgs:
            return show_input_errors(errmsgs)

        if daytimes_early(interval):
            flash_warning(
                "Talk for speaker %s includes early AM hours, please correct if this is not intended (use 24-hour time format).",
                speaker,
            )
        elif daytimes_long(interval) > 8 * 60:
            flash_warning("Time s %s is longer than 8 hours, please correct if this is not intended.", speaker),

        if seminar_ctr:
            # existing talk
            seminar_ctr = int(seminar_ctr)
            talk = WebTalk(shortname, seminar_ctr, seminar=seminar)
        else:
            # new talk
            talk = WebTalk(shortname, seminar=seminar, editing=True)

        data = dict(talk.__dict__)
        data["speaker"] = speaker
        data["start_time"] = start_time
        data["end_time"] = end_time

        for col in optional_cols:
            typ = db.talks.col_type[col]
            try:
                val = raw_data.get("%s%s" % (col, i), "")
                data[col] = None  # make sure col is present even if process_user_input fails
                data[col] = process_user_input(val, col, typ, tz)
            except Exception as err:
                errmsgs.append(format_input_errmsg(err, val, col))

        # Don't try to create new_version using invalid input
        if errmsgs:
            return show_input_errors(errmsgs)

        if seminar_ctr:
            new_version = WebTalk(talk.seminar_id, data=data)
            if new_version != talk:
                updated += 1
                to_save.append(new_version) # defer save in case of errors on other talks
        else:
            data["seminar_ctr"] = ctr
            ctr += 1
            new_version = WebTalk(talk.seminar_id, data=data)
            to_save.append(new_version) # defer save in case of errors on other talks

    for newver in to_save:
        newver.save()

    if raw_data.get("detailctr"):
        return redirect(url_for(".edit_talk", seminar_id=shortname, seminar_ctr=int(raw_data.get("detailctr")),), 302,)
    else:
        flash("%s talks updated, %s talks created" % (updated, ctr - curmax - 1))
        if warned:
            return redirect(url_for(".edit_seminar_schedule", **raw_data), 302)
        else:
            return redirect(
                url_for(
                    ".edit_seminar_schedule",
                    shortname=shortname,
                    begin=raw_data.get("begin"),
                    end=raw_data.get("end"),
                    frequency=raw_data.get("frequency"),
                    weekday=raw_data.get("weekday"),
                ),
                302,
            )
