#!/usr/bin/env python3
# fsgc_diaspora_hunter_v4.py - Basato su ricerca diaspora reale

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# DATI REALI DALLA RICERCA
DIASPORA_DATA = {
    "usa": {
        "population": 3000,
        "cities": ["detroit", "troy", "michigan", "new york", "nyc"],
        "weight": 3.0,  # Detroit/Troy concentrazione massima
        "keywords": ["michigan", "detroit", "troy", "new york", "mls", "usl"]
    },
    "argentina": {
        "population": 1600,
        "cities": ["buenos aires", "córdoba", "pergamino", "mendoza", "jujuy", "río negro"],
        "weight": 2.5,  # 6 associazioni ufficiali
        "keywords": ["argentina", "argentino", "river", "boca", "racing", "primera b", "primera c"]
    },
    "italy": {
        "population": 5724,
        "cities": ["roma", "milano", "torino", "napoli", "bologna"],
        "weight": 2.0,  # Più grande ma più integrata
        "keywords": ["italia", "serie c", "serie d", "lega pro", "eccellenza"]
    },
    "france": {
        "population": 1881,
        "cities": ["paris", "lyon", "marseille", "nice"],
        "weight": 1.5,  # 700 a Parigi
        "keywords": ["france", "français", "ligue 2", "national", "cfa"]
    },
    "brazil": {
        "population": 500,  # Stimato, non confermato
        "cities": ["são paulo", "rio", "santos"],
        "weight": 1.0,
        "keywords": ["brasil", "brasileiro", "série b", "série c"]
    }
}

# COGNOMI REALI PIÙ COMUNI (dalla ricerca)
TOP_SURNAMES = {
    "tier1": [  # Top 10 più comuni
        "Gasperoni",  # 786 persone
        "Guidi",      # 667
        "Casadei",    # 457
        "Zanotti",    # 397
        "Giardi",     # 396
        "Mularoni",
        "Belluzzi",
        "Della Valle",
        "Benedettini",
        "Ceccoli"
    ],
    "tier2": [  # Altri comuni documentati
        "Bollini", "Mazza", "Nataloni", "Fabbri",
        "Valentini", "Casali", "Righi", "Berardi",
        "Battistini", "Felici", "Gatti", "Giovagnoli"
    ],
    "tier3": [  # Cognomi con varianti diaspora
        "Rossi", "Conti", "Guerra", "Stefanelli",
        "Forcellini", "Francini", "Morri", "Nicolini",
        "Selva", "Terenzi", "Ugolini", "Zafferani"
    ]
}

# VARIANTI COGNOMI PER PAESE
SURNAME_VARIANTS = {
    "Gasperoni": ["Gasperoni", "Gasparoni", "Gasperon", "Gasperón"],  # Spagnolo -ón
    "Guidi": ["Guidi", "Guido", "Guid", "Guidy"],
    "Zanotti": ["Zanotti", "Zanoti", "Zanott", "Zanotto"],
    "Giardi": ["Giardi", "Giard", "Jardí", "Jardy"],  # Francese/Spagnolo
    "Casadei": ["Casadei", "Casadey", "Casade", "Casadé"],
    "Mularoni": ["Mularoni", "Mullaroni", "Mularón", "Mularony"],
    "Belluzzi": ["Belluzzi", "Bellucci", "Belluz", "Belluzzy"],
    "Della Valle": ["Della Valle", "DellaValle", "Dellavalle", "Del Valle", "Delvalle"],
    "Benedettini": ["Benedettini", "Benedettino", "Benedetti", "Benedettin"],
    "Felici": ["Felici", "Felice", "Feliz", "Felix"],  # Latino/Spagnolo
    "Fabbri": ["Fabbri", "Fabri", "Faber", "Fabre"],  # Latino/Francese
    "Rossi": ["Rossi", "Rossy", "Ross", "Rosi", "Rosso"],
    "Stefanelli": ["Stefanelli", "Estefanelli", "Stefanel", "Stephanel"],  # Spagnolo/Francese
}

