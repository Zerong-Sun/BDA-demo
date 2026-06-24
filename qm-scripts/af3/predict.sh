python /share/apps/alphafold3-v3.0.1/run_alphafold.py \
        --json_path=$1 \
        --model_dir=/work/bme-liz/db/af3/models \
        --db_dir=/share/apps/alphafold3-data \
        --output_dir=./output \
        --num_diffusion_samples=1 \