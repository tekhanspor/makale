#!/usr/bin/env python3
"""
Taekwondo & Spor Bilimleri Makale Takip Agent
Her gün GitHub Actions tarafından otomatik çalıştırılır.
Kaynaklar: PubMed, arXiv, Semantic Scholar, DOAJ, OpenAlex, Europe PMC, Dergipark, CORE, CrossRef, KCI
"""

import json
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

DAYS_BACK = 3

DEFAULT_KEYWORDS = [
    "taekwondo", "tae kwon do", "poomsae", "kyorugi",
    "태권도", "품새", "겨루기",
    "taekwondo biomechanics", "taekwondo physiology", "taekwondo psychology",
    "taekwondo training", "taekwondo coaching", "taekwondo performance",
    "taekwondo competition", "taekwondo sparring", "taekwondo kicking technique",
    "taekwondo injury", "taekwondo Olympic", "taekwondo education",
    "taekwondo history", "para taekwondo",
    "tekvando", "spor psikolojisi", "spor biyomekaniği",
    "sport performance analysis", "sports biomechanics", "exercise physiology",
    "sport psychology", "athletic training", "combat sport", "martial arts science",
]

DATA_FILE = Path("data/papers.json")
KEYWORDS_FILE = Path("data/keywords.json")
DATA_FILE.parent.mkdir(exist_ok=True)

def load_keywords():
    if KEYWORDS_FILE.exists():
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            kws = data.get("keywords", [])
            if kws:
                print(f"📋 keywords.json'dan {len(kws)} anahtar kelime yüklendi")
                return kws
    print(f"📋 Varsayılan {len(DEFAULT_KEYWORDS)} anahtar kelime")
    return DEFAULT_KEYWORDS

def load_existing():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"papers": [], "seen_urls": [], "last_updated": None}

def save_data(data):
    data["last_updated"] = datetime.utcnow().isoformat()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✓ Kaydedildi: {len(data['papers'])} makale")

