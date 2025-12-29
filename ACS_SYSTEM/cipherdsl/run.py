cd cipherdsl
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2) set your base seed (32 bytes recommended; we'll right-pad otherwise)
export EVOLVE_SEED='this_is_my_32byte_seed________'

# 3) make a sample plaintext
echo 'hello world from ADAP' > pt.txt

# 4) encrypt via DSL
./cipher_cli.py enc -p pipelines/evolvex.yaml -i pt.txt -o cipher.json

# 5) decrypt (note: uses the same EVOLVE_SEED)
./cipher_cli.py dec -k env:EVOLVE_SEED -i cipher.json -o out.txt
diff -u pt.txt out.txt  # should be empty (files identical)
