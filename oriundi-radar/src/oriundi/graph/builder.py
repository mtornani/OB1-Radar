"""Build and export a simple knowledge graph from resolved candidates."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from ..data_sources.base import RecordBatch

SCHEMA_PREFIX = "@prefix oriundi: <https://oriundi.ob1.dev/schema#> ."
ENTITY_PREFIX = "@prefix entity: <https://oriundi.ob1.dev/entity/> ."


def build_graph(records: RecordBatch) -> Dict[str, List[dict]]:
    nodes: Dict[str, dict] = {}
    edges: List[dict] = []
    for record in records:
        node_id = record.get("entity.cluster_id") or record.get("player.full_name", "anon")
        if node_id not in nodes:
            nodes[node_id] = {
                "uri": f"entity:{node_id}",
                "label": record.get("entity.canonical_name") or record.get("player.full_name", ""),
                "birth_date": record.get("player.birth_date"),
                "birth_place": record.get("player.birth_place"),
                "current_club": record.get("player.current_club"),
            }
        article_url = record.get("article.url")
        if article_url:
            edges.append(
                {
                    "source": f"entity:{node_id}",
                    "target": f"<{article_url}>",
                    "predicate": "oriundi:mentionedIn",
                }
            )
    return {"nodes": list(nodes.values()), "edges": edges}


def export_graph(graph: Dict[str, List[dict]], destination: Path) -> None:
    lines: List[str] = [SCHEMA_PREFIX, ENTITY_PREFIX, ""]
    for node in graph.get("nodes", []):
        uri = node["uri"]
        lines.append(f"{uri} a oriundi:Player ;")
        if node.get("label"):
            lines.append(f'    oriundi:label "{node["label"]}" ;')
        if node.get("birth_date"):
            lines.append(f'    oriundi:birthDate "{node["birth_date"]}" ;')
        if node.get("birth_place"):
            lines.append(f'    oriundi:birthPlace "{node["birth_place"]}" ;')
        if node.get("current_club"):
            lines.append(f'    oriundi:currentClub "{node["current_club"]}" ;')
        if lines[-1].endswith(";"):
            lines[-1] = lines[-1][:-1] + "."
        else:
            lines.append(".")
        lines.append("")
    for edge in graph.get("edges", []):
        lines.append(f"{edge['source']} {edge['predicate']} {edge['target']} .")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")


__all__ = ["build_graph", "export_graph"]