def fetch_url(url, timeout=15, headers=None):
    try:
        h = {"User-Agent": "TaekwondoResearchTracker/1.0 (academic bot; contact: research@tracker.com)"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ✗ {url[:70]}... → {e}")
        return None

def date_from_days_back(days):
    return (datetime.utcnow() - timedelta(days=days)).strftime("%Y/%m/%d")

def iso_date_from_days_back(days):
    return (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

# ─── 1. PubMed ────────────────────────────────────────────────────────────────
def fetch_pubmed(keywords, days_back, seen_urls):
    print("\n📗 PubMed taranıyor...")
    papers = []
    query = " OR ".join(f'"{k}"' for k in keywords[:6])
    raw = fetch_url(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={urllib.parse.quote(query)}"
        f"&mindate={date_from_days_back(days_back)}&maxdate={date_from_days_back(0)}"
        "&datetype=pdat&retmax=30&retmode=json&sort=date"
    )
    if not raw: return papers
    try:
        ids = json.loads(raw).get("esearchresult", {}).get("idlist", [])
        print(f"  → {len(ids)} sonuç")
        if not ids: return papers
    except: return papers
    time.sleep(0.4)
    raw2 = fetch_url(f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json")
    if not raw2: return papers
    try:
        result = json.loads(raw2).get("result", {})
        for pmid in ids:
            item = result.get(pmid, {})
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if not item or url in seen_urls: continue
            papers.append({
                "id": f"pubmed_{pmid}", "title": item.get("title","").rstrip("."),
                "authors": ", ".join(a.get("name","") for a in item.get("authors",[])[:3]),
                "date": item.get("pubdate",""), "url": url, "source": "PubMed",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e: print(f"  ✗ {e}")
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 2. arXiv ────────────────────────────────────────────────────────────────
def fetch_arxiv(keywords, days_back, seen_urls):
    print("\n📘 arXiv taranıyor...")
    papers = []
    query = "+OR+".join(urllib.parse.quote(k) for k in keywords[:4])
    raw = fetch_url(f"https://export.arxiv.org/api/query?search_query=all:{query}&sortBy=submittedDate&sortOrder=descending&max_results=20")
    if not raw: return papers
    try:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        for entry in ET.fromstring(raw).findall("atom:entry", ns):
            pub = entry.findtext("atom:published","",ns)
            try:
                if datetime.strptime(pub[:10],"%Y-%m-%d") < cutoff: continue
            except: continue
            pid = entry.findtext("atom:id","",ns).replace("http://","https://")
            if pid in seen_urls: continue
            authors = [a.findtext("atom:name","",ns) for a in entry.findall("atom:author",ns)]
            papers.append({
                "id": f"arxiv_{pid.split('/')[-1]}",
                "title": entry.findtext("atom:title","",ns).strip().replace("\n"," "),
                "authors": ", ".join(authors[:3]), "date": pub[:10],
                "url": pid, "source": "arXiv", "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e: print(f"  ✗ {e}")
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 3. Semantic Scholar ──────────────────────────────────────────────────────
def fetch_semantic_scholar(keywords, days_back, seen_urls):
    print("\n📙 Semantic Scholar taranıyor...")
    papers = []
    cutoff = datetime.utcnow() - timedelta(days=days_back)
    seen = set()
    for kw in keywords[:5]:
        raw = fetch_url(f"https://api.semanticscholar.org/graph/v1/paper/search?query={urllib.parse.quote(kw)}&fields=title,authors,year,publicationDate,externalIds&limit=10&sort=publicationDate:desc")
        if not raw: time.sleep(1); continue
        try:
            for item in json.loads(raw).get("data",[]):
                pub_date = item.get("publicationDate","")
                if pub_date:
                    try:
                        if datetime.strptime(pub_date,"%Y-%m-%d") < cutoff: continue
                    except: pass
                pid = item.get("paperId","")
                doi = item.get("externalIds",{}).get("DOI","")
                url = f"https://doi.org/{doi}" if doi else f"https://www.semanticscholar.org/paper/{pid}"
                if url in seen_urls or url in seen: continue
                seen.add(url)
                papers.append({
                    "id": f"ss_{pid}", "title": item.get("title",""),
                    "authors": ", ".join(a.get("name","") for a in item.get("authors",[])[:3]),
                    "date": pub_date or str(item.get("year","")),
                    "url": url, "source": "Semantic Scholar", "added_at": datetime.utcnow().isoformat()
                })
        except Exception as e: print(f"  ✗ {e}")
        time.sleep(1.2)
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 4. DOAJ ─────────────────────────────────────────────────────────────────
def fetch_doaj(keywords, days_back, seen_urls):
    print("\n📕 DOAJ taranıyor...")
    papers = []
    query = urllib.parse.quote(" OR ".join(keywords[:3]))
    raw = fetch_url(f"https://doaj.org/api/search/articles/{query}?sort=created_date:desc&pageSize=20")
    if not raw: return papers
    try:
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        for item in json.loads(raw).get("results",[]):
            bib = item.get("bibjson",{})
            created = item.get("created_date","")[:10]
            try:
                if created and datetime.strptime(created,"%Y-%m-%d") < cutoff: continue
            except: pass
            links = bib.get("link",[])
            url = next((l.get("url","") for l in links if l.get("type")=="fulltext"),"")
            if not url or url in seen_urls: continue
            papers.append({
                "id": f"doaj_{item.get('id','')}",
                "title": bib.get("title",""),
                "authors": ", ".join(a.get("name","") for a in bib.get("author",[])[:3]),
                "date": bib.get("year",""), "url": url, "source": "DOAJ",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e: print(f"  ✗ {e}")
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 5. OpenAlex ─────────────────────────────────────────────────────────────
def fetch_openalex(keywords, days_back, seen_urls):
    print("\n🌐 OpenAlex taranıyor...")
    papers = []
    cutoff = iso_date_from_days_back(days_back)
    seen = set()
    for kw in keywords[:6]:
        url = (
            "https://api.openalex.org/works"
            f"?search={urllib.parse.quote(kw)}"
            f"&filter=from_publication_date:{cutoff}"
            "&sort=publication_date:desc&per-page=15"
            "&mailto=research@tracker.com"
        )
        raw = fetch_url(url)
        if not raw: time.sleep(1); continue
        try:
            for item in json.loads(raw).get("results",[]):
                doi = item.get("doi","")
                paper_url = doi if doi else item.get("id","")
                if not paper_url or paper_url in seen_urls or paper_url in seen: continue
                seen.add(paper_url)
                authors = [
                    a.get("author",{}).get("display_name","")
                    for a in item.get("authorships",[])[:3]
                ]
                papers.append({
                    "id": f"oa_{item.get('id','').split('/')[-1]}",
                    "title": item.get("title","") or "",
                    "authors": ", ".join(authors),
                    "date": item.get("publication_date",""),
                    "url": paper_url, "source": "OpenAlex",
                    "added_at": datetime.utcnow().isoformat()
                })
        except Exception as e: print(f"  ✗ {e}")
        time.sleep(0.5)
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 6. Europe PMC ───────────────────────────────────────────────────────────
def fetch_europe_pmc(keywords, days_back, seen_urls):
    print("\n🇪🇺 Europe PMC taranıyor...")
    papers = []
    cutoff_year = (datetime.utcnow() - timedelta(days=days_back)).year
    query = " OR ".join(f'"{k}"' for k in keywords[:5])
    url = (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
        f"?query={urllib.parse.quote(query)}&resultType=core&pageSize=20"
        "&sort=P_PDATE_D desc&format=json"
    )
    raw = fetch_url(url)
    if not raw: return papers
    try:
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        for item in json.loads(raw).get("resultList",{}).get("result",[]):
            pub_date = item.get("firstPublicationDate","")
            try:
                if pub_date and datetime.strptime(pub_date,"%Y-%m-%d") < cutoff: continue
            except: pass
            pmid = item.get("pmid","")
            doi = item.get("doi","")
            paper_url = f"https://doi.org/{doi}" if doi else (f"https://europepmc.org/article/MED/{pmid}" if pmid else "")
            if not paper_url or paper_url in seen_urls: continue
            authors_list = item.get("authorList",{}).get("author",[])
            authors = ", ".join(f"{a.get('lastName','')} {a.get('initials','')}".strip() for a in authors_list[:3])
            papers.append({
                "id": f"epmc_{item.get('id','')}",
                "title": item.get("title","").rstrip("."),
                "authors": authors, "date": pub_date,
                "url": paper_url, "source": "Europe PMC",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e: print(f"  ✗ {e}")
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 7. Dergipark ────────────────────────────────────────────────────────────
def fetch_dergipark(keywords, days_back, seen_urls):
    print("\n🇹🇷 Dergipark taranıyor...")
    papers = []
    tr_keywords = [k for k in keywords if any(c > '\u0100' or k in [
        "tekvando","spor psikolojisi","spor biyomekaniği","beden eğitimi",
        "spor performans analizi","egzersiz fizyolojisi","antrenörlük bilimi",
        "spor motivasyonu","spor pedagojisi","spor hekimliği","dövüş sporu"
    ] for c in k)] or keywords[:3]

    for kw in tr_keywords[:4]:
        url = f"https://dergipark.org.tr/tr/search?q={urllib.parse.quote(kw)}&section=article"
        raw = fetch_url(url)
        if not raw: time.sleep(1); continue
        try:
            # Dergipark HTML parse — makale linklerini bul
            import re
            links = re.findall(r'href="(https://dergipark\.org\.tr/tr/pub/[^"]+/article/\d+)"', raw)
            titles = re.findall(r'class="article-title[^"]*"[^>]*>\s*<a[^>]*>([^<]+)<', raw)
            dates = re.findall(r'(\d{4})', raw)

            for i, link in enumerate(links[:5]):
                if link in seen_urls: continue
                title = titles[i].strip() if i < len(titles) else "Başlık yok"
                papers.append({
                    "id": f"dergipark_{link.split('/')[-1]}",
                    "title": title, "authors": "", "date": "",
                    "url": link, "source": "Dergipark",
                    "added_at": datetime.utcnow().isoformat()
                })
        except Exception as e: print(f"  ✗ {e}")
        time.sleep(1)
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 8. CORE ─────────────────────────────────────────────────────────────────
def fetch_core(keywords, days_back, seen_urls):
    print("\n🔓 CORE taranıyor...")
    papers = []
    cutoff = iso_date_from_days_back(days_back)
    query = " OR ".join(keywords[:4])
    url = (
        "https://api.core.ac.uk/v3/search/works"
        f"?q={urllib.parse.quote(query)}"
        f"&limit=15&sort=publishedDate&order=desc"
    )
    raw = fetch_url(url)
    if not raw: return papers
    try:
        cutoff_dt = datetime.utcnow() - timedelta(days=days_back)
        for item in json.loads(raw).get("results",[]):
            pub_date = (item.get("publishedDate","") or "")[:10]
            try:
                if pub_date and datetime.strptime(pub_date,"%Y-%m-%d") < cutoff_dt: continue
            except: pass
            doi = item.get("doi","")
            paper_url = f"https://doi.org/{doi}" if doi else item.get("downloadUrl","")
            if not paper_url or paper_url in seen_urls: continue
            authors = item.get("authors",[])
            author_names = ", ".join(
                (a.get("name","") if isinstance(a,dict) else str(a))
                for a in authors[:3]
            )
            papers.append({
                "id": f"core_{item.get('id','')}",
                "title": item.get("title",""),
                "authors": author_names, "date": pub_date,
                "url": paper_url, "source": "CORE",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e: print(f"  ✗ {e}")
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 9. CrossRef ─────────────────────────────────────────────────────────────
def fetch_crossref(keywords, days_back, seen_urls):
    print("\n🔗 CrossRef taranıyor...")
    papers = []
    cutoff = iso_date_from_days_back(days_back)
    query = " ".join(keywords[:3])
    url = (
        "https://api.crossref.org/works"
        f"?query={urllib.parse.quote(query)}"
        f"&filter=from-pub-date:{cutoff}"
        "&rows=20&sort=published&order=desc"
        "&mailto=research@tracker.com"
    )
    raw = fetch_url(url)
    if not raw: return papers
    try:
        items = json.loads(raw).get("message",{}).get("items",[])
        for item in items:
            doi = item.get("DOI","")
            paper_url = f"https://doi.org/{doi}" if doi else ""
            if not paper_url or paper_url in seen_urls: continue
            date_parts = item.get("published",{}).get("date-parts",[[]])[0]
            pub_date = "-".join(str(d).zfill(2) for d in date_parts) if date_parts else ""
            authors_raw = item.get("author",[])
            authors = ", ".join(
                f"{a.get('family','')} {a.get('given','')[0] if a.get('given') else ''}".strip()
                for a in authors_raw[:3]
            )
            title_list = item.get("title",[])
            title = title_list[0] if title_list else ""
            if not title: continue
            papers.append({
                "id": f"crossref_{doi.replace('/','_')}",
                "title": title, "authors": authors, "date": pub_date,
                "url": paper_url, "source": "CrossRef",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e: print(f"  ✗ {e}")
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── 10. KCI (Korea) ─────────────────────────────────────────────────────────
def fetch_kci(keywords, days_back, seen_urls):
    print("\n🇰🇷 KCI taranıyor...")
    papers = []
    kr_keywords = [k for k in keywords if any('\uAC00' <= c <= '\uD7A3' for c in k)]
    if not kr_keywords:
        kr_keywords = ["태권도", "품새", "겨루기"]

    for kw in kr_keywords[:3]:
        url = (
            "https://www.kci.go.kr/kciportal/po/search/poArtiSearList.kci"
            f"?artiTitle={urllib.parse.quote(kw)}&orderBy=pubYear&orderByDir=desc"
        )
        raw = fetch_url(url)
        if not raw: time.sleep(1); continue
        try:
            import re
            links = re.findall(r'href="(/kciportal/po/search/poArtiSearDetail\.kci\?[^"]+)"', raw)
            titles = re.findall(r'class="tit"[^>]*>([^<]+)<', raw)
            for i, link in enumerate(links[:5]):
                full_url = f"https://www.kci.go.kr{link}"
                if full_url in seen_urls: continue
                title = titles[i].strip() if i < len(titles) else "제목 없음"
                papers.append({
                    "id": f"kci_{abs(hash(full_url))}",
                    "title": title, "authors": "", "date": "",
                    "url": full_url, "source": "KCI",
                    "added_at": datetime.utcnow().isoformat()
                })
        except Exception as e: print(f"  ✗ {e}")
        time.sleep(1)
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── Ana Fonksiyon ────────────────────────────────────────────────────────────
def main():
    KEYWORDS = load_keywords()
    print("="*60)
    print("🥋 Taekwondo & Spor Bilimleri Makale Takip Agent")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"🔍 {len(KEYWORDS)} anahtar kelime · Son {DAYS_BACK} gün · 10 kaynak")
    print("="*60)

    existing = load_existing()
    seen_urls = set(existing.get("seen_urls",[]))
    all_papers = existing.get("papers",[])
    new_papers = []

    new_papers += fetch_pubmed(KEYWORDS, DAYS_BACK, seen_urls);       time.sleep(1)
    new_papers += fetch_arxiv(KEYWORDS, DAYS_BACK, seen_urls);        time.sleep(1)
    new_papers += fetch_semantic_scholar(KEYWORDS, DAYS_BACK, seen_urls); time.sleep(1)
    new_papers += fetch_doaj(KEYWORDS, DAYS_BACK, seen_urls);         time.sleep(1)
    new_papers += fetch_openalex(KEYWORDS, DAYS_BACK, seen_urls);     time.sleep(1)
    new_papers += fetch_europe_pmc(KEYWORDS, DAYS_BACK, seen_urls);   time.sleep(1)
    new_papers += fetch_dergipark(KEYWORDS, DAYS_BACK, seen_urls);    time.sleep(1)
    new_papers += fetch_core(KEYWORDS, DAYS_BACK, seen_urls);         time.sleep(1)
    new_papers += fetch_crossref(KEYWORDS, DAYS_BACK, seen_urls);     time.sleep(1)
    new_papers += fetch_kci(KEYWORDS, DAYS_BACK, seen_urls)

    for p in new_papers: seen_urls.add(p["url"])
    combined = (new_papers + all_papers)[:1000]

    sources = {}
    for p in combined:
        sources[p["source"]] = sources.get(p["source"], 0) + 1

    save_data({
        "papers": combined,
        "seen_urls": list(seen_urls)[-5000:],
        "last_updated": datetime.utcnow().isoformat(),
        "stats": {
            "total": len(combined),
            "new_today": len(new_papers),
            "sources": sources
        }
    })

    if not KEYWORDS_FILE.exists():
        with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
            json.dump({"keywords": KEYWORDS}, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"✅ Tamamlandı! {len(new_papers)} yeni · Toplam {len(combined)} makale")
    print("Kaynaklar:", " | ".join(f"{k}:{v}" for k,v in sources.items()))
    print("="*60)

if __name__ == "__main__":
    main()
