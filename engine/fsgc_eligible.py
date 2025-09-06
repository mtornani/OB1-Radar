#!/usr/bin/env python3
# fsgc_eligible.py - Genera JSON eleggibili San Marino

import json
import re
from datetime import datetime
from pathlib import Path

# Database cognomi sammarinesi esteso
SM_SURNAMES = [
    # Top 20 più comuni
    "Bernardi", "Gasperoni", "Mularoni", "Valentini", "Guidi",
    "Casali", "Belluzzi", "Righi", "Della Valle", "Berardi",
    "Battistini", "Benedettini", "Bollini", "Busignani", "Ceccoli",
    "Felici", "Gatti", "Giovagnoli", "Grandoni", "Muccioli",
    # Altri cognomi storici
    "Forcellini", "Francini", "Morri", "Nicolini", "Rossi",
    "Selva", "Stefanelli", "Terenzi", "Ugolini", "Zafferani",
    "Biordi", "Bugli", "Capicchioni", "Cecchetti", "Conti",
    "Fabbri", "Gasperoni", "Giardi", "Gobbi", "Guerra",
    "Lonfernini", "Mazza", "Michelotti", "Muratori", "Pelliccioni",
    "Renzi", "Righi", "Rinaldi", "Rossini", "Santolini",
    "Simoncini", "Stolfi", "Tamagnini", "Tomassoni", "Zonzini"
]

def analyze_for_eligibility(item):
    """Analizza un item OB1 per eleggibilità SM"""
    title = item.get("label", "")
    title_lower = title.lower()
    score = 0
    eligibility_type = None
    surname_match = None
    
    # Check cognomi (case insensitive)
    for surname in SM_SURNAMES:
        if surname.lower() in title_lower:
            score = 75
            surname_match = surname
            eligibility_type = "SURNAME_MATCH"
            break
    
    # Check contesto youth
    youth_keywords = ["u19", "u20", "u21", "u-19", "u-20", "u-21", 
                     "under 19", "under 20", "under 21",
                     "youth", "giovani", "primavera", "sub-20", "sub-19"]
    
    if any(k in title_lower for k in youth_keywords):
        score += 15
    
    # Check se è transfer/convocation
    if item.get("anomaly_type") == "TRANSFER_SIGNAL":
        score += 10
    elif item.get("anomaly_type") == "PLAYER_BURST":
        score += 5
    
    # Check per menzioni San Marino
    if "san marino" in title_lower or "sammarinese" in title_lower:
        score += 20
        if not eligibility_type:
            eligibility_type = "SM_MENTION"
    
    return score, eligibility_type, surname_match

def generate_fsgc_json():
    """Genera JSON eleggibili in formato OB1"""
    
    # Carica daily.json
    daily_path = Path("output/daily.json")
    if not daily_path.exists():
        print("[ERROR] daily.json non trovato")
        return None
    
    with open(daily_path, 'r', encoding='utf-8') as f:
        daily_data = json.load(f)
    
    eligible_items = []
    
    # Analizza ogni item
    for item in daily_data.get("items", []):
        score, elig_type, surname = analyze_for_eligibility(item)
        
        if score >= 50:  # Soglia minima
            # Crea item eleggibile
            eligible_item = {
                "entity": "ELIGIBLE_SM",
                "label": item["label"],
                "anomaly_type": elig_type or "POTENTIAL_ELIGIBLE",
                "eligibility_score": score,
                "surname_found": surname,
                "original_score": item.get("score", 0),
                "why": item.get("why", []) + ["SM_ELIGIBLE"],
                "links": item.get("links", [])
            }
            eligible_items.append(eligible_item)
    
    # Ordina per score eleggibilità
    eligible_items.sort(key=lambda x: x["eligibility_score"], reverse=True)
    
    # Crea payload FSGC
    fsgc_payload = {
        "generated_at_utc": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "source": "FSGC-EligibilityRadar",
        "mode": "eligibility_check",
        "total_scanned": len(daily_data.get("items", [])),
        "eligible_found": len(eligible_items),
        "eligibility_breakdown": {
            "surname_match": sum(1 for i in eligible_items if i.get("surname_found")),
            "sm_mention": sum(1 for i in eligible_items if i.get("anomaly_type") == "SM_MENTION"),
            "potential": len(eligible_items) - sum(1 for i in eligible_items if i.get("surname_found")),
            "high_confidence": sum(1 for i in eligible_items if i["eligibility_score"] >= 75),
            "medium_confidence": sum(1 for i in eligible_items if 50 <= i["eligibility_score"] < 75)
        },
        "items": eligible_items[:10]  # Top 10
    }
    
    # Salva JSON giornaliero
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    output_file = output_dir / f"fsgc_eligible_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fsgc_payload, f, ensure_ascii=False, indent=2)
    
    print(f"[FSGC] Generato {output_file}")
    print(f"[FSGC] Trovati {len(eligible_items)} potenziali eleggibili")
    
    # Genera anche snapshot per docs
    docs_dir = Path("docs")
    if docs_dir.exists():
        docs_file = docs_dir / "fsgc_eligible.json"
        with open(docs_file, 'w', encoding='utf-8') as f:
            json.dump(fsgc_payload, f, ensure_ascii=False, indent=2)
        print(f"[FSGC] Copiato in docs per GitHub Pages")
    
    # Se ci sono eleggibili, genera report testuale
    if eligible_items:
        report_lines = [
            f"FSGC Report Eleggibili - {datetime.now().strftime('%d/%m/%Y')}",
            "=" * 50,
            f"Trovati {len(eligible_items)} potenziali eleggibili\n"
        ]
        
        for i, item in enumerate(eligible_items[:5], 1):
            report_lines.append(f"{i}. {item['label']}")
            report_lines.append(f"   Score: {item['eligibility_score']}/100")
            if item.get('surname_found'):
                report_lines.append(f"   Cognome: {item['surname_found']}")
            report_lines.append(f"   Link: {item['links'][0] if item.get('links') else 'N/A'}")
            report_lines.append("")
        
        report_text = "\n".join(report_lines)
        report_file = output_dir / "fsgc_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"[FSGC] Report testuale: {report_file}")
    
    return fsgc_payload

if __name__ == "__main__":
    result = generate_fsgc_json()
    
    if result and result["eligible_found"] > 0:
        print("\nTop candidati eleggibili:")
        for item in result["items"][:3]:
            print(f"- {item['label'][:60]}...")
            print(f"  Score: {item['eligibility_score']}/100")
            if item.get('surname_found'):
                print(f"  Cognome: {item['surname_found']}")
