"""Official conference metadata importer. No PDFs are bulk-downloaded.

Run: python conference_sources.py [--refresh] [--only ICML CVPR ...]
HTML/JSON responses are cached for 24 hours. Failed sources preserve prior rows.
Requires only Python standard library and Windows curl.exe (curl elsewhere).
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import re
import subprocess
import time
from pathlib import Path
from urllib.parse import urljoin, urlencode

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "local-data" / "conference-cache"
OUT = ROOT / "local-data" / "conferences.json"
REFRESH = False


def clean(s):
    return " ".join(html.unescape(html.unescape(re.sub("<[^>]+>", " ", s))).split())


def fetch(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".txt")
    if not REFRESH and path.exists() and time.time() - path.stat().st_mtime < 86400:
        cached = path.read_text(encoding="utf-8")
        if not cached.startswith("\x1f"):
            return cached
    time.sleep(.7)
    result = subprocess.run(
        ["curl.exe" if __import__("os").name == "nt" else "curl",
         "-f", "-sS", "-L", "--compressed", "--retry", "2", "--retry-all-errors", "--connect-timeout", "20",
         "--max-time", "100", url], capture_output=True)
    if result.returncode:
        raise RuntimeError(url + ": " + result.stderr.decode("utf-8", "replace")[:350])
    raw = result.stdout
    if raw.startswith(b"\x1f\x8b"):
        import gzip
        raw = gzip.decompress(raw)
    text = raw.decode("utf-8", "replace")
    if len(text) < 20:
        raise RuntimeError("Empty response")
    path.write_text(text, encoding="utf-8")
    return text


def classify(title, abstract=""):
    text = (title + " " + abstract).lower()
    topics = []
    if re.search(r"\bagent(s|ic)?\b", text):
        topics.append("Agent")
    if re.search(r"object detect|open.vocabulary detect|small.object|3d detect|detr\b", text):
        topics.append("Object Detection")
    if re.search(r"agent.?os|agent operating|agent runtime|agent infrastructure", text):
        topics.append("Agent OS")
    if re.search(r"prompt injection|agent.*secur|secur.*agent|tool.poison|agent.*attack|agent.*safety", text):
        topics.append("Agent Security")
    if re.search(r"harness|agent.*orchestrat|agent.*scaffold|agent.*evaluat|agent.*benchmark", text):
        topics.append("Agent Harness")
    return topics or ["其他"]


def paper(title, authors, source, pdf, venue, year, summary="", published=""):
    return dict(id=f"{venue.lower()}-{year}-"+hashlib.sha256(source.encode()).hexdigest()[:20],
                title=clean(title), authors=clean(authors), source=source, pdf=pdf,
                venue=venue, year=year, summary=clean(summary), topics=classify(clean(title), clean(summary)),
                published=published, updated=published, classification="关键词自动分类，待复核")


def pmlr(year):
    url = f"https://proceedings.mlr.press/v{267 if year == 2025 else 306}/"
    text = fetch(url)
    if not re.search(r"International Conference on Machine Learning", text, re.I):
        raise RuntimeError("Volume does not identify ICML; not imported")
    rows = []
    for block in re.split(r'<div class="paper">', text)[1:]:
        title = re.search(r'<p class="title">(.*?)</p>', block, re.S)
        authors = re.search(r'<span class="authors">(.*?)</span>', block, re.S)
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        src = next((u for u, label in links if clean(label) == "abs"), "")
        pdf = next((u for u, label in links if clean(label) == "Download PDF"), "")
        if title and src:
            rows.append(paper(title[1], authors[1] if authors else "", src, pdf, "ICML", year))
    return rows, url, "官方PMLR该卷全部目录条目；摘要未逐篇抓取。"


def cvf(venue, year):
    url = f"https://openaccess.thecvf.com/{venue}{year}?day=all"
    text = fetch(url)
    rows = []
    for block in re.split(r'<dt class="ptitle">', text)[1:]:
        link = re.search(r'<a href="([^"]+)">(.*?)</a>', block, re.S)
        authors = re.findall(r'name="query_author" value="([^"]+)"', block)
        pdf = re.search(r'href="([^"]+\.pdf)"', block)
        if link:
            rows.append(paper(link[2], ", ".join(authors), urljoin(url, link[1]),
                              urljoin(url, pdf[1]) if pdf else "", venue, year))
    return rows, url, "CVF主会 day=all 官方目录全部条目；不含独立workshop论文集。"


def neurips(year):
    if year == 2026:
        return virtual_conference("NeurIPS", year, "neurips.cc")
    url = f"https://papers.nips.cc/paper_files/paper/{year}/vol{year-1987}-main-conference"
    text = fetch(url)
    rows = []
    for block in re.split(r'<li[^>]*>', text):
        link = re.search(r'<a[^>]*title="paper title"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', block, re.S)
        if not link:
            continue
        author = re.search(r'<span class="paper-authors">(.*?)</span>', block, re.S)
        src = urljoin(url, link[1])
        pdf = src.replace("/hash/", "/file/").replace("-Abstract", "-Paper").replace(".html", ".pdf")
        rows.append(paper(link[2], author[1] if author else "", src, pdf, "NeurIPS", year))
    # Legacy official pages use simpler li/a/i markup.
    if not rows:
        for block in re.findall(r"<li\b.*?</li>", text, re.S):
            link = re.search(r'<a[^>]*href="([^"]+Abstract[^"]+)"[^>]*>(.*?)</a>', block, re.S)
            if link:
                author = re.search(r"<i>(.*?)</i>", block, re.S)
                src = urljoin(url, link[1])
                rows.append(paper(link[2], author[1] if author else "", src,
                                  src.replace("/hash/", "/file/").replace("-Abstract", "-Paper").replace(".html", ".pdf"),
                                  "NeurIPS", year))
    return rows, url, "官方主会论文集全部条目；不含Creative AI和workshop独立论文集。"


def iclr_openreview(year):
    url = "https://api2.openreview.net/notes?"
    rows, offset, expected = [], 0, None
    while expected is None or offset < expected:
        data = json.loads(fetch(url + urlencode({"content.venueid": f"ICLR.cc/{year}/Conference",
                                                  "limit": 1000, "offset": offset})))
        expected = data.get("count")
        notes = data.get("notes", [])
        if expected is None:
            raise RuntimeError("OpenReview total count missing")
        for note in notes:
            c = note["content"]
            def val(key, default=""):
                value = c.get(key, default)
                return value.get("value", default) if isinstance(value, dict) else value
            ident = note["id"]
            authors = val("authors", [])
            date = dt.datetime.fromtimestamp(note.get("pdate", note.get("cdate", 0))/1000, dt.timezone.utc).date().isoformat()
            rows.append(paper(val("title"), ", ".join(authors), "https://openreview.net/forum?id="+ident,
                              "https://openreview.net/pdf?id="+ident, "ICLR", year, val("abstract"), date))
        offset += len(notes)
        if not notes and offset < expected:
            raise RuntimeError(f"Incomplete pagination {offset}/{expected}")
    return rows, f"https://openreview.net/group?id=ICLR.cc/{year}/Conference", f"OpenReview venueid已录用集合；API总数{expected}。"


def iclr(year):
    return virtual_conference("ICLR", year, "iclr.cc")


def virtual_conference(venue, year, host):
    page = f"https://{host}/virtual/{year}/papers.html"
    text = fetch(page)
    found = re.search(r'start\("([^"]+orals-posters\.json)"', text)
    if not found:
        raise RuntimeError(f"Official {venue} page has no expected metadata link")
    data = json.loads(fetch(urljoin(page, found[1])))
    events = data.get("results", [])
    if data.get("next") or len(events) != data.get("count"):
        raise RuntimeError(f"Official {venue} event JSON pagination incomplete")
    rows = {}
    missing_pdf = 0
    for event in events:
        source = event.get("paper_url") or ""
        # Conference event exports sometimes fabricate oral-event OpenReview IDs.
        # These are event placeholders, not actual paper identifiers.
        if re.search(r"[?&]id=20\d\d-(?:Oral|Poster|Spotlight)", source, re.I):
            source = ""
        alternate = event.get("url") or ""
        if not source:
            source = alternate if alternate.startswith("https://openreview.net/forum?id=") else urljoin(page, event.get("virtualsite_url") or page)
        authors = ", ".join(a["fullname"] for a in event.get("authors", []))
        pdf = event.get("paper_pdf_url") or ""
        if not pdf and source.startswith("https://openreview.net/forum?id="):
            pdf = source.replace("/forum?", "/pdf?")
        if not pdf:
            missing_pdf += 1
        p = paper(event["name"], authors, source,
                  pdf,
                  venue, year, event.get("abstract") or "")
        p["officialTopic"] = event.get("topic") or ""
        p["decision"] = event.get("decision") or ""
        key = clean(event["name"]).casefold()
        if key not in rows or (not rows[key]["pdf"] and p["pdf"]):
            rows[key] = p
    return list(rows.values()), page, (f"{venue}官网已公布报告目录的去重清单，非最终正式论文集。公开JSON共{len(events)}个报告事件，"
                                      f"按同标题合并重复报告；{missing_pdf}个事件未提供直接PDF链接，保留官方会议页；含官网列出的journal等track，不含独立workshop。")


def aaai(year):
    archive = "https://ojs.aaai.org/index.php/AAAI/issue/archive"
    issues = {}
    # OJS archive pages contain both 2025 and 2026 volumes, possibly paginated.
    for page in range(1, 8):
        text = fetch(archive + (f"/{page}" if page > 1 else ""))
        found_older = False
        for block in re.split(r'<div[^>]*class="[^"]*obj_issue_summary[^"]*"[^>]*>', text)[1:]:
            link = re.search(r'href="([^"]*/issue/view/\d+)"', block)
            volume = re.search(r"Vol\.\s*(\d+)", clean(block))
            issue_year = int(volume[1]) + 1986 if volume else 0
            if link and year == issue_year:
                issues[link[1]] = clean(block)[:250]
            if issue_year and issue_year < year:
                found_older = True
        if found_older:
            break
    if not issues:
        raise RuntimeError("No matching official AAAI issue links found")
    rows = []
    for url in issues:
        text = fetch(url)
        for block in re.split(r'<div[^>]*class="[^"]*obj_article_summary[^"]*"[^>]*>', text)[1:]:
            link = re.search(r'<a[^>]*href="([^"]*/article/view/\d+)"[^>]*>(.*?)</a>', block, re.S)
            author = re.search(r'<div[^>]*class="authors"[^>]*>(.*?)</div>', block, re.S)
            pdf = re.search(r'href="([^"]*/article/view/\d+/\d+)"', block)
            if link:
                rows.append(paper(link[2], author[1] if author else "", link[1],
                                  pdf[1].replace("/article/view/", "/article/download/") if pdf else "", "AAAI", year))
    return rows, archive, f"官方AAAI年度卷{len(issues)}个分册全部目录条目，含该卷附属track；PDF为官方直接下载地址。"



def parse_acl_bib(text, year, track):
    rows=[]
    for entry in re.split(r'(?m)^@', text):
        if not entry.lower().startswith('inproceedings{'):continue
        fields={}
        for key,value in re.findall(r'(?m)^\s*(\w+)\s*=\s*(.*?)(?=,\s*\n\s*\w+\s*=|\n\})',entry,re.S):
            value=value.strip().rstrip(',').strip()
            if value[:1] in ('"','{'):value=value[1:-1]
            fields[key.lower()]=re.sub(r'\s+', ' ', value).strip()
        source=fields.get('url','')
        if not re.fullmatch(rf'https://aclanthology\.org/{year}\.acl-{track}\.\d+/',source):
            raise ValueError('ACL bibliography has an unexpected paper URL')
        if fields.get('year')!=str(year) or not fields.get('title'):
            raise ValueError('ACL bibliography has a missing title or mismatched year')
        title=fields['title'].replace('{','').replace('}','')
        authors=[]
        for name in re.split(r'\s+and\s+',fields.get('author','')):
            parts=name.split(',',1)
            authors.append((parts[1].strip()+' '+parts[0].strip()) if len(parts)==2 else name)
        row=paper(title,'; '.join(authors),source,source.rstrip('/')+'.pdf','ACL',year)
        row['track']='Long Papers' if track=='long' else 'Short Papers'
        row['doi']=fields.get('doi','')
        rows.append(row)
    if not rows:raise ValueError('No ACL main-conference papers parsed')
    return rows


def acl(year):
    rows=[]
    for track in ('long','short'):
        url=f'https://aclanthology.org/volumes/{year}.acl-{track}.bib'
        rows.extend(parse_acl_bib(fetch(url),year,track))
    return rows,f'https://aclanthology.org/events/acl-{year}/','ACL Anthology 主会长论文与短论文官方书目；不含 Findings、workshop、demo 或 industry；未逐篇采集摘要。'

def main():
    global REFRESH
    args = argparse.ArgumentParser()
    args.add_argument("--refresh", action="store_true")
    args.add_argument("--only", nargs="*", choices=["AAAI", "NeurIPS", "ICML", "ICCV", "CVPR", "ICLR", "ACL"])
    opt = args.parse_args()
    REFRESH = opt.refresh
    prior = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {"papers": [], "sources": []}
    data = {"generatedAt": dt.datetime.now(dt.timezone.utc).isoformat(),
            "classificationMethod": "标题/可用摘要关键词自动分类，非官方track，待人工复核；其他包含所有不匹配五方向的论文。",
            "sources": list(prior["sources"]), "papers": list(prior["papers"])}
    for venue in ["AAAI", "NeurIPS", "ICML", "ICCV", "CVPR", "ICLR", "ACL"]:
        for year in [2025, 2026]:
            old = [p for p in prior["papers"] if p["venue"] == venue and p["year"] == year]
            if opt.only and venue not in opt.only:
                continue
            status = dict(venue=venue, year=year, status="failed", count=0, url="", note="")
            print(f"{venue} {year} fetching", flush=True)
            try:
                if venue == "ICCV" and year == 2026:
                    status.update(status="no_conference", note="ICCV为奇数年会议，2026无主会。", url="https://www.thecvf.com/")
                    rows = []
                else:
                    fn = {"AAAI": aaai, "NeurIPS": neurips, "ICML": pmlr, "ICLR": iclr, "ACL": acl}.get(venue)
                    rows, url, note = fn(year) if fn else cvf(venue, year)
                    if not rows:
                        raise RuntimeError("Official index returned zero parsed papers; completeness unverified")
                    rows = list({p["id"]: p for p in rows}.values())
                    status.update(status="complete_index", count=len(rows), url=url, note=note)
                data["papers"] = [p for p in data["papers"] if not (p["venue"] == venue and p["year"] == year)]
                data["papers"].extend(rows)
            except Exception as exc:
                status.update(note=str(exc), count=len(old))
            data["sources"] = [s for s in data["sources"] if not (s["venue"] == venue and s["year"] == year)]
            data["sources"].append(status)
            OUT.parent.mkdir(parents=True, exist_ok=True)
            temp = OUT.with_suffix(".tmp")
            temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            for attempt in range(20):
                try:
                    temp.replace(OUT)
                    break
                except PermissionError:
                    if attempt == 19:
                        raise
                    time.sleep(.25)
            print(json.dumps(status, ensure_ascii=False), flush=True)
    print(f"Total: {len(data['papers'])}", flush=True)


if __name__ == "__main__":
    main()
