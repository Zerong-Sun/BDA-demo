from __future__ import annotations

import json
import sqlite3

from .sweet_protein_planner import SCAFFOLDS


REGULATORY = [
    ("reg_fda_grn_1142", "FDA", "GRN 1142", "Brazzein produced by Komagataella phaffii", "official_notice", "https://www.cfsanappsexternal.fda.gov/scripts/fdcc/?id=1142&set=GRASNotices"),
    ("reg_fda_grn_1183", "FDA", "GRN 1183", "Modified monellin produced by Komagataella phaffii", "official_notice", "https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1183&set=GRASNotices"),
    ("reg_fda_grn_1207", "FDA", "GRN 1207", "Brazzein preparation produced by Aspergillus oryzae", "official_notice", "https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1207&set=grasnotices"),
    ("reg_fda_grn_1269", "FDA", "GRN 1269", "Modified monellin sweet protein", "official_notice", "https://www.hfpappexternal.fda.gov/scripts/fdcc/index.cfm?id=1269&set=GRASNotices"),
]


def register_sweet_protein_catalog(connection: sqlite3.Connection) -> None:
    for scaffold in SCAFFOLDS:
        connection.execute(
            """
            INSERT INTO protein_scaffolds (
                scaffold_id, name, scaffold_class, properties_json,
                evidence_json, risk_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                scaffold_class=excluded.scaffold_class,
                properties_json=excluded.properties_json,
                evidence_json=excluded.evidence_json,
                risk_json=excluded.risk_json,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                f"scaffold_{scaffold['id']}",
                scaffold["name"],
                scaffold["route"],
                json.dumps({
                    "priority": scaffold["priority"],
                    "design_focus": scaffold["design_focus"],
                    "strengths": scaffold["strengths"],
                }),
                json.dumps([]),
                json.dumps(scaffold["risks"]),
            ),
        )
    for subunit, domain, label in (
        ("TAS1R2", "VFD", "TAS1R2 Venus flytrap domain"),
        ("TAS1R2", "CRD", "TAS1R2 cysteine-rich domain"),
        ("TAS1R3", "CRD", "TAS1R3 cysteine-rich domain"),
        ("TAS1R2/TAS1R3", "interface", "Heterodimer extracellular interface"),
    ):
        region_id = f"region_{subunit.lower().replace('/', '_')}_{domain.lower()}"
        connection.execute(
            """
            INSERT OR IGNORE INTO receptor_regions (
                receptor_region_id, receptor_name, species, subunit,
                domain, region_label, evidence_json, status
            ) VALUES (?, 'TAS1R2/TAS1R3', 'Homo sapiens', ?, ?, ?, '[]', 'hypothesis')
            """,
            (region_id, subunit, domain, label),
        )
    for record_id, authority, identifier, subject, status_class, uri in REGULATORY:
        connection.execute(
            """
            INSERT INTO regulatory_precedents (
                regulatory_precedent_id, jurisdiction, authority, identifier,
                subject, status_class, official_uri, conditions_json,
                evidence_json, verification_status
            ) VALUES (?, 'United States', ?, ?, ?, ?, ?, '{}', '[]', 'pending_verification')
            ON CONFLICT(authority, identifier) DO UPDATE SET
                subject=excluded.subject,
                status_class=excluded.status_class,
                official_uri=excluded.official_uri,
                updated_at=CURRENT_TIMESTAMP
            """,
            (record_id, authority, identifier, subject, status_class, uri),
        )
    for key, title, category in (
        ("expression_and_folding", "Expression and correct folding", "manufacturing"),
        ("purification_quality", "Purification and quality", "quality"),
        ("stability", "Stability and formulation", "quality"),
        ("receptor_function", "Human sweet-receptor function", "function"),
        ("sensory", "Approved sensory evaluation", "sensory"),
        ("food_matrix", "Food-matrix validation", "application"),
        ("process", "Fermentation and downstream economics", "manufacturing"),
        ("safety_regulatory", "Safety and regulatory evidence", "safety"),
    ):
        connection.execute(
            """
            INSERT OR IGNORE INTO assay_templates (
                assay_template_id, assay_key, title, category, template_json
            ) VALUES (?, ?, ?, ?, '{}')
            """,
            (f"assay_{key}", key, title, category),
        )
    connection.execute(
        """
        INSERT OR IGNORE INTO food_matrix_profiles (
            food_matrix_profile_id, matrix_key, title, constraints_json, tests_json
        ) VALUES (
            'matrix_beverage', 'beverage', 'Beverage',
            '{"pH":[2.5,7],"processes":["pasteurization","UHT","carbonation"]}',
            '["clarity","precipitation","activity retention","shelf stability","sensory compatibility"]'
        )
        """
    )
