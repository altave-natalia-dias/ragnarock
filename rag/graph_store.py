"""
BountyRAG — Neo4j Graph Store
Ontologia focada em Bug Bounty com exploit-chaining via Cypher.

Schema:
  Nodes:    Alvo, Subdominio, Endpoint, Parametro, Tecnologia,
            Vulnerabilidade, Writeup_Ref, Tecnica (MITRE)
  Edges:    TEM_SUBDOMINIO, TEM_ENDPOINT, POSSUI_PARAMETRO,
            RODA, VULNERAVEL_A, MENCIONADA_EM, LEVA_A,
            MITRE_ATTACK, MESMA_FAMILIA
"""
from __future__ import annotations
import sys, json, textwrap
from typing import Optional
from pathlib import Path

VENV_SITE = "/home/altave/venv/lib/python3.12/site-packages"
if VENV_SITE not in sys.path:
    sys.path.insert(0, VENV_SITE)

from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import ServiceUnavailable, AuthError

# ── Connection ─────────────────────────────────────────────────────── #
NEO4J_URI  = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASS = "changeme"

SEVERITY_ORDER = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "INFO": 0}


class GraphStore:
    """Wrapper Neo4j para ontologia de Bug Bounty."""

    def __init__(
        self,
        uri:  str = NEO4J_URI,
        user: str = NEO4J_USER,
        pwd:  str = NEO4J_PASS,
    ):
        self._driver = None
        self._ok     = False
        try:
            self._driver = GraphDatabase.driver(uri, auth=basic_auth(user, pwd))
            self._driver.verify_connectivity()
            self._ok = True
            self._apply_schema()
        except (ServiceUnavailable, AuthError) as e:
            print(f"  [GraphStore] Neo4j unavailable ({e}) — graph features disabled")

    @property
    def ok(self) -> bool:
        return self._ok

    def close(self):
        if self._driver:
            self._driver.close()

    # ── Schema ────────────────────────────────────────────────────── #

    def _apply_schema(self):
        constraints = [
            "CREATE CONSTRAINT alvo_domain IF NOT EXISTS FOR (n:Alvo) REQUIRE n.domain IS UNIQUE",
            "CREATE CONSTRAINT sub_fqdn IF NOT EXISTS FOR (n:Subdominio) REQUIRE n.fqdn IS UNIQUE",
            "CREATE CONSTRAINT tech_key IF NOT EXISTS FOR (n:Tecnologia) REQUIRE n.key IS UNIQUE",
            "CREATE CONSTRAINT vuln_key IF NOT EXISTS FOR (n:Vulnerabilidade) REQUIRE n.key IS UNIQUE",
            "CREATE CONSTRAINT writeup_id IF NOT EXISTS FOR (n:Writeup_Ref) REQUIRE n.chroma_id IS UNIQUE",
            "CREATE CONSTRAINT tecnica_id IF NOT EXISTS FOR (n:Tecnica) REQUIRE n.technique_id IS UNIQUE",
            "CREATE CONSTRAINT endpoint_key IF NOT EXISTS FOR (n:Endpoint) REQUIRE n.key IS UNIQUE",
        ]
        with self._driver.session() as s:
            for c in constraints:
                try:
                    s.run(c)
                except Exception:
                    pass

    # ── Node upserts ──────────────────────────────────────────────── #

    def upsert_alvo(self, domain: str, asn: str = "", ip_ranges: list[str] | None = None) -> None:
        if not self._ok: return
        with self._driver.session() as s:
            s.run(
                """
                MERGE (a:Alvo {domain: $domain})
                SET a.asn = $asn,
                    a.ip_ranges = $ip_ranges,
                    a.updated = timestamp()
                """,
                domain=domain, asn=asn, ip_ranges=json.dumps(ip_ranges or []),
            )

    def upsert_subdominio(
        self, fqdn: str, parent_domain: str,
        ip: str = "", status: int = 0, title: str = "", techs: list[str] | None = None,
    ) -> None:
        if not self._ok: return
        with self._driver.session() as s:
            s.run(
                """
                MERGE (s:Subdominio {fqdn: $fqdn})
                SET s.ip = $ip,
                    s.status = $status,
                    s.title  = $title,
                    s.techs  = $techs,
                    s.updated = timestamp()
                WITH s
                MATCH (a:Alvo {domain: $parent})
                MERGE (a)-[:TEM_SUBDOMINIO]->(s)
                """,
                fqdn=fqdn, parent=parent_domain,
                ip=ip, status=status, title=title,
                techs=json.dumps(techs or []),
            )

    def upsert_endpoint(
        self, path: str, fqdn: str, method: str = "GET",
        params: list[str] | None = None, status: int = 200,
        content_type: str = "",
    ) -> None:
        if not self._ok: return
        key = f"{fqdn}:{method}:{path}"
        with self._driver.session() as s:
            s.run(
                """
                MERGE (e:Endpoint {key: $key})
                SET e.path = $path,
                    e.method = $method,
                    e.status = $status,
                    e.content_type = $ct,
                    e.updated = timestamp()
                WITH e
                MATCH (s:Subdominio {fqdn: $fqdn})
                MERGE (s)-[:TEM_ENDPOINT]->(e)
                """,
                key=key, path=path, fqdn=fqdn,
                method=method, status=status, ct=content_type,
            )
            # upsert params
            for p in (params or []):
                pk = f"{key}:{p}"
                s.run(
                    """
                    MERGE (pr:Parametro {key: $pk})
                    SET pr.name = $name
                    WITH pr
                    MATCH (e:Endpoint {key: $ek})
                    MERGE (e)-[:POSSUI_PARAMETRO]->(pr)
                    """,
                    pk=pk, name=p, ek=key,
                )

    def upsert_tecnologia(
        self, name: str, version: str = "", cpe: str = "",
        fqdn: str = "", endpoint_key: str = "",
    ) -> None:
        if not self._ok: return
        key = f"{name.lower()}:{version}".rstrip(":")
        with self._driver.session() as s:
            s.run(
                """
                MERGE (t:Tecnologia {key: $key})
                SET t.name = $name,
                    t.version = $version,
                    t.cpe = $cpe
                """,
                key=key, name=name, version=version, cpe=cpe,
            )
            if fqdn:
                s.run(
                    """
                    MATCH (s:Subdominio {fqdn: $fqdn})
                    MATCH (t:Tecnologia {key: $key})
                    MERGE (s)-[:RODA]->(t)
                    """,
                    fqdn=fqdn, key=key,
                )
            if endpoint_key:
                s.run(
                    """
                    MATCH (e:Endpoint {key: $ek})
                    MATCH (t:Tecnologia {key: $key})
                    MERGE (e)-[:RODA]->(t)
                    """,
                    ek=endpoint_key, key=key,
                )

    def upsert_vulnerabilidade(
        self,
        name: str,
        cve: str = "",
        cwe: str = "",
        severity: str = "MEDIUM",
        tactic: str = "",
        technique_id: str = "",
        description: str = "",
    ) -> None:
        if not self._ok: return
        key = (cve or name.lower().replace(" ", "_"))[:80]
        with self._driver.session() as s:
            s.run(
                """
                MERGE (v:Vulnerabilidade {key: $key})
                SET v.name = $name,
                    v.cve  = $cve,
                    v.cwe  = $cwe,
                    v.severity = $severity,
                    v.severity_score = $score,
                    v.tactic = $tactic,
                    v.description = $desc
                """,
                key=key, name=name, cve=cve, cwe=cwe,
                severity=severity,
                score=SEVERITY_ORDER.get(severity.upper(), 2),
                tactic=tactic, desc=description[:500],
            )
            if technique_id:
                s.run(
                    """
                    MATCH (v:Vulnerabilidade {key: $key})
                    MERGE (t:Tecnica {technique_id: $tid})
                    SET t.name = $tname
                    MERGE (v)-[:MITRE_ATTACK]->(t)
                    """,
                    key=key, tid=technique_id, tname=name,
                )

    def link_tech_to_vuln(self, tech_key: str, vuln_key: str) -> None:
        if not self._ok: return
        with self._driver.session() as s:
            s.run(
                """
                MATCH (t:Tecnologia {key: $tk})
                MATCH (v:Vulnerabilidade {key: $vk})
                MERGE (t)-[:VULNERAVEL_A]->(v)
                """,
                tk=tech_key, vk=vuln_key,
            )

    def link_vuln_to_vuln(self, from_key: str, to_key: str, chain_label: str = "") -> None:
        """Explicit exploit chain: vuln A leads to vuln B."""
        if not self._ok: return
        with self._driver.session() as s:
            s.run(
                """
                MATCH (a:Vulnerabilidade {key: $ak})
                MATCH (b:Vulnerabilidade {key: $bk})
                MERGE (a)-[r:LEVA_A]->(b)
                SET r.label = $label
                """,
                ak=from_key, bk=to_key, label=chain_label,
            )

    def upsert_writeup_ref(
        self,
        chroma_id: str,
        title: str,
        url: str,
        vuln_type: str = "",
        platform: str = "",
        severity: str = "",
    ) -> None:
        if not self._ok: return
        with self._driver.session() as s:
            s.run(
                """
                MERGE (w:Writeup_Ref {chroma_id: $cid})
                SET w.title = $title,
                    w.url   = $url,
                    w.vuln_type = $vt,
                    w.platform = $plat,
                    w.severity = $sev
                """,
                cid=chroma_id, title=title[:200], url=url,
                vt=vuln_type, plat=platform, sev=severity,
            )

    def link_vuln_to_writeup(self, vuln_key: str, chroma_id: str) -> None:
        if not self._ok: return
        with self._driver.session() as s:
            s.run(
                """
                MATCH (v:Vulnerabilidade {key: $vk})
                MATCH (w:Writeup_Ref {chroma_id: $cid})
                MERGE (v)-[:MENCIONADA_EM]->(w)
                """,
                vk=vuln_key, cid=chroma_id,
            )

    # ── Query: Attack Paths ───────────────────────────────────────── #

    def attack_paths_for_domain(self, domain: str, max_depth: int = 4) -> list[dict]:
        """
        Find all attack paths from a domain's tech stack to vulnerabilities.
        Returns ordered list of paths (highest severity first).
        """
        if not self._ok: return []
        with self._driver.session() as s:
            result = s.run(
                """
                MATCH (a:Alvo {domain: $domain})-[:TEM_SUBDOMINIO]->(sub:Subdominio)
                      -[:RODA]->(t:Tecnologia)-[:VULNERAVEL_A]->(v:Vulnerabilidade)
                OPTIONAL MATCH (v)-[:MENCIONADA_EM]->(w:Writeup_Ref)
                OPTIONAL MATCH (v)-[:MITRE_ATTACK]->(mt:Tecnica)
                RETURN
                  sub.fqdn          AS fqdn,
                  sub.status        AS status,
                  t.name            AS tech,
                  t.version         AS version,
                  v.name            AS vuln,
                  v.severity        AS severity,
                  v.severity_score  AS score,
                  v.cve             AS cve,
                  v.cwe             AS cwe,
                  v.tactic          AS tactic,
                  mt.technique_id   AS technique_id,
                  collect(w.chroma_id)[0..3] AS writeup_ids,
                  collect(w.title)[0..3]     AS writeup_titles
                ORDER BY score DESC, fqdn ASC
                """,
                domain=domain,
            )
            return [dict(r) for r in result]

    def exploit_chains(self, domain: str) -> list[dict]:
        """
        Find multi-step exploit chains: vuln A → vuln B (LEVA_A relationships).
        """
        if not self._ok: return []
        with self._driver.session() as s:
            result = s.run(
                """
                MATCH (a:Alvo {domain: $domain})-[:TEM_SUBDOMINIO]->(:Subdominio)
                      -[:RODA]->(:Tecnologia)-[:VULNERAVEL_A]->(v1:Vulnerabilidade)
                      -[:LEVA_A]->(v2:Vulnerabilidade)
                OPTIONAL MATCH (v2)-[:LEVA_A]->(v3:Vulnerabilidade)
                RETURN
                  v1.name AS step1,  v1.severity AS sev1,
                  v2.name AS step2,  v2.severity AS sev2,
                  v3.name AS step3,  v3.severity AS sev3,
                  (CASE WHEN v3 IS NOT NULL THEN 3 ELSE 2 END) AS chain_len
                ORDER BY chain_len DESC, sev1 DESC
                LIMIT 10
                """,
                domain=domain,
            )
            return [dict(r) for r in result]

    def infra_map(self, domain: str) -> list[dict]:
        """Full infrastructure map: domain → subdomains → endpoints → technologies."""
        if not self._ok: return []
        with self._driver.session() as s:
            result = s.run(
                """
                MATCH (a:Alvo {domain: $domain})-[:TEM_SUBDOMINIO]->(sub:Subdominio)
                OPTIONAL MATCH (sub)-[:RODA]->(t:Tecnologia)
                OPTIONAL MATCH (sub)-[:TEM_ENDPOINT]->(e:Endpoint)
                RETURN
                  sub.fqdn    AS fqdn,
                  sub.ip      AS ip,
                  sub.status  AS status,
                  sub.title   AS title,
                  collect(DISTINCT t.name + ':' + coalesce(t.version,'?')) AS techs,
                  collect(DISTINCT e.method + ' ' + e.path)[0..10]         AS endpoints
                ORDER BY sub.fqdn ASC
                """,
                domain=domain,
            )
            return [dict(r) for r in result]

    def tech_vuln_matrix(self, domain: str) -> list[dict]:
        """
        Matrix: tech → vulns found in writeups for this target's tech stack.
        Used for exploit suggestion even before active testing.
        """
        if not self._ok: return []
        with self._driver.session() as s:
            result = s.run(
                """
                MATCH (a:Alvo {domain: $domain})-[:TEM_SUBDOMINIO]->(:Subdominio)
                      -[:RODA]->(t:Tecnologia)
                OPTIONAL MATCH (t)-[:VULNERAVEL_A]->(v:Vulnerabilidade)
                OPTIONAL MATCH (v)-[:MENCIONADA_EM]->(w:Writeup_Ref)
                RETURN
                  t.name       AS tech,
                  t.version    AS version,
                  collect(DISTINCT v.name)     AS vulns,
                  collect(DISTINCT v.severity) AS severities,
                  collect(DISTINCT w.chroma_id)[0..5] AS writeup_ids
                ORDER BY t.name ASC
                """,
                domain=domain,
            )
            return [dict(r) for r in result]

    def shortest_attack_path(self, domain: str, target_vuln: str = "RCE") -> list[dict]:
        """
        Use Neo4j shortest path to find min-hop route from ANY tech
        in the target's infra to a critical vuln.
        """
        if not self._ok: return []
        with self._driver.session() as s:
            result = s.run(
                """
                MATCH (a:Alvo {domain: $domain})-[:TEM_SUBDOMINIO]->(:Subdominio)
                      -[:RODA]->(t:Tecnologia)
                MATCH (target:Vulnerabilidade)
                WHERE target.name CONTAINS $tvuln OR target.severity = 'CRITICAL'
                MATCH path = shortestPath((t)-[*1..5]->(target))
                RETURN
                  [n in nodes(path) | labels(n)[0] + ':' + coalesce(n.name, n.key, n.fqdn, '')] AS path_nodes,
                  length(path) AS hops
                ORDER BY hops ASC
                LIMIT 5
                """,
                domain=domain, tvuln=target_vuln,
            )
            return [dict(r) for r in result]

    # ── Stats ─────────────────────────────────────────────────────── #

    def stats(self) -> dict:
        if not self._ok: return {"error": "Neo4j offline"}
        with self._driver.session() as s:
            counts = {}
            for label in ["Alvo", "Subdominio", "Endpoint", "Tecnologia",
                          "Vulnerabilidade", "Writeup_Ref", "Parametro"]:
                r = s.run(f"MATCH (n:{label}) RETURN count(n) AS c").single()
                counts[label] = r["c"] if r else 0
            # relationship count
            r = s.run("MATCH ()-[r]->() RETURN count(r) AS c").single()
            counts["Relationships"] = r["c"] if r else 0
            return counts

    def clear_target(self, domain: str) -> None:
        """Remove all nodes associated with a target domain."""
        if not self._ok: return
        with self._driver.session() as s:
            s.run(
                """
                MATCH (a:Alvo {domain: $domain})-[:TEM_SUBDOMINIO]->(sub)
                OPTIONAL MATCH (sub)-[:TEM_ENDPOINT]->(e)-[:POSSUI_PARAMETRO]->(p)
                DETACH DELETE a, sub, e, p
                """,
                domain=domain,
            )


# ── Singleton ──────────────────────────────────────────────────────── #
_graph: GraphStore | None = None

def get_graph() -> GraphStore:
    global _graph
    if _graph is None:
        _graph = GraphStore()
    return _graph
