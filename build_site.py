#!/usr/bin/env python3
"""
data/papers.json dosyasından statik HTML site oluşturur.
"""

import json
from pathlib import Path
from datetime import datetime

DATA_FILE = Path("data/papers.json")
OUTPUT_FILE = Path("docs/index.html")
OUTPUT_FILE.parent.mkdir(exist_ok=True)

def load_data():
    if not DATA_FILE.exists():
        return {"papers": [], "stats": {}, "last_updated": None}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def source_badge(source):
    classes = {
        "PubMed": ("pubmed", "#3b8beb"),
        "arXiv": ("arxiv", "#e05c00"),
        "Semantic Scholar": ("scholar", "#00cec9"),
        "DOAJ": ("doaj", "#6c5ce7"),
    }
    cls, color = classes.get(source, ("other", "#888"))
    return f'<span class="badge" style="background:rgba(0,0,0,0.3);border:1px solid {color};color:{color}">{source}</span>'

def build_html(data):
    papers = data.get("papers", [])
    stats = data.get("stats", {})
    last_updated = data.get("last_updated", "")
    
    if last_updated:
        try:
            dt = datetime.fromisoformat(last_updated)
            last_updated_str = dt.strftime("%d %B %Y, %H:%M UTC")
        except:
            last_updated_str = last_updated
    else:
        last_updated_str = "Henüz taranmadı"
    
    new_today = stats.get("new_today", 0)
    total = stats.get("total", len(papers))
    sources = stats.get("sources", {})
    cnt_pubmed = sources.get("pubmed", 0)
    cnt_arxiv = sources.get("arxiv", 0)
    cnt_scholar = sources.get("semantic_scholar", 0)
    
    # Paper cards HTML
    def paper_card(p, idx):
        title = p.get("title", "Başlık yok")
        authors = p.get("authors", "")
        date = p.get("date", "")
        url = p.get("url", "#")
        source = p.get("source", "")
        added = p.get("added_at", "")
        
        # Is new (added today)?
        is_new = False
        if added:
            try:
                added_dt = datetime.fromisoformat(added)
                is_new = (datetime.utcnow() - added_dt).days < 1
            except:
                pass
        
        new_badge = '<span class="new-badge">YENİ</span>' if is_new else ""
        
        return f"""
        <a class="paper-card" href="{url}" target="_blank" rel="noopener" data-source="{source.lower().replace(' ', '-')}">
          <div class="paper-top">
            {source_badge(source)}
            {new_badge}
            <span class="paper-date">{date}</span>
          </div>
          <div class="paper-title">{title}</div>
          {f'<div class="paper-authors">{authors}</div>' if authors else ''}
        </a>"""
    
    cards_html = "\n".join(paper_card(p, i) for i, p in enumerate(papers[:200]))
    
    html = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🥋 Taekwondo Makale Takip</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;800&display=swap');

  :root {{
    --bg: #08080f;
    --surface: #10101a;
    --border: #1c1c2e;
    --accent: #6c5ce7;
    --accent2: #00cec9;
    --text: #e0e0f0;
    --muted: #5a5a7a;
  }}

  * {{ margin: 0; padding: 0; box-sizing: border-box; }}

  body {{
    background: var(--bg);
    color: var(--text);
    font-family: 'Syne', sans-serif;
    min-height: 100vh;
  }}

  body::before {{
    content: '';
    position: fixed;
    inset: 0;
    background-image: 
      linear-gradient(rgba(108,92,231,0.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(108,92,231,0.025) 1px, transparent 1px);
    background-size: 48px 48px;
    pointer-events: none;
  }}

  .hero {{
    background: linear-gradient(135deg, #0d0d1f, #13132a);
    border-bottom: 1px solid var(--border);
    padding: 40px 24px 32px;
    text-align: center;
    position: relative;
  }}

  .hero-icon {{ font-size: 48px; margin-bottom: 12px; }}

  h1 {{
    font-size: 32px;
    font-weight: 800;
    letter-spacing: -1px;
    margin-bottom: 6px;
  }}

  h1 span {{
    background: linear-gradient(90deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}

  .hero-sub {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    color: var(--muted);
    margin-bottom: 24px;
  }}

  .stats-row {{
    display: flex;
    gap: 12px;
    justify-content: center;
    flex-wrap: wrap;
  }}

  .stat {{
    background: rgba(108,92,231,0.1);
    border: 1px solid rgba(108,92,231,0.25);
    border-radius: 20px;
    padding: 6px 18px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
  }}

  .stat b {{ color: var(--accent2); }}

  .container {{
    max-width: 900px;
    margin: 0 auto;
    padding: 32px 20px;
    position: relative;
  }}

  .filter-bar {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin-bottom: 24px;
    align-items: center;
  }}

  .filter-label {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--muted);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-right: 4px;
  }}

  .filter-btn {{
    padding: 6px 14px;
    border-radius: 20px;
    border: 1px solid var(--border);
    background: var(--surface);
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    cursor: pointer;
    transition: all 0.15s;
  }}

  .filter-btn:hover, .filter-btn.active {{
    border-color: var(--accent);
    color: var(--accent);
    background: rgba(108,92,231,0.1);
  }}

  .search-box {{
    flex: 1;
    min-width: 200px;
    padding: 8px 14px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    outline: none;
    margin-left: auto;
  }}

  .search-box:focus {{ border-color: var(--accent); }}
  .search-box::placeholder {{ color: var(--muted); }}

  .papers-grid {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}

  .paper-card {{
    display: block;
    padding: 16px 18px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    text-decoration: none;
    color: inherit;
    transition: all 0.15s;
    animation: fadeIn 0.3s ease;
  }}

  .paper-card:hover {{
    border-color: rgba(108,92,231,0.5);
    transform: translateX(4px);
    background: rgba(108,92,231,0.04);
  }}

  .paper-card.hidden {{ display: none; }}

  .paper-top {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }}

  .badge {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 10px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}

  .new-badge {{
    background: var(--accent2);
    color: #000;
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    font-weight: 800;
    padding: 2px 8px;
    border-radius: 10px;
    letter-spacing: 1px;
  }}

  .paper-date {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    color: var(--muted);
    margin-left: auto;
  }}

  .paper-title {{
    font-size: 14px;
    font-weight: 600;
    line-height: 1.5;
    color: var(--text);
    margin-bottom: 5px;
  }}

  .paper-authors {{
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
  }}

  .empty-state {{
    text-align: center;
    padding: 64px 24px;
    color: var(--muted);
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
  }}

  .empty-icon {{ font-size: 40px; margin-bottom: 12px; opacity: 0.4; }}

  .footer {{
    text-align: center;
    padding: 32px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: var(--muted);
    border-top: 1px solid var(--border);
  }}

  @keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(4px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  @media (max-width: 600px) {{
    h1 {{ font-size: 22px; }}
    .filter-bar {{ gap: 6px; }}
  }}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-icon">🥋</div>
  <h1>Taekwondo <span>Makale Takip</span></h1>
  <div class="hero-sub">// son güncelleme: {last_updated_str}</div>
  <div class="stats-row">
    <div class="stat">Toplam <b>{total}</b> makale</div>
    <div class="stat">Bugün <b>{new_today}</b> yeni</div>
    <div class="stat">PubMed <b>{cnt_pubmed}</b></div>
    <div class="stat">arXiv <b>{cnt_arxiv}</b></div>
    <div class="stat">Scholar <b>{cnt_scholar}</b></div>
  </div>
</div>

<div class="container">

  <div class="filter-bar">
    <span class="filter-label">Filtre:</span>
    <button class="filter-btn active" onclick="filterSource('all', this)">Tümü</button>
    <button class="filter-btn" onclick="filterSource('pubmed', this)">PubMed</button>
    <button class="filter-btn" onclick="filterSource('arxiv', this)">arXiv</button>
    <button class="filter-btn" onclick="filterSource('semantic-scholar', this)">Scholar</button>
    <button class="filter-btn" onclick="filterSource('doaj', this)">DOAJ</button>
    <button class="filter-btn" onclick="filterSource('openalex', this)">OpenAlex</button>
    <button class="filter-btn" onclick="filterSource('europe-pmc', this)">Europe PMC</button>
    <button class="filter-btn" onclick="filterSource('dergipark', this)">Dergipark</button>
    <button class="filter-btn" onclick="filterSource('core', this)">CORE</button>
    <button class="filter-btn" onclick="filterSource('crossref', this)">CrossRef</button>
    <button class="filter-btn" onclick="filterSource('kci', this)">KCI</button>
    <input class="search-box" type="text" placeholder="🔍 Başlık veya yazar ara..." oninput="searchPapers(this.value)" />
  </div>

  <div class="papers-grid" id="papersGrid">
    {cards_html if papers else '<div class="empty-state"><div class="empty-icon">📭</div>Henüz makale yok.<br>GitHub Actions ilk çalıştığında makaleler burada görünecek.</div>'}
  </div>

</div>

<div class="footer">
  🤖 Her gün 09:00 (TR) otomatik güncellenir · GitHub Actions + Python
</div>

<script>
  let currentSource = 'all';
  let currentSearch = '';

  function filterSource(src, btn) {{
    currentSource = src;
    document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    applyFilters();
  }}

  function searchPapers(q) {{
    currentSearch = q.toLowerCase();
    applyFilters();
  }}

  function applyFilters() {{
    const cards = document.querySelectorAll('.paper-card');
    cards.forEach(card => {{
      const srcMatch = currentSource === 'all' || card.dataset.source === currentSource;
      const title = card.querySelector('.paper-title')?.textContent.toLowerCase() || '';
      const authors = card.querySelector('.paper-authors')?.textContent.toLowerCase() || '';
      const searchMatch = !currentSearch || title.includes(currentSearch) || authors.includes(currentSearch);
      card.classList.toggle('hidden', !(srcMatch && searchMatch));
    }});
  }}
</script>

</body>
</html>"""
    return html

def main():
    print("🌐 Web sitesi oluşturuluyor...")
    data = load_data()
    html = build_html(data)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✓ {OUTPUT_FILE} oluşturuldu ({len(html)} karakter)")

if __name__ == "__main__":
    main()
