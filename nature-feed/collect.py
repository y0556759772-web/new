import urllib.request, pathlib, json, re, time, datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
root=pathlib.Path("nature-feed")
images=root/"images"; images.mkdir(exist_ok=True)
def fetch(url, maximum=12000000):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0"}),timeout=30) as r:
                b=r.read(maximum+1)
                if len(b)>maximum: raise ValueError("File too large")
                return b
        except Exception:
            if attempt==2: raise
            time.sleep(2)
soup=BeautifulSoup(fetch("https://t.me/s/matmon2020"),"html.parser")
messages=sorted(soup.select(".tgme_widget_message[data-post]"),key=lambda m:int(m["data-post"].split("/")[-1]))[-8:]
posts=[]
for m in reversed(messages):
    post_id=m["data-post"].split("/")[-1]
    stamp=m.select_one("time[datetime]")
    t=m.select_one(".tgme_widget_message_text")
    links=[{"text":a.get_text(),"url":a["href"]} for a in t.select("a[href]")] if t else []
    if t:
        for br in t.find_all("br"): br.replace_with("\n")
    post={"id":post_id,"date":stamp["datetime"] if stamp else None,"source":"https://t.me/"+m["data-post"],"text":t.get_text() if t else "","links":links,"images":[],"notes":[]}
    seen=set()
    for e in m.select("a.tgme_widget_message_photo_wrap"):
        match=re.search(r"background-image:\s*url\(['\"]?([^'\"\)]+)",e.get("style",""))
        if not match: continue
        url=match.group(1)
        if url in seen: continue
        seen.add(url)
        host=urlparse(url).hostname or ""
        if not host.endswith((".telesco.pe",".telegram-cdn.org")): continue
        try:
            data=fetch(url)
            ext=".jpg" if data.startswith(bytes.fromhex("ffd8ff")) else ".png" if data.startswith(bytes.fromhex("89504e470d0a1a0a")) else None
            if not ext: raise ValueError("Invalid image")
            name=post_id+"_"+str(len(post["images"])+1)+ext
            (images/name).write_bytes(data);post["images"].append("images/"+name)
        except Exception:
            post["notes"].append("תמונה אחת לא הייתה זמינה בזמן האיסוף")
    if m.select("video,.tgme_widget_message_video_player,.tgme_widget_message_video"):
        post["notes"].append("הפרסום המקורי כולל גם סרטון")
    posts.append(post)
if not posts or not any(p["images"] for p in posts): raise RuntimeError("No photo posts collected")
data={"channel":"matmon2020","collected_at":datetime.datetime.now(datetime.timezone.utc).isoformat(),"posts":posts}
(root/"feed.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"posts":len(posts),"photos":sum(len(p["images"]) for p in posts),"notes":[p["notes"] for p in posts if p["notes"]],"ids":[p["id"] for p in posts]}))
