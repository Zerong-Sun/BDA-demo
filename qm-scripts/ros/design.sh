input_pdb=$1
pdb=${1##*/}
name=${pdb%.*}

if [ ! -e output/ ]; then mkdir output ; fi
outpath="output"

exepath="mpirun -np 24 /work/ccse-yangyc/apps/il/rosetta/source/bin/rosetta_scripts.mpi.linuxgccrelease"
#exepath="/work/bme-liz/software/rosetta/source/bin/rosetta_scripts.default.linuxgccrelease"

${exepath} \
-s ${1} \
-parser:protocol score.xml \
-ex1 \
-ex2 \
-beta \
-nstruct 1 \
-renumber_pdb 1 \
-per_chain_renumbering 1 \
-overwrite \
-out:path:all ${outpath} \
-out::file::pdb_comments \
-mute core.select.residue_selector.SecondaryStructureSelector \
-ignore_unrecognized_res | tee ${outpath}/design.log
