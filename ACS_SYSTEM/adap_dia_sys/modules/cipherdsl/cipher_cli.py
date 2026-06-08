# cipher_cli.py
#!/usr/bin/env python3
import argparse, sys, json
from dsl import load_pipeline, resolve_key_source
from engine import encrypt_pipeline, decrypt_pipeline, Context

def main():
    ap = argparse.ArgumentParser(description="AI Cipher DSL CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    aenc = sub.add_parser("enc")
    aenc.add_argument("-p","--pipeline", required=True, help="YAML file")
    aenc.add_argument("-i","--infile", required=True)
    aenc.add_argument("-o","--outfile", required=True)

    adec = sub.add_parser("dec")
    adec.add_argument("-k","--key-source", required=True, help="env:VAR|hex:...|random:N")
    adec.add_argument("-i","--infile", required=True)
    adec.add_argument("-o","--outfile", required=True)

    args = ap.parse_args()

    if args.cmd == "enc":
        cfg = load_pipeline(args.pipeline)
        key = resolve_key_source(cfg.get("key_source","random:32"))
        ctx = Context(key)
        with open(args.infile,"rb") as f: pt = f.read()
        env = encrypt_pipeline(cfg["name"], cfg.get("meta",{}), ctx, cfg["steps"], pt)
        with open(args.outfile,"wt") as f: json.dump(env, f, separators=(",",":"))
        print("[✓] Encrypted ->", args.outfile)
    elif args.cmd == "dec":
        key = resolve_key_source(args.key_source)
        ctx = Context(key)
        with open(args.infile,"rt") as f: env = json.load(f)
        pt = decrypt_pipeline(ctx, env)
        with open(args.outfile,"wb") as f: f.write(pt)
        print("[✓] Decrypted ->", args.outfile)

if __name__ == "__main__":
    main()
