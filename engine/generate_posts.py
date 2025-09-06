#!/usr/bin/env python3
# generate_posts.py - Genera post LinkedIn dal daily.json

import json
from datetime import datetime
from pathlib import Path

def generate_linkedin_post():
    """Genera post bilingue per LinkedIn"""
    daily = Path("output/daily.json")
    if not daily.exists():
        print("[ERROR] daily.json non trovato")
        return None
    
    with open(daily, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    items = data.get('items', [])[:3]
    if not items:
        print("[WARNING] Nessun item trovato in daily.json")
        return None
    
    date = datetime.now().strftime('%d/%m')
    
    # Estrai highlight con emoji per regioni
    highlights = []
    region_emojis = {
        'africa': '🌍',
        'asia': '🌏', 
        'south-america': '🌎',
        'international': '🌐'
    }
    
    for item in items:
        label = item.get('label', '')[:50]
        tags = item.get('why', [])
        emoji = ''
        for region, em in region_emojis.items():
            if region in tags:
                emoji = em + ' '
                break
        highlights.append(f"• {emoji}{label}...")
    
    # Conta regioni attive
    breakdown = data.get('region_breakdown', {})
    regions = sum(1 for v in breakdown.values() if v > 0)
    total = len(data.get('items', []))
    
    # Costruisci post
    post = f"""OB1 Radar - {date}

{chr(10).join(highlights)}

{total} segnali da {regions} regioni.
Non è magia. È metodo.

Demo → mtornani.github.io/OB1-Radar

---

OB1 Radar - {date}

{chr(10).join(highlights)}

{total} signals from {regions} regions.
It's not magic. It's method.

Demo → mtornani.github.io/OB1-Radar

#OB1Radar #U20 #ScoutingIntelligence #FootballData"""
    
    # Salva post
    output = Path("output/linkedin_post.txt")
    output.parent.mkdir(exist_ok=True)
    with open(output, 'w', encoding='utf-8') as f:
        f.write(post)
    
    print(f"[SUCCESS] Post LinkedIn generato: {output}")
    
    # Genera anche versione corta per Twitter/X
    twitter_post = f"""OB1 Radar - {date}

Top find: {items[0].get('label', '')[:60]}...

{total} segnali U19/U20 oggi.

mtornani.github.io/OB1-Radar

#OB1Radar #U20"""
    
    twitter_output = Path("output/twitter_post.txt")
    with open(twitter_output, 'w', encoding='utf-8') as f:
        f.write(twitter_post)
    
    print(f"[SUCCESS] Post Twitter generato: {twitter_output}")
    return post

if __name__ == "__main__":
    generate_linkedin_post()
