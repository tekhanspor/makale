#!/usr/bin/env python3
"""
Taekwondo & Spor Bilimleri Makale Takip Agent
Her gün GitHub Actions tarafından otomatik çalıştırılır.
"""

import json
import os
import time
import urllib.request
import urllib.parse
import urllib.error
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

# ─── Ayarlar ──────────────────────────────────────────────────────────────────

KEYWORDS = [
    "taekwondo",
    "태권도",
    "tae kwon do",
    "taekwondo biomechanics",
    "taekwondo training",
    "taekwondo performance",
    "taekwondo physiology",
    "martial arts combat sport",
]

DAYS_BACK = 3  # Kaç günlük makale taransın

DATA_FILE = Path("data/papers.json")
DATA_FILE.parent.mkdir(exist_ok=True)

# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

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

def fetch_url(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "TaekwondoResearchTracker/1.0 (Academic research bot)"
        })
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ✗ Hata: {url[:60]}... → {e}")
        return None

def date_from_days_back(days):
    d = datetime.utcnow() - timedelta(days=days)
    return d.strftime("%Y/%m/%d")

def date_iso_from_days_back(days):
    d = datetime.utcnow() - timedelta(days=days)
    return d.strftime("%Y-%m-%d")

# ─── PubMed ───────────────────────────────────────────────────────────────────

