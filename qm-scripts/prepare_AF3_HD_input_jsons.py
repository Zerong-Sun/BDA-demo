import os
import sys
import json
from Bio import PDB

def extract_chain_sequence(pdb_file, chain_id="A"):
    parser = PDB.PDBParser(QUIET=True)
    structure = parser.get_structure("pdb", pdb_file)
    ppb = PDB.PPBuilder()
    for model in structure:
        for chain in model:
            if chain.id == chain_id:
                for pp in ppb.build_peptides(chain):
                    return str(pp.get_sequence())
    return ""

def modify_json(template_path, sequence_1, sequence_2, pdb_id):
    with open(template_path, 'r') as f:
        data = json.load(f)

    data["name"] = pdb_id
    for entry in data["sequences"]:
        if entry["protein"]["id"] == "A":
            entry["protein"]["sequence"] = sequence_1
        if entry["protein"]["id"] == "B":
            entry["protein"]["sequence"] = sequence_2

    return data

def main(pdb_folder, template_json):
    output_folder = os.path.join(pdb_folder, "input_jsons")
    os.makedirs(output_folder, exist_ok=True)

    for filename in os.listdir(pdb_folder):
        if filename.endswith(".pdb"):
            pdb_path = os.path.join(pdb_folder, filename)
            pdb_id = os.path.splitext(filename)[0]
            sequence_1 = extract_chain_sequence(pdb_path, "A")
            sequence_2 = extract_chain_sequence(pdb_path, "B")

            if sequence_1 and sequence_2:
                modified_json = modify_json(template_json, sequence_1, sequence_2, pdb_id)
                output_file = os.path.join(output_folder, f"{pdb_id}_input.json")
                with open(output_file, 'w') as out:
                    json.dump(modified_json, out, indent=2)
                print(f"Processed {filename} -> {output_file}")
            else:
                print(f"Chain A not found in {filename}, skipped.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python prepare_input_json.py <pdb_folder_path> <template_json_path>")
        sys.exit(1)
    main(sys.argv[1], sys.argv[2])
