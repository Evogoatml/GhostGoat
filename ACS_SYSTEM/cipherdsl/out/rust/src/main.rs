use std::fs;
use clap::{Parser, Subcommand};
use anyhow::Result;
use serde::{Serialize, Deserialize};

use rand::RngCore;
use base64::{engine::general_purpose, Engine as _};

use sha3::{Digest, Sha3_512};
use aes_gcm::{Aes256Gcm, aead::{Aead, KeyInit, OsRng, generic_array::GenericArray}};
use chacha20poly1305::{ChaCha20Poly1305, Key, XChaCha20Poly1305}; // (XChaCha unused, kept for future)
use chacha20poly1305::aead::{Aead as CAead, KeyInit as CKeyInit};

#[derive(Parser)]
#[command(name="cipher", version)]
struct Cli {
    #[command(subcommand)]
    cmd: Cmd
}

#[derive(Subcommand)]
enum Cmd {
    /// encrypt
    Enc {
        /// seed string (raw or hex: prefix with 0x)
        #[arg(short='k', long="key")]
        seed: String,
        /// input file
        #[arg(short='i', long="in")]
        infile: String,
        /// output file
        #[arg(short='o', long="out")]
        outfile: String,
    },
    /// decrypt
    Dec {
        #[arg(short='k', long="key")]
        seed: String,
        #[arg(short='i', long="in")]
        infile: String,
        #[arg(short='o', long="out")]
        outfile: String,
    }
}

#[derive(Serialize, Deserialize)]
struct Bundle {
    /// Random bundle identifier
    id: String,
    /// Steps executed (serialized)
    steps: Vec<StepOut>,
    /// Final ciphertext (base64) or plaintext for dec
    data_b64: String,
}

#[derive(Serialize, Deserialize)]
struct StepOut {
    op: String,
    #[serde(skip_serializing_if="Option::is_none")]
    nonce_b64: Option<String>,
    #[serde(skip_serializing_if="Option::is_none")]
    tag_b64: Option<String>,
    #[serde(skip_serializing_if="Option::is_none")]
    aad_b64: Option<String>,
}

fn parse_seed(seed: &str) -> Vec<u8> {
    if seed.starts_with("0x") || seed.starts_with("0X") {
        hex::decode(seed.trim_start_matches("0x").trim_start_matches("0X")).expect("bad hex seed")
    } else {
        seed.as_bytes().to_vec()
    }
}

fn rolling_key(cur: &[u8], counter: u64, extra: &[u8]) -> [u8; 32] {
    let mut h = Sha3_512::new();
    h.update(cur);
    h.update(counter.to_be_bytes());
    h.update(extra);
    let out = h.finalize();
    let mut key = [0u8; 32];
    key.copy_from_slice(&out[..32]);
    key
}

fn aesgcm_encrypt(k: &[u8;32], pt: &[u8], aad: &[u8]) -> (Vec<u8>, [u8;12], [u8;16]) {
    let key = GenericArray::from_slice(k);
    let cipher = Aes256Gcm::new(key);
    let mut nonce = [0u8;12];
    rand::rngs::OsRng.fill_bytes(&mut nonce);
    let nonce_ga = GenericArray::from_slice(&nonce);
    let ct = cipher.encrypt(nonce_ga, aes_gcm::aead::Payload { msg: pt, aad }).expect("AES-GCM enc");
    // AES-GCM in this crate appends tag at end; but we want separate tag -> split
    // For aes-gcm crate, tag is not returned separately. We'll serialize alongside ciphertext by not splitting.
    // Workaround: we’ll just use the whole ct as-is and rely on decrypt to verify, tag is internal.
    // To expose tag separately we'd need aes-gcm's streaming interface; we'll keep ct only.
    // To remain symmetric, we'll not output tag here.
    let tag = [0u8;16]; // placeholder not used; kept for schema parity
    (ct, nonce, tag)
}

fn aesgcm_decrypt(k: &[u8;32], nonce:&[u8;12], ct:&[u8], aad:&[u8]) -> Vec<u8> {
    let key = GenericArray::from_slice(k);
    let cipher = Aes256Gcm::new(key);
    let nonce_ga = GenericArray::from_slice(nonce);
    cipher.decrypt(nonce_ga, aes_gcm::aead::Payload { msg: ct, aad }).expect("AES-GCM dec")
}

fn chacha_encrypt(k:&[u8;32], pt:&[u8], aad:&[u8]) -> (Vec<u8>, [u8;12], [u8;16]) {
    let key = Key::from_slice(k);
    let cipher = ChaCha20Poly1305::new(key);
    let mut nonce = [0u8;12];
    rand::rngs::OsRng.fill_bytes(&mut nonce);
    let ct = cipher.encrypt(&nonce.into(), chacha20poly1305::aead::Payload { msg: pt, aad })
        .expect("chacha enc");
    // chacha20poly1305 crate also keeps tag internally; same symmetry as above.
    let tag = [0u8;16];
    (ct, nonce, tag)
}

