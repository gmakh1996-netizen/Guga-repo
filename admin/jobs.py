"""ფონური ამოცანები: სურათების ჩამოტანა, პროგრესი, გაჩერება."""
import json

from flask import current_app, flash, jsonify, redirect, render_template, request, url_for

from medialib import jobs as job_engine
from medialib import mirror
from models import Job, db

from . import admin_bp
from .auth import current_admin, log_action

KINDS = {
    "media_mirror": "სურათების ჩამოტანა",
}


@admin_bp.route("/jobs")
def jobs_list():
    recent = Job.query.order_by(Job.id.desc()).limit(20).all()
    live = job_engine.running_job()
    try:
        plan = mirror.plan()
    except Exception as exc:  # noqa: BLE001
        current_app.logger.warning("mirror.plan ჩავარდა: %s", exc)
        plan = None
    return render_template(
        "admin/jobs.html", jobs=recent, live=live, plan=plan, kinds=KINDS,
    )


@admin_bp.route("/jobs/mirror", methods=["POST"])
def jobs_mirror():
    if job_engine.running_job() is not None:
        flash("ერთი ამოცანა უკვე მიმდინარეობს. დაელოდეთ ან გააჩერეთ.", "error")
        return redirect(url_for("admin.jobs_list"))

    try:
        limit = max(0, min(int(request.form.get("limit") or 0), 20000))
    except ValueError:
        limit = 0

    subject_types = request.form.getlist("subject_types") or ["movie", "series"]
    admin = current_admin()
    job = job_engine.create_job(
        "media_mirror",
        {"limit": limit, "prefer_tmdb": True, "subject_types": subject_types},
        admin_id=admin.id if admin else None,
    )
    job_engine.start(current_app._get_current_object(), job.id, mirror.run)
    log_action("jobs.mirror", "job", job.id, detail="limit=%d" % limit)
    flash("ამოცანა გაეშვა. პროგრესი ქვემოთ ჩანს.", "ok")
    return redirect(url_for("admin.jobs_list"))


@admin_bp.route("/jobs/<int:job_id>/cancel", methods=["POST"])
def jobs_cancel(job_id):
    if job_engine.request_cancel(job_id):
        log_action("jobs.cancel", "job", job_id)
        flash("გაჩერების მოთხოვნა გაიგზავნა.", "ok")
    else:
        flash("ეს ამოცანა აღარ მუშაობს.", "error")
    return redirect(url_for("admin.jobs_list"))


@admin_bp.route("/jobs/<int:job_id>/status")
def jobs_status(job_id):
    job = db.session.get(Job, job_id)
    if job is None:
        return jsonify(error="ვერ მოიძებნა"), 404
    return jsonify(
        id=job.id, kind=job.kind, status=job.status, live=job.is_live,
        total=job.total or 0, done=job.done or 0, failed=job.failed or 0,
        skipped=job.skipped or 0, percent=job.percent,
        bytes_fetched=job.bytes_fetched or 0,
        log=(job.log_text or "")[-4000:],
        result=json.loads(job.result_json) if job.result_json else None,
    )