def fetch_pubmed(keywords, days_back, seen_urls):
    print("\n📗 PubMed taranıyor...")
    papers = []
    
    # İlk 3 keyword ile tara (rate limit için)
    main_keywords = keywords[:4]
    query = " OR ".join(f'"{k}"' for k in main_keywords)
    date_from = date_from_days_back(days_back)
    date_to = date_from_days_back(0)
    
    search_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        f"?db=pubmed&term={urllib.parse.quote(query)}"
        f"&mindate={date_from}&maxdate={date_to}&datetype=pdat"
        "&retmax=30&retmode=json&sort=date"
    )
    
    raw = fetch_url(search_url)
    if not raw:
        return papers
    
    try:
        data = json.loads(raw)
        ids = data.get("esearchresult", {}).get("idlist", [])
        print(f"  → {len(ids)} sonuç bulundu")
        if not ids:
            return papers
    except:
        return papers
    
    time.sleep(0.4)  # NCBI rate limit
    
    # Detayları çek
    summary_url = (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=pubmed&id={','.join(ids)}&retmode=json"
    )
    raw2 = fetch_url(summary_url)
    if not raw2:
        return papers
    
    try:
        sdata = json.loads(raw2)
        result = sdata.get("result", {})
        for pmid in ids:
            item = result.get(pmid, {})
            if not item:
                continue
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            if url in seen_urls:
                continue
            authors = ", ".join(
                a.get("name", "") for a in item.get("authors", [])[:3]
            )
            papers.append({
                "id": f"pubmed_{pmid}",
                "title": item.get("title", "").rstrip("."),
                "authors": authors,
                "date": item.get("pubdate", ""),
                "url": url,
                "source": "PubMed",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"  ✗ PubMed parse hatası: {e}")
    
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── arXiv ────────────────────────────────────────────────────────────────────

def fetch_arxiv(keywords, days_back, seen_urls):
    print("\n📘 arXiv taranıyor...")
    papers = []
    
    query = "+AND+".join(urllib.parse.quote(k) for k in keywords[:3])
    url = (
        "https://export.arxiv.org/api/query"
        f"?search_query=all:{query}"
        "&sortBy=submittedDate&sortOrder=descending&max_results=20"
    )
    
    raw = fetch_url(url)
    if not raw:
        return papers
    
    try:
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        root = ET.fromstring(raw)
        entries = root.findall("atom:entry", ns)
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        
        for entry in entries:
            published = entry.findtext("atom:published", "", ns)
            try:
                pub_dt = datetime.strptime(published[:10], "%Y-%m-%d")
                if pub_dt < cutoff:
                    continue
            except:
                continue
            
            paper_id = entry.findtext("atom:id", "", ns)
            paper_url = paper_id.replace("http://", "https://")
            if paper_url in seen_urls:
                continue
            
            authors = [
                a.findtext("atom:name", "", ns)
                for a in entry.findall("atom:author", ns)
            ]
            
            papers.append({
                "id": f"arxiv_{paper_url.split('/')[-1]}",
                "title": entry.findtext("atom:title", "", ns).strip().replace("\n", " "),
                "authors": ", ".join(authors[:3]),
                "date": published[:10],
                "url": paper_url,
                "source": "arXiv",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"  ✗ arXiv parse hatası: {e}")
    
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── Semantic Scholar ─────────────────────────────────────────────────────────

def fetch_semantic_scholar(keywords, days_back, seen_urls):
    print("\n📙 Semantic Scholar taranıyor...")
    papers = []
    
    for kw in keywords[:3]:
        query = urllib.parse.quote(kw)
        url = (
            "https://api.semanticscholar.org/graph/v1/paper/search"
            f"?query={query}"
            "&fields=title,authors,year,publicationDate,externalIds"
            "&limit=10&sort=publicationDate:desc"
        )
        
        raw = fetch_url(url)
        if not raw:
            time.sleep(1)
            continue
        
        try:
            data = json.loads(raw)
            cutoff = datetime.utcnow() - timedelta(days=days_back)
            
            for item in data.get("data", []):
                pub_date = item.get("publicationDate", "")
                if pub_date:
                    try:
                        if datetime.strptime(pub_date, "%Y-%m-%d") < cutoff:
                            continue
                    except:
                        pass
                
                paper_id = item.get("paperId", "")
                paper_url = f"https://www.semanticscholar.org/paper/{paper_id}"
                if paper_url in seen_urls:
                    continue
                
                doi = item.get("externalIds", {}).get("DOI", "")
                if doi:
                    paper_url = f"https://doi.org/{doi}"
                
                authors = [
                    a.get("name", "") for a in item.get("authors", [])[:3]
                ]
                
                papers.append({
                    "id": f"ss_{paper_id}",
                    "title": item.get("title", ""),
                    "authors": ", ".join(authors),
                    "date": pub_date or str(item.get("year", "")),
                    "url": paper_url,
                    "source": "Semantic Scholar",
                    "added_at": datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"  ✗ SS parse hatası ({kw}): {e}")
        
        time.sleep(1.2)  # Semantic Scholar rate limit
    
    # Deduplicate
    seen = set()
    unique = []
    for p in papers:
        if p["url"] not in seen and p["url"] not in seen_urls:
            seen.add(p["url"])
            unique.append(p)
    
    print(f"  ✓ {len(unique)} yeni makale")
    return unique

# ─── DOAJ (Directory of Open Access Journals) ────────────────────────────────

def fetch_doaj(keywords, days_back, seen_urls):
    print("\n📕 DOAJ taranıyor...")
    papers = []
    
    query = urllib.parse.quote(" OR ".join(keywords[:3]))
    url = (
        f"https://doaj.org/api/search/articles/{query}"
        "?sort=created_date:desc&pageSize=20"
    )
    
    raw = fetch_url(url)
    if not raw:
        return papers
    
    try:
        data = json.loads(raw)
        cutoff = datetime.utcnow() - timedelta(days=days_back)
        
        for item in data.get("results", []):
            bib = item.get("bibjson", {})
            created = item.get("created_date", "")[:10]
            try:
                if created and datetime.strptime(created, "%Y-%m-%d") < cutoff:
                    continue
            except:
                pass
            
            links = bib.get("link", [])
            paper_url = next(
                (l.get("url", "") for l in links if l.get("type") == "fulltext"),
                ""
            )
            if not paper_url or paper_url in seen_urls:
                continue
            
            authors = [
                a.get("name", "") for a in bib.get("author", [])[:3]
            ]
            pub_date = bib.get("year", "")
            
            papers.append({
                "id": f"doaj_{item.get('id', '')}",
                "title": bib.get("title", ""),
                "authors": ", ".join(authors),
                "date": pub_date,
                "url": paper_url,
                "source": "DOAJ",
                "added_at": datetime.utcnow().isoformat()
            })
    except Exception as e:
        print(f"  ✗ DOAJ parse hatası: {e}")
    
    print(f"  ✓ {len(papers)} yeni makale")
    return papers

# ─── Ana Fonksiyon ────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("🥋 Taekwondo Makale Takip Agent")
    print(f"📅 {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC")
    print(f"🔍 Keywords: {', '.join(KEYWORDS[:4])}...")
    print(f"📆 Son {DAYS_BACK} gün taranıyor")
    print("=" * 55)
    
    # Mevcut veriyi yükle
    existing = load_existing()
    seen_urls = set(existing.get("seen_urls", []))
    all_papers = existing.get("papers", [])
    
    new_papers = []
    
    # Tara
    new_papers += fetch_pubmed(KEYWORDS, DAYS_BACK, seen_urls)
    time.sleep(1)
    new_papers += fetch_arxiv(KEYWORDS, DAYS_BACK, seen_urls)
    time.sleep(1)
    new_papers += fetch_semantic_scholar(KEYWORDS, DAYS_BACK, seen_urls)
    time.sleep(1)
    new_papers += fetch_doaj(KEYWORDS, DAYS_BACK, seen_urls)
    
    # Yeni URL'leri kaydet
    for p in new_papers:
        seen_urls.add(p["url"])
    
    # Birleştir (en yeni önce)
    combined = new_papers + all_papers
    # Max 1000 makale tut
    combined = combined[:1000]
    
    # Kaydet
    save_data({
        "papers": combined,
        "seen_urls": list(seen_urls)[-5000:],
        "last_updated": datetime.utcnow().isoformat(),
        "stats": {
            "total": len(combined),
            "new_today": len(new_papers),
            "sources": {
                "pubmed": sum(1 for p in combined if p["source"] == "PubMed"),
                "arxiv": sum(1 for p in combined if p["source"] == "arXiv"),
                "semantic_scholar": sum(1 for p in combined if p["source"] == "Semantic Scholar"),
                "doaj": sum(1 for p in combined if p["source"] == "DOAJ"),
            }
        }
    })
    
    print("\n" + "=" * 55)
    print(f"✅ Tamamlandı! {len(new_papers)} yeni makale eklendi.")
    print(f"📚 Toplam: {len(combined)} makale")
    print("=" * 55)

if __name__ == "__main__":
    main()
