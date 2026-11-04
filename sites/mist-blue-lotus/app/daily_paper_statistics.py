"""Daily reading starts remain separate from completed reading."""
import datetime
import study_service as study
import reading_journal

def snapshot(date):
    date=study.valid_date(date or study.today())
    monday=(datetime.date.fromisoformat(date)-datetime.timedelta(days=datetime.date.fromisoformat(date).weekday())).isoformat()
    with study.connection() as c:
        rows=study.records(c,'paper-knowledge')
        manual={r['id']:r for r in study.records(c,'paper-reading-status')}
    started={r['id']:r.get('startedDate') for r in rows if r.get('tasks',{}).get('methodology',{}).get('done') is True}
    completed={r['id']:r.get('readDate') for r in rows if reading_journal.complete(r)}
    for ident,r in manual.items():
        completed.pop(ident,None)
        if r.get('read'):completed[ident]=r.get('readDate')
    return dict(date=date,started=sum(d==date for d in started.values()),inProgress=len(set(started)-set(completed)),today=sum(d==date for d in completed.values()),week=sum(bool(d and monday<=d<=date) for d in completed.values()),month=sum(bool(d and d[:7]==date[:7] and d<=date) for d in completed.values()),total=len(completed))
