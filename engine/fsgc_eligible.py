#!/usr/bin/env python3
# fsgc_eligible.py - Genera JSON eleggibili San Marino

import json
import re
from datetime import datetime
from pathlib import Path

# Database cognomi sammarinesi
SM_SURNAMES = [
    "Bernardi", "Gasperoni", "Mularoni", "Valentini", "Guidi",
    "Casali", "Belluzzi", "Righi", "Della Valle", "Berardi",
    "Battistini", "Benedettini", "Bollini", "Busignani", "Ceccoli",
    "Felici", "Gatti", "Giovagnoli", "Grandoni", "Muccioli"
]

def analyze_for_eligibility(item):
    """Analizza un item OB1 per eleggibilità SM"""
    title = item.get("label", "").lower()
    score = 0
    eligibility_type = None
    surname_match = None
    
    # Check cognomi
    for surname in SM_SURNAMES:
        if surname.lower() in title:
            score = 75
            surname_match = surname
            eligibility_type = "SURNAME_MATCH"
            break
    
    # Check contesto youth
    if any(k in title for k in ["u19", "u20", "u21", "youth", "giovani", "primavera"]):
        score += 15
    
    # Check se è transfer/convocation
    if item.get("anomaly_type") == "TRANSFER_SIGNAL":
        score += 10
    
    return score, eligibility_type, surname_match

def generate_fsgc_json():
    """Genera JSON eleggibili in formato OB1"""
    
    # Carica daily.json
    daily_path = Path("output/daily.json")
    if not daily_path.exists():
        print("[ERROR] daily.json non trovato")
        return
    
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
            "potential": len(eligible_items) - sum(1 for i in eligible_items if i.get("surname_found")),
            "high_confidence": sum(1 for i in eligible_items if i["eligibility_score"] >= 75),
            "medium_confidence": sum(1 for i in eligible_items if 50 <= i["eligibility_score"] < 75)
        },
        "items": eligible_items[:10]  # Top 10
    }
    
    # Salva JSON
    output_file = f"output/fsgc_eligible_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(fsgc_payload, f, ensure_ascii=False, indent=2)
    
    print(f"[FSGC] Generato {output_file}")
    print(f"[FSGC] Trovati {len(eligible_items)} potenziali eleggibili")
    
    # Genera anche snapshot
    snapshot_dir = Path("output/snapshots")
    snapshot_dir.mkdir(exist_ok=True)
    snapshot_file = snapshot_dir / f"fsgc_{datetime.now().strftime('%Y-%m-%d')}.json"
    with open(snapshot_file, 'w', encoding='utf-8') as f:
        json.dump(fsgc_payload, f, ensure_ascii=False, indent=2)
    
    return fsgc_payload

if __name__ == "__main__":
    result = generate_fsgc_json()
    
    if result and result["eligible_found"] > 0:
        print("\nTop candidati:")
        for item in result["items"][:3]:
            print(f"- {item['label'][:60]}...")
            print(f"  Score: {item['eligibility_score']}/100")
            if item.get('surname_found'):
                print(f"  Cognome: {item['surname_found']}")