# CASI NOTI DI SUCCESSO (dalla ricerca)
SUCCESS_CASES = {
    "Andy Selva": {
        "born": "Roma",
        "mother": "San Marinese",
        "career": "8 goals in 73 caps",
        "pattern": "Italian-born with SM parent"
    },
    "Massimo Bonini": {
        "career": "Refused Italy for San Marino",
        "pattern": "Loyalty over opportunity"
    }
}

class DiasporaHunterV4:
    def __init__(self):
        self.all_surnames = []
        for tier in TOP_SURNAMES.values():
            self.all_surnames.extend(tier)
        
        self.all_variants = []
        for variants in SURNAME_VARIANTS.values():
            self.all_variants.extend(variants)
    
    def check_surname_with_context(self, text: str) -> Tuple[int, Optional[str], Optional[str], int]:
        """Check cognomi con peso basato su tier e contesto"""
        text_lower = text.lower()
        
        # Check Tier 1 (più comuni)
        for surname in TOP_SURNAMES["tier1"]:
            for variant in SURNAME_VARIANTS.get(surname, [surname]):
                if self._surname_match(variant.lower(), text_lower):
                    return (90, surname, variant, 1)
        
        # Check Tier 2
        for surname in TOP_SURNAMES["tier2"]:
            for variant in SURNAME_VARIANTS.get(surname, [surname]):
                if self._surname_match(variant.lower(), text_lower):
                    return (75, surname, variant, 2)
        
        # Check Tier 3
        for surname in TOP_SURNAMES["tier3"]:
            for variant in SURNAME_VARIANTS.get(surname, [surname]):
                if self._surname_match(variant.lower(), text_lower):
                    return (60, surname, variant, 3)
        
        return (0, None, None, 0)
    
    def _surname_match(self, surname: str, text: str) -> bool:
        """Match intelligente per cognomi"""
        patterns = [
            rf'\b{surname}\b',                    # Cognome esatto
            rf'\b\w+\s+{surname}\b',              # Nome + Cognome
            rf'\b{surname}\s+\w+\b',              # Cognome + Nome (sudamerica)
            rf'\b\w+\s+{surname}\s+\w+\b',        # Nome + Cognome + Secondo
        ]
        
        for pattern in patterns:
            if re.search(pattern, text):
                return True
        return False
    
    def check_diaspora_location(self, text: str) -> Tuple[int, Optional[str]]:
        """Check location con pesi basati su popolazione reale"""
        text_lower = text.lower()
        best_score = 0
        best_location = None
        
        for country, data in DIASPORA_DATA.items():
            # Check città specifiche (più peso)
            for city in data["cities"]:
                if city in text_lower:
                    score = 30 * data["weight"]
                    if score > best_score:
                        best_score = score
                        best_location = f"{country}:{city}"
            
            # Check keywords generici
            for keyword in data["keywords"]:
                if keyword in text_lower:
                    score = 20 * data["weight"]
                    if score > best_score:
                        best_score = score
                        best_location = country
        
        return (int(best_score), best_location)
    
    def check_league_level(self, text: str) -> Tuple[int, Optional[str]]:
        """Check livello competitivo (serie minori = più probabile)"""
        text_lower = text.lower()
        
        leagues = {
            "high_opportunity": {  # Serie minori, alta opportunità
                "patterns": ["serie c", "serie d", "lega pro", "eccellenza", "promozione",
                           "primera b", "primera c", "torneo federal", "regional",
                           "série b", "série c", "série d", "estadual",
                           "ligue 2", "national", "cfa", "usl", "npsl"],
                "score": 30,
                "level": "semi-pro"
            },
            "medium_opportunity": {
                "patterns": ["serie b", "championship", "segunda división",
                           "2. bundesliga", "ligue 1"],
                "score": 20,
                "level": "professional"
            },
            "low_opportunity": {  # Top league, difficile
                "patterns": ["serie a", "premier league", "la liga", "bundesliga",
                           "primeira divisão", "mls"],
                "score": 10,
                "level": "elite"
            }
        }
        
        for category, data in leagues.items():
            for pattern in data["patterns"]:
                if pattern in text_lower:
                    return (data["score"], data["level"])
        
        return (0, None)
    
    def check_age_profile(self, text: str) -> Tuple[int, Optional[str]]:
        """Check età con focus su 18-25 (ideale per switch)"""
        text_lower = text.lower()
        
        age_patterns = [
            (r'\b(18|19|20)\s*(años|anni|years|ans|anos)\b', 35, "perfect"),
            (r'\b(21|22|23)\s*(años|anni|years|ans|anos)\b', 30, "ideal"),
            (r'\b(24|25)\s*(años|anni|years|ans|anos)\b', 25, "good"),
            (r'\b(26|27|28)\s*(años|anni|years|ans|anos)\b', 15, "acceptable"),
            (r'\bu[-\s]?(19|20|21)\b', 30, "youth"),
            (r'\bsub[-\s]?(19|20|21)\b', 30, "youth"),
        ]
        
        for pattern, score, category in age_patterns:
            if re.search(pattern, text_lower):
                return (score, category)
        
        return (0, None)
    
    def check_naturalization_signals(self, text: str) -> Tuple[int, List[str]]:
        """Check segnali di possibile naturalizzazione"""
        text_lower = text.lower()
        score = 0
        signals = []
        
        patterns = {
            "oriundo": 40,
            "eligible": 35,
            "cittadinanza": 35,
            "passport": 30,
            "dual national": 30,
            "grandparent": 25,
            "nonno": 25,
            "abuelo": 25,
            "overlooked": 20,
            "non convocato": 20,
            "no call-up": 20,
        }
        
        for pattern, points in patterns.items():
            if pattern in text_lower:
                score += points
                signals.append(pattern)
        
        return (score, signals)
    
    def analyze_complete(self, item: Dict) -> Dict:
        """Analisi completa con tutti i fattori"""
        label = item.get("label", "")
        full_text = f"{label} {' '.join(item.get('why', []))}"
        
        # Tutti i check
        surname_score, original, variant, tier = self.check_surname_with_context(full_text)
        location_score, location = self.check_diaspora_location(full_text)
        league_score, league = self.check_league_level(full_text)
        age_score, age_cat = self.check_age_profile(full_text)
        nat_score, nat_signals = self.check_naturalization_signals(full_text)
        
        # Score totale pesato
        total_score = surname_score + location_score + league_score + age_score + nat_score
        
        # Determina priorità
        if total_score >= 120:
            priority = "🚨 CRITICAL - CONTACT IMMEDIATELY"
        elif total_score >= 100:
            priority = "⚠️ HIGH - Research genealogy"
        elif total_score >= 80:
            priority = "📍 MEDIUM - Monitor closely"
        elif total_score >= 60:
            priority = "👀 LOW - Add to watchlist"
        else:
            priority = "📝 MINIMAL - Archive"
        
        # Costruisci intelligence report
        return {
            "entity": "DIASPORA_TARGET",
            "label": label,
            "total_score": total_score,
            "priority": priority,
            "surname": {
                "found": variant,
                "original": original,
                "tier": tier,
                "score": surname_score
            },
            "location": {
                "identified": location,
                "score": location_score,
                "population": DIASPORA_DATA.get(location.split(":")[0], {}).get("population", 0) if location else 0
            },
            "competitive_level": {
                "league": league,
                "score": league_score
            },
            "age_profile": {
                "category": age_cat,
                "score": age_score
            },
            "naturalization": {
                "signals": nat_signals,
                "score": nat_score
            },
            "action": self._generate_action(total_score, location, variant, tier),
            "links": item.get("links", [])
        }
    
    def _generate_action(self, score: int, location: str, surname: str, tier: int) -> str:
        """Genera azione specifica basata su dati"""
        if score >= 120:
            if location and "argentina" in location.lower():
                return f"🚨 IMMEDIATE: Check CEMLA database for {surname} family immigration records"
            elif location and "detroit" in location.lower():
                return f"🚨 IMMEDIATE: Contact San Marino Club Troy for {surname} family"
            else:
                return f"🚨 IMMEDIATE: Verify {surname} lineage - Tier {tier} surname"
        
        elif score >= 100:
            return f"⚠️ Research Ellis Island/CEMLA records for {surname} emigration"
        
        elif score >= 80:
            return f"📍 Monitor performance, gather family history on {surname}"
        
        else:
            return "👀 Add to long-term tracking database"