fn chacha_decrypt(k:&[u8;32], nonce:&[u8;12], ct:&[u8], aad:&[u8]) -> Vec<u8> {
    let key = Key::from_slice(k);
    let cipher = ChaCha20Poly1305::new(key);
    cipher.decrypt(&nonce.clone().into(), chacha20poly1305::aead::Payload { msg: ct, aad })
        .expect("chacha dec")
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    // pipeline baked in at generation time:
    // {[{"op":"rolling_key","extra":"time_ns"},{"op":"aesgcm_enc","aad":"adap"},{"op":"chacha20poly1305_enc","aad":"evolve"}]}

    let steps: Vec<serde_json::Value> = serde_json::from_str(PIPELINE_JSON)?;
    match cli.cmd {
        Cmd::Enc { seed, infile, outfile } => {
            let seedb = parse_seed(&seed);
            let mut key = {
                let mut k = [0u8;32];
                if seedb.len() >= 32 { k.copy_from_slice(&seedb[..32]); }
                else {
                    k[..seedb.len()].copy_from_slice(&seedb);
                    for i in seedb.len()..32 { k[i] = 0; }
                }
                k
            };
            let mut data = fs::read(infile)?;
            let mut counter: u64 = 1;

            let mut out_steps: Vec<StepOut> = Vec::new();

            for s in steps.iter() {
                let op = s.get("op").unwrap().as_str().unwrap();
                match op {
                    "rolling_key" => {
                        let extra = counter.to_be_bytes();
                        key = rolling_key(&key, counter, &extra);
                        counter += 1;
                        out_steps.push(StepOut { op: op.to_string(), nonce_b64: None, tag_b64: None, aad_b64: None });
                    }
                    "chacha20poly1305_enc" => {
                        let aad = s.get("aad").and_then(|v| v.as_str()).unwrap_or("").as_bytes().to_vec();
                        let (ct, nonce, _tag) = chacha_encrypt(&key, &data, &aad);
                        data = ct;
                        out_steps.push(StepOut {
                            op: op.to_string(),
                            nonce_b64: Some(general_purpose::STANDARD.encode(nonce)),
                            tag_b64: None,
                            aad_b64: Some(general_purpose::STANDARD.encode(aad)),
                        });
                    }
                    "aesgcm_enc" => {
                        let aad = s.get("aad").and_then(|v| v.as_str()).unwrap_or("").as_bytes().to_vec();
                        let (ct, nonce, _tag) = aesgcm_encrypt(&key, &data, &aad);
                        data = ct;
                        out_steps.push(StepOut {
                            op: op.to_string(),
                            nonce_b64: Some(general_purpose::STANDARD.encode(nonce)),
                            tag_b64: None,
                            aad_b64: Some(general_purpose::STANDARD.encode(aad)),
                        });
                    }
                    _ => {
                        panic!("enc: unsupported op {}", op);
                    }
                }
            }

            let bundle = Bundle {
                id: format!("{:016x}", rand::random::<u64>()),
                steps: out_steps,
                data_b64: general_purpose::STANDARD.encode(&data),
            };
            fs::write(outfile, serde_json::to_vec_pretty(&bundle)?)?;
        }
        Cmd::Dec { seed, infile, outfile } => {
            let seedb = parse_seed(&seed);
            let mut key = {
                let mut k = [0u8;32];
                if seedb.len() >= 32 { k.copy_from_slice(&seedb[..32]); }
                else {
                    k[..seedb.len()].copy_from_slice(&seedb);
                    for i in seedb.len()..32 { k[i] = 0; }
                }
                k
            };
            let mut counter: u64 = 1;

            let bundle_bytes = fs::read(infile)?;
            let bundle: Bundle = serde_json::from_slice(&bundle_bytes)?;
            let mut data = general_purpose::STANDARD.decode(bundle.data_b64)?;

            // Replay steps in the same order, but invert enc->dec
            for (i, s) in bundle.steps.iter().enumerate() {
                match s.op.as_str() {
                    "rolling_key" => {
                        let extra = counter.to_be_bytes();
                        key = rolling_key(&key, counter, &extra);
                        counter += 1;
                    }
                    "chacha20poly1305_enc" => {
                        let nonce = general_purpose::STANDARD.decode(s.nonce_b64.as_ref().unwrap()).unwrap();
                        let mut n12 = [0u8;12]; n12.copy_from_slice(&nonce);
                        let aad = s.aad_b64.as_ref().map(|x| general_purpose::STANDARD.decode(x).unwrap()).unwrap_or_default();
                        data = chacha_decrypt(&key, &n12, &data, &aad);
                    }
                    "aesgcm_enc" => {
                        let nonce = general_purpose::STANDARD.decode(s.nonce_b64.as_ref().unwrap()).unwrap();
                        let mut n12 = [0u8;12]; n12.copy_from_slice(&nonce);
                        let aad = s.aad_b64.as_ref().map(|x| general_purpose::STANDARD.decode(x).unwrap()).unwrap_or_default();
                        data = aesgcm_decrypt(&key, &n12, &data, &aad);
                    }
                    other => panic!("dec: unsupported step {}", other),
                }
            }

            fs::write(outfile, data)?;
        }
    }

    Ok(())
}

// The generator injects the pipeline steps here as JSON:
const PIPELINE_JSON: &str = r#"[{"op":"rolling_key","extra":"time_ns"},{"op":"aesgcm_enc","aad":"adap"},{"op":"chacha20poly1305_enc","aad":"evolve"}]"#;
