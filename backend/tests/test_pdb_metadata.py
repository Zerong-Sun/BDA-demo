from backend.app.services.artifacts import parse_pdb_metadata


def test_parse_pdb_metadata_uses_fixed_pdb_columns():
    content = "\n".join([
        "ATOM      9  N   ASP A   2      58.894  11.704   2.101  1.00 56.97           N  ",
        "ATOM     10  CA  ASP A   2      58.231  10.775   1.188  1.00 60.96           C  ",
        "ATOM     11  N   CYS B  10A     57.100  10.100   0.500  1.00 50.00           N  ",
        "HETATM   12  O   HOH A 201      60.000  12.000   3.000  1.00 30.00           O  ",
    ])

    assert parse_pdb_metadata(content) == {
        "atom_count": 4,
        "chain_count": 2,
        "chains": ["A", "B"],
        "residue_count": 2,
    }
