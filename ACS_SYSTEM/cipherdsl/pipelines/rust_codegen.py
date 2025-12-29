# rust_codegen.py
import os, json, pathlib
from dsl import load_pipeline, resolve_key_source

CARGO_TOML = """\
[package]
name = "evolvex_cipher"
version = "0.1.0"
edition = "2021"

[dependencies]
aes-gcm = "0.10"
chacha20poly1305 = "0.10"
sha3 = "0.10"
hex = "0.4"
base64 = "0.22"
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
rand = "0.8"
"""

MAIN_RS = r#"
use aes_gcm::{Aes256Gcm, aead::{Aead, KeyInit, Payload}};
use chacha20poly1305::{ChaCha20Poly1305, KeyInit as KeyInit2, aead::{Aead as Aead2}};
use sha3::{Digest, Sha3_512};
use serde::{Serialize, Deserialize};
use rand::RngCore;
use std::fs;

#[derive(Serialize, Deserialize)]
struct Bundle {
    alg: String,
    nonce: String,
    tag: String,
    ct: String,
    aad: String
}

fn b64e(bytes: &[u8]) -> String { base64::encode(bytes) }
fn b64d(s: &str) -> Vec<u8> { base64::decode(s).unwrap() }

fn rolling_key(prev: &[u8], counter: u64, extra: &[u8]) -> Vec<u8> {
    let mut hasher = Sha3_512::new();
    hasher.update(prev);
    hasher.update(&counter.to_be_bytes());
    hasher.update(extra);
    let out = hasher.finalize();
    out[..32].to_vec()
}

fn aes_gcm_encrypt(key: &[u8], pt: &[u8], aad: &[u8]) -> Bundle {
    let mut nonce = [0u8;12]; rand::thread_rng().fill_bytes(&mut nonce);
    let cipher = Aes256Gcm::new_from_slice(key).unwrap();
    let ct = cipher.encrypt(&nonce.into(), Payload { msg: pt, aad }).unwrap();
    // split tag from ct? aes-gcm crate returns combined; we’ll store whole ct as ct, and tag empty for parity
    Bundle{ alg:"AES-GCM".into(), nonce:b64e(&nonce), tag:"".into(), ct:b64e(&ct), aad:b64e(aad) }
}

fn chacha_encrypt(key: &[u8], pt: &[u8], aad: &[u8]) -> Bundle {
    let mut nonce = [0u8;12]; rand::thread_rng().fill_bytes(&mut nonce);
    let cipher = ChaCha20Poly1305::new_from_slice(key).unwrap();
    let ct = cipher.encrypt(&nonce.into(), chacha20poly1305::aead::Payload{msg:pt, aad}).unwrap();
    Bundle{ alg:"CHACHA20-POLY1305".into(), nonce:b64e(&nonce), tag:"".into(), ct:b64e(&ct), aad:b64e(aad) }
}

fn whirlpool_hex(data: &[u8]) -> String {
    // Use SHA3-512 here as a placeholder for integrity if Whirlpool crate not desired.
    // If you need true Whirlpool, use a Whirlpool crate and swap this function.
    let mut hasher = sha3::Sha3_512::new();
    hasher.update(data);
    hex::encode(hasher.finalize())
}

#[derive(Serialize, Deserialize)]
struct Envelope {
    name: String,
    meta: serde_json::Value,
    pipeline: serde_json::Value,
    layers: Vec<Bundle>,
    blob: String
}

fn main() {
    // Very small demo runner: read plaintext.bin, output cipher.json
    let key = std::env::var("EVOLVE_SEED").unwrap_or_else(|_| "default-seed".into());
    let mut key32 = [0u8;32];
    let kb = key.as_bytes();
    let copy_len = kb.len().min(32);
    key32[..copy_len].copy_from_slice(&kb[..copy_len]);
    let mut counter: u64 = 0;

    let pt = fs::read("plaintext.bin").expect("read plaintext.bin");
    let mut payload = pt.clone();
    let mut layers: Vec<Bundle> = Vec::new();
    let mut pipe = vec![];

    // rolling key
    counter += 1;
    let rk = rolling_key(&key32, counter, &0u128.to_be_bytes());
    pipe.push(serde_json::json!({"op":"rolling_key"}));

    // AES-GCM
    let b1 = aes_gcm_encrypt(&rk, &payload, b"adap");
    payload = serde_json::to_vec(&b1).unwrap();
    layers.push(b1);
    pipe.push(serde_json::json!({"op":"aes_gcm"}));

    // ChaCha20
    let b2 = chacha_encrypt(&rk, &payload, b"evolve");
    payload = serde_json::to_vec(&b2).unwrap();
    layers.push(b2);
    pipe.push(serde_json::json!({"op":"chacha20"}));

    // Whirlpool integrity (using Sha3_512 as stand-in)
    let integ = whirlpool_hex(&payload);
    pipe.push(serde_json::json!({"op":"whirlpool","digest":integ}));

    let env = Envelope{
        name:"EvolveX".into(),
        meta: serde_json::json!({"version":1}),
        pipeline: serde_json::Value::Array(pipe),
        layers,
        blob: String::from_utf8(payload.clone()).unwrap()
    };

    fs::write("cipher.json", serde_json::to_vec(&env).unwrap()).unwrap();
    println!("Wrote cipher.json");
}
"#;

def write_rust_project(outdir: str):
    os.makedirs(os.path.join(outdir, "src"), exist_ok=True)
    with open(os.path.join(outdir, "Cargo.toml"), "wt") as f:
        f.write(CARGO_TOML)
    with open(os.path.join(outdir, "src", "main.rs"), "wt") as f:
        f.write(MAIN_RS)
    print("[✓] Rust project emitted ->", outdir)

if __name__ == "__main__":
    write_rust_project("evolvex_cipher")