def generate_enhanced_report():
    """Genera report con dati reali diaspora"""
    
    # Load daily.json
    daily_path = Path("output/daily.json")
    if not daily_path.exists():
        print("[ERROR] daily.json not found")
        return None
    
    with open(daily_path, 'r', encoding='utf-8') as f:
        daily_data = json.load(f)
    
    hunter = DiasporaHunterV4()
    targets = []
    
    # Analizza tutti gli items
    for item in daily_data.get("items", []):
        analysis = hunter.analyze_complete(item)
        if analysis["total_score"] >= 50:  # Soglia minima
            targets.append(analysis)
    
    # Ordina per score
    targets.sort(key=lambda x: x["total_score"], reverse=True)
    
    # Stats per paese
    country_stats = {}
    for target in targets:
        loc = target["location"]["identified"]
        if loc:
            country = loc.split(":")[0]
            country_stats[country] = country_stats.get(country, 0) + 1
    
    # Genera report finale
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "source": "FSGC-DiasporaHunter-v4",
        "based_on": "Real San Marino diaspora research",
        "diaspora_stats": {
            "total_diaspora": 13000,
            "usa": 3000,
            "italy": 5724,
            "france": 1881,
            "argentina": 1600
        },
        "analysis": {
            "total_scanned": len(daily_data.get("items", [])),
            "targets_found": len(targets),
            "critical": sum(1 for t in targets if "CRITICAL" in t["priority"]),
            "high": sum(1 for t in targets if "HIGH" in t["priority"]),
            "by_country": country_stats
        },
        "targets": targets[:20]  # Top 20
    }
    
    # Salva report
    output_dir = Path("output")
    output_file = output_dir / f"fsgc_diaspora_{datetime.now().strftime('%Y-%m-%d')}.json"
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n[DIASPORA HUNTER v4] Report generated: {output_file}")
    print(f"[DIASPORA HUNTER v4] Based on REAL diaspora data")
    print(f"[DIASPORA HUNTER v4] Key locations: Detroit/Troy, Argentina, Italy, France")
    
    # Alert per critical finds
    if report["analysis"]["critical"] > 0:
        print("\n🚨 CRITICAL TARGETS FOUND!")
        for target in targets[:3]:
            if "CRITICAL" in target["priority"]:
                print(f"\n→ {target['label'][:60]}...")
                print(f"  Score: {target['total_score']}")
                if target["surname"]["found"]:
                    print(f"  Surname: {target['surname']['found']} (Tier {target['surname']['tier']})")
                if target["location"]["identified"]:
                    print(f"  Location: {target['location']['identified']}")
                print(f"  ACTION: {target['action']}")
    
    return report

if __name__ == "__main__":
    print("=" * 60)
    print("FSGC DIASPORA HUNTER v4.0")
    print("Based on real San Marino emigration data")
    print("=" * 60)
    print("\nKey diaspora locations:")
    print("• USA: 3,000 (Detroit/Troy concentration)")
    print("• Italy: 5,724 (10 communities)")
    print("• France: 1,881 (Paris 700)")
    print("• Argentina: 1,600 (6 associations)")
    print("=" * 60)
    
    result = generate_enhanced_report()
