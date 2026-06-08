#!/usr/bin/env python3
import argparse, json, os, sys, yaml
from pathlib import Path

# --- supported ops we’ll lower into target langs ---
SUPPORTED = {
    "rolling_key",            # update key via SHA3-512 -> first 32 bytes
    "chacha20poly1305_enc",   # AEAD enc (nonce random, optional AAD)
    "chacha20poly1305_dec",
    "aesgcm_enc",             # AEAD enc (nonce random, optional AAD)
    "aesgcm_dec",
}

def load_pipeline(path):
    with open(path, "r") as f:
        y = yaml.safe_load(f)
    steps = y.get("steps") or y.get("pipeline") or y
    if not isinstance(steps, list):
        raise ValueError("Pipeline YAML must be a list under 'steps:' or 'pipeline:'")
    for s in steps:
        if s.get("op") not in SUPPORTED:
            raise ValueError(f"Unsupported op in pipeline: {s.get('op')}")
    return steps

def ensure_dir(p):
    Path(p).mkdir(parents=True, exist_ok=True)

def render_rust(steps, outdir):
    from codegen.rust_gen import generate_rust_project
    generate_rust_project(steps, outdir)

def render_go(steps, outdir):
    from codegen.go_gen import generate_go_project
    generate_go_project(steps, outdir)

def main():
    ap = argparse.ArgumentParser(description="Generate Rust/Go code from cipher DSL pipeline.")
    ap.add_argument("lang", choices=["rust","go"], help="Target language")
    ap.add_argument("-p","--pipeline", required=True, help="YAML pipeline path")
    ap.add_argument("-o","--outdir", required=True, help="Output directory for generated project")
    args = ap.parse_args()

    steps = load_pipeline(args.pipeline)
    ensure_dir(args.outdir)

    if args.lang == "rust":
        render_rust(steps, args.outdir)
        print(f"[OK] Rust project generated at {args.outdir}")
        print("Build:  cargo build --release")
        print("Usage:  target/release/cipher enc -k <seed> -i <infile> -o <outfile>")
        print("        target/release/cipher dec -k <seed> -i <infile> -o <outfile>")
    else:
        render_go(steps, args.outdir)
        print(f"[OK] Go project generated at {args.outdir}")
        print("Build:  go build -o cipher .")
        print("Usage:  ./cipher enc -k <seed> -i <infile> -o <outfile>")
        print("        ./cipher dec -k <seed> -i <infile> -o <outfile>")

if __name__ == "__main__":
    main()
