from __future__ import annotations

import math
from collections import Counter
from typing import Any

import httpx

USER_AGENT = "BDA-Workbench/1.0 (programmable biomaterials research assistant)"
TIMEOUT = 20.0

AA_MASS = {
    "A": 89.09, "R": 174.20, "N": 132.12, "D": 133.10, "C": 121.16,
    "E": 147.13, "Q": 146.15, "G": 75.07, "H": 155.16, "I": 131.17,
    "L": 131.17, "K": 146.19, "M": 149.21, "F": 165.19, "P": 115.13,
    "S": 105.09, "T": 119.12, "W": 204.23, "Y": 181.19, "V": 117.15,
}
HYDROPHOBIC = frozenset("AILMFWVY")


def _client() -> httpx.Client:
    from ..settings import get_settings

    proxy = get_settings().bda_research_proxy.strip() or None
    return httpx.Client(
        timeout=TIMEOUT,
        follow_redirects=True,
        headers={"User-Agent": USER_AGENT},
        proxy=proxy,
    )


def search_literature(query: str, *, limit: int = 5) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit), 10))
    with _client() as client:
        response = client.get(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            params={
                "query": query,
                "format": "json",
                "pageSize": safe_limit,
                "resultType": "core",
            },
        )
        response.raise_for_status()
        payload = response.json()
    results = []
    for item in payload.get("resultList", {}).get("result", []):
        source = item.get("source")
        identifier = item.get("id")
        results.append({
            "source": source,
            "identifier": identifier,
            "title": item.get("title"),
            "authors": item.get("authorString"),
            "journal": item.get("journalTitle"),
            "year": item.get("pubYear"),
            "doi": item.get("doi"),
            "pmid": item.get("pmid"),
            "pmcid": item.get("pmcid"),
            "cited_by_count": item.get("citedByCount"),
            "is_open_access": item.get("isOpenAccess") == "Y",
            "abstract": item.get("abstractText"),
            "url": (
                f"https://europepmc.org/article/{source}/{identifier}"
                if source and identifier else None
            ),
        })
    return {
        "query": query,
        "source": "Europe PMC",
        "results": results,
        "total": int(payload.get("hitCount") or len(results)),
    }


def get_europe_pmc_full_text(pmcid: str) -> str:
    normalized = pmcid.strip().upper()
    if not normalized.startswith("PMC") or not normalized[3:].isdigit():
        raise ValueError("invalid_pmcid")
    with _client() as client:
        response = client.get(
            f"https://www.ebi.ac.uk/europepmc/webservices/rest/{normalized}/fullTextXML",
        )
        response.raise_for_status()
        return response.text


def search_pdb(query: str, *, limit: int = 5) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit), 10))
    request = {
        "query": {
            "type": "terminal",
            "service": "full_text",
            "parameters": {"value": query},
        },
        "return_type": "entry",
        "request_options": {
            "paginate": {"start": 0, "rows": safe_limit},
            "results_content_type": ["experimental"],
        },
    }
    with _client() as client:
        response = client.post(
            "https://search.rcsb.org/rcsbsearch/v2/query",
            json=request,
        )
        response.raise_for_status()
        payload = response.json()
    ids = [item["identifier"] for item in payload.get("result_set", [])]
    details = []
    for pdb_id in ids:
        try:
            details.append(get_pdb_entry(pdb_id))
        except (httpx.HTTPError, ValueError) as exc:
            details.append({
                "pdb_id": pdb_id,
                "url": f"https://www.rcsb.org/structure/{pdb_id}",
                "detail_error": str(exc)[:200],
            })
    return {
        "query": query,
        "source": "RCSB PDB",
        "pdb_ids": ids,
        "results": details,
        "total": int(payload.get("total_count") or len(ids)),
    }


def get_pdb_entry(pdb_id: str) -> dict[str, Any]:
    normalized = pdb_id.strip().upper()
    if not normalized or len(normalized) > 12:
        raise ValueError("invalid_pdb_id")
    with _client() as client:
        response = client.get(
            f"https://data.rcsb.org/rest/v1/core/entry/{normalized}",
        )
        response.raise_for_status()
        item = response.json()
    entry_info = item.get("rcsb_entry_info") or {}
    citation = item.get("rcsb_primary_citation") or {}
    return {
        "pdb_id": normalized,
        "title": (item.get("struct") or {}).get("title"),
        "experimental_method": entry_info.get("experimental_method"),
        "resolution": entry_info.get("resolution_combined"),
        "polymer_entity_count": entry_info.get("polymer_entity_count"),
        "nonpolymer_entity_count": entry_info.get("nonpolymer_entity_count"),
        "release_date": (item.get("rcsb_accession_info") or {}).get("initial_release_date"),
        "citation_title": citation.get("title"),
        "citation_doi": citation.get("pdbx_database_id_DOI"),
        "citation_pubmed_id": citation.get("pdbx_database_id_PubMed"),
        "url": f"https://www.rcsb.org/structure/{normalized}",
        "download_url": f"https://files.rcsb.org/download/{normalized}.cif",
    }


