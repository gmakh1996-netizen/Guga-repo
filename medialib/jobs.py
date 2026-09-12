"""ფონური ამოცანების მარტივი ძრავი.

მიზანი მინიმალურია და განზრახ: ცალკე worker-პროცესი და რიგის ბროკერი ამ
პროექტს ჯერ არ სჭირდება. ამოცანა ეშვება ცალკე thread-ში, პროგრესს წერს
`Job` ცხრილში, ბექოფისი კი კითხულობს და აჩვენებს.

შეზღუდვები, რომლებიც ცალსახად უნდა ვიცოდეთ:
  * ერთდროულად მხოლოდ ერთი მძიმე ამოცანა გადის (`_LOCK`);
  * gunicorn-ის თითო მუშას საკუთარი thread-ები აქვს, ამიტომ ჩაწერა
    „ერთი ამოცანა ერთდროულად" მკაცრად მხოლოდ ერთი მუშის ფარგლებშია.
    ამიტომვე ვამოწმებთ ბაზაშიც, ხომ არ გაშვებულია იმავე ტიპის ამოცანა;
  * გაჩერების მოთხოვნა ბაზაში იწერება, ამოცანა კი მას ციკლში ამოწმებს.
"""
import json
import threading
import traceback
from datetime import datetime, timezone

from models import Job, db

_LOCK = threading.Lock()
MAX_LOG_CHARS = 60000


class Cancelled(Exception):
    """ამოცანა მომხმარებელმა გააჩერა."""


class JobContext:
    """ამოცანის შიგნით გამოსაყენებელი დამხმარე: პროგრესი, ლოგი, გაჩერება."""

    def __init__(self, job_id, flush_every=25):
        self.job_id = job_id
        self.flush_every = flush_every
        self._lines = []
        self._since_flush = 0
        self.counters = {"done": 0, "failed": 0, "skipped": 0, "bytes_fetched": 0}

    # -- ლოგი ------------------------------------------------------------
    def log(self, message):
        stamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self._lines.append("[%s] %s" % (stamp, message))

    # -- პროგრესი --------------------------------------------------------
    def bump(self, key, amount=1):
        self.counters[key] = self.counters.get(key, 0) + amount
        self._since_flush += 1
        if self._since_flush >= self.flush_every:
            self.flush()

    def set_total(self, total):
        job = db.session.get(Job, self.job_id)
        job.total = total
        db.session.commit()

    def flush(self):
        """მრიცხველების და ლოგის ჩაწერა. აქვე მოწმდება გაჩერების მოთხოვნა."""
        job = db.session.get(Job, self.job_id)
        if job is None:
            raise Cancelled("ამოცანა წაშლილია")
        for key, value in self.counters.items():
            setattr(job, key, value)
        if self._lines:
            text = (job.log_text or "") + "\n".join(self._lines) + "\n"
            job.log_text = text[-MAX_LOG_CHARS:]
            self._lines = []
        db.session.commit()
        self._since_flush = 0
        db.session.refresh(job)
        if job.cancel_requested:
            raise Cancelled()

    def check_cancel(self):
        job = db.session.get(Job, self.job_id)
        db.session.refresh(job)
        if job.cancel_requested:
            raise Cancelled()


def running_job(kind=None):
    """მიმდინარე (ან რიგში მდგომი) ამოცანა."""
    query = Job.query.filter(Job.status.in_(("pending", "running")))
    if kind:
        query = query.filter_by(kind=kind)
    return query.order_by(Job.id.desc()).first()


def create_job(kind, params=None, admin_id=None):
    job = Job(
        kind=kind,
        params_json=json.dumps(params or {}, ensure_ascii=False),
        admin_id=admin_id,
        status="pending",
    )
    db.session.add(job)
    db.session.commit()
    return job


def start(app, job_id, fn):
    """ამოცანის გაშვება thread-ში. fn(ctx, params) -> dict | None."""
    def runner():
        with app.app_context():
            job = db.session.get(Job, job_id)
            if job is None:
                return
            if not _LOCK.acquire(blocking=False):
                job.status = "failed"
                job.log_text = "სხვა ამოცანა უკვე მიმდინარეობს. სცადეთ მოგვიანებით."
                job.finished_at = datetime.now(timezone.utc)
                db.session.commit()
                return
            ctx = JobContext(job_id)
            try:
                job.status = "running"
                job.started_at = datetime.now(timezone.utc)
                db.session.commit()

                params = json.loads(job.params_json or "{}")
                result = fn(ctx, params) or {}

                ctx.flush()
                job = db.session.get(Job, job_id)
                job.status = "done"
                job.result_json = json.dumps(result, ensure_ascii=False)
            except Cancelled:
                db.session.rollback()
                job = db.session.get(Job, job_id)
                job.status = "cancelled"
                job.log_text = (job.log_text or "") + "\nგაჩერებულია მომხმარებლის მოთხოვნით."
            except Exception as exc:  # noqa: BLE001
                db.session.rollback()
                job = db.session.get(Job, job_id)
                job.status = "failed"
                tail = traceback.format_exc()[-4000:]
                job.log_text = (job.log_text or "") + "\nშეცდომა: %s\n%s" % (exc, tail)
            finally:
                try:
                    job = db.session.get(Job, job_id)
                    if job is not None:
                        job.finished_at = datetime.now(timezone.utc)
                        db.session.commit()
                except Exception:  # noqa: BLE001
                    db.session.rollback()
                db.session.remove()
                _LOCK.release()

    thread = threading.Thread(target=runner, name="job-%d" % job_id, daemon=True)
    thread.start()
    return thread


def request_cancel(job_id):
    job = db.session.get(Job, job_id)
    if job is None or not job.is_live:
        return False
    job.cancel_requested = True
    db.session.commit()
    return True
