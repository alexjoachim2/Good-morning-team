#!/usr/bin/env python3
"""Build a weekly reading issue from public RSS and Atom feeds."""
import datetime as dt
import email.utils
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

SOURCES = [
 ("ArchDaily","https://www.archdaily.com/feed/rss/","Architecture"),
 ("designboom","https://www.designboom.com/feed/","Design"),
 ("Dezeen","https://www.dezeen.com/architecture/feed/","Architecture"),
 ("Colossal","https://www.thisiscolossal.com/feed/","Art & ideas"),
 ("The Architect's Newspaper","https://archpaper.com/feed","Cities"),
 ("Design Milk","https://design-milk.com/category/architecture/feed/","Design"),
]
INTERESTS = {"hotel":12,"hospitality":12,"adaptive reuse":14,"heritage":9,"interior":8,"cafe":8,"café":8,"architecture":6,"architect":5,"city":6,"urban":7,"neighborhood":8,"historic":8,"museum":7,"library":7,"branding":8,"identity":6,"graphic":6,"design":3,"material":5,"renovation":8,"new york":9,"restoration":8}
BASE=Path(__file__).resolve().parents[1]
OUT=BASE/"data"/"weekly.json"
def local(tag): return tag.split("}")[-1].lower()
def plain(s):
    s=html.unescape(re.sub(r"<[^>]+>"," ",s or ""))
    return " ".join(s.split())[:280]
def field(node,names):
    for c in node:
        if local(c.tag) in names:
            if local(c.tag)=="link" and c.attrib.get("href"): return c.attrib["href"]
            return "".join(c.itertext()).strip()
    return ""
def dateparse(raw):
    if not raw:return None
    try: value=email.utils.parsedate_to_datetime(raw)
    except Exception:
        try:value=dt.datetime.fromisoformat(raw.replace("Z","+00:00"))
        except Exception:return None
    if value.tzinfo is None:value=value.replace(tzinfo=dt.timezone.utc)
    return value.astimezone(dt.timezone.utc)
def main():
    now=dt.datetime.now(dt.timezone.utc)
    collected=[]; working=0
    for name,url,category in SOURCES:
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; CreativeLibraryRSS/1.0)","Accept":"application/rss+xml,application/atom+xml,application/xml,text/xml,*/*"})
            with urllib.request.urlopen(req,timeout=17) as resp: root=ET.fromstring(resp.read(4000000))
            entries=[e for e in root.iter() if local(e.tag) in ("item","entry")]
            if entries:working+=1
            for e in entries[:40]:
                title=plain(field(e,{"title"}))
                snippet=plain(field(e,{"description","summary","content","encoded"}))
                link=field(e,{"link"})
                published=dateparse(field(e,{"pubdate","published","updated","date"}))
                if not link or not link.startswith(("https://","http://")) or not published or len(title)<12:continue
                age=(now-published).total_seconds()/86400
                if age < -1 or age>21:continue
                match=(title+" "+snippet).lower()
                score=sum(v for k,v in INTERESTS.items() if k in match) + max(0,12-int(age))
                collected.append({"title":title,"summary":snippet,"url":link,"source":name,"category":category,"published":published.isoformat(),"score":score})
        except Exception as exc:print(f"Skipping {name}: {exc}")
    collected.sort(key=lambda x:x["score"],reverse=True)
    seen=set();counts={};picked=[]
    for x in collected:
        k=x["url"].split("?")[0].lower()
        if k in seen or counts.get(x["source"],0)>=3:continue
        seen.add(k);counts[x["source"]]=counts.get(x["source"],0)+1
        x.pop("score",None);picked.append(x)
        if len(picked)==9:break
    OUT.parent.mkdir(parents=True,exist_ok=True)
    if not picked and OUT.exists():
        try:
            old=json.loads(OUT.read_text())
            if old.get("articles"):
                print("No eligible feeds; retaining previous weekly issue.")
                return
        except Exception:pass
    OUT.write_text(json.dumps({"updated_at":now.isoformat() if picked else None,"source_count":working,"source_status":"ok" if working==len(SOURCES) else "partial","articles":picked},ensure_ascii=False,indent=2))
    print(f"Published {len(picked)} stories from {working} feeds.")
if __name__=="__main__":main()