def calculate_sequence_properties(sequence: str) -> dict[str, Any]:
    normalized = "".join(sequence.split()).upper()
    invalid = sorted(set(normalized) - set(AA_MASS))
    if not normalized:
        raise ValueError("empty_sequence")
    if invalid:
        raise ValueError(f"invalid_amino_acids:{''.join(invalid)}")
    counts = Counter(normalized)
    molecular_weight = sum(AA_MASS[aa] for aa in normalized) - 18.015 * (len(normalized) - 1)
    net_charge_proxy = (
        counts["K"] + counts["R"] + 0.1 * counts["H"]
        - counts["D"] - counts["E"]
    )
    hydrophobic_fraction = sum(counts[aa] for aa in HYDROPHOBIC) / len(normalized)
    aromatic_fraction = sum(counts[aa] for aa in "FWY") / len(normalized)
    return {
        "length": len(normalized),
        "molecular_weight_da": round(molecular_weight, 2),
        "hydrophobic_fraction": round(hydrophobic_fraction, 4),
        "aromatic_fraction": round(aromatic_fraction, 4),
        "cysteine_count": counts["C"],
        "net_charge_proxy": round(net_charge_proxy, 2),
        "estimated_extinction_280": int(
            5500 * counts["W"] + 1490 * counts["Y"] + 125 * math.floor(counts["C"] / 2)
        ),
        "note": (
            "These are sequence-only screening descriptors, not substitutes for "
            "structure-based developability prediction or experimental measurement."
        ),
    }


def search_uniprot(
    query: str,
    *,
    limit: int = 5,
    reviewed_only: bool = True,
) -> dict[str, Any]:
    safe_limit = max(1, min(int(limit), 10))
    effective_query = f"({query})"
    if reviewed_only:
        effective_query += " AND reviewed:true"
    with _client() as client:
        response = client.get(
            "https://rest.uniprot.org/uniprotkb/search",
            params={
                "query": effective_query,
                "format": "json",
                "size": safe_limit,
                "fields": (
                    "accession,id,protein_name,gene_names,organism_name,length,"
                    "reviewed,cc_function,cc_subunit,cc_pathway,go_p,ft_domain"
                ),
            },
        )
        response.raise_for_status()
        payload = response.json()
    results = []
    for item in payload.get("results", []):
        accession = item.get("primaryAccession")
        description = item.get("proteinDescription") or {}
        recommended = description.get("recommendedName") or {}
        protein_name = ((recommended.get("fullName") or {}).get("value"))
        genes = [
            (gene.get("geneName") or {}).get("value")
            for gene in item.get("genes", [])
            if (gene.get("geneName") or {}).get("value")
        ]
        comments = item.get("comments") or []
        results.append({
            "accession": accession,
            "entry_name": item.get("uniProtkbId"),
            "protein_name": protein_name,
            "genes": genes,
            "organism": (item.get("organism") or {}).get("scientificName"),
            "sequence_length": (item.get("sequence") or {}).get("length"),
            "reviewed": item.get("entryType") == "UniProtKB reviewed (Swiss-Prot)",
            "function_comments": [
                text.get("value")
                for comment in comments if comment.get("commentType") == "FUNCTION"
                for text in comment.get("texts", [])
                if text.get("value")
            ],
            "pathway_comments": [
                text.get("value")
                for comment in comments if comment.get("commentType") == "PATHWAY"
                for text in comment.get("texts", [])
                if text.get("value")
            ],
            "url": f"https://www.uniprot.org/uniprotkb/{accession}/entry" if accession else None,
        })
    return {
        "query": query,
        "source": "UniProtKB",
        "reviewed_only": reviewed_only,
        "results": results,
    }


def analyze_reactome_pathways(
    identifiers: list[str],
    *,
    species: str = "Homo sapiens",
    limit: int = 10,
) -> dict[str, Any]:
    cleaned = [str(item).strip() for item in identifiers if str(item).strip()]
    if not cleaned:
        raise ValueError("identifiers_required")
    safe_limit = max(1, min(int(limit), 25))
    with _client() as client:
        response = client.post(
            "https://reactome.org/AnalysisService/identifiers/projection",
            params={"pageSize": safe_limit, "page": 1},
            content="\n".join(cleaned),
            headers={"Content-Type": "text/plain"},
        )
        response.raise_for_status()
        payload = response.json()
    pathways = []
    for item in payload.get("pathways", []):
        pathway_species = (item.get("species") or {}).get("name")
        if species and pathway_species and pathway_species.lower() != species.lower():
            continue
        entities = item.get("entities") or {}
        pathways.append({
            "pathway_id": item.get("stId"),
            "name": item.get("name"),
            "species": pathway_species,
            "p_value": item.get("pValue"),
            "fdr": item.get("fdr"),
            "entities_found": entities.get("found"),
            "entities_total": entities.get("total"),
            "url": (
                f"https://reactome.org/PathwayBrowser/#/{item.get('stId')}"
                if item.get("stId") else None
            ),
        })
    return {
        "source": "Reactome",
        "identifiers": cleaned,
        "species": species,
        "pathways": pathways[:safe_limit],
        "identifiers_not_found": payload.get("identifiersNotFound"),
        "analysis_token": (payload.get("summary") or {}).get("token"),
        "note": (
            "Pathway membership and enrichment are database annotations/statistical results; "
            "they do not by themselves establish a causal mechanism in the user's biological context."
        ),
    }
