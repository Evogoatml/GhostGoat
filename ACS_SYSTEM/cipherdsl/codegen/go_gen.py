# codegen/go_gen.py
from pathlib import Path
import json

MAIN_GO_TEMPLATE = """\
package main

import (
    "crypto/aes"
    "crypto/cipher"
    "crypto/rand"
    "encoding/base64"
    "encoding/hex"
    "encoding/json"
    "flag"
    "fmt"
    "io"
    "os"

    "golang.org/x/crypto/chacha20poly1305"
    "golang.org/x/crypto/sha3"
)

type StepOut struct {
    Op       string  `json:"op"`
    NonceB64 *string `json:"nonce_b64,omitempty"`
    TagB64   *string `json:"tag_b64,omitempty"` // kept for schema parity
    AADB64   *string `json:"aad_b64,omitempty"`
}

type Bundle struct {
    ID      string    `json:"id"`
    Steps   []StepOut `json:"steps"`
    DataB64 string    `json:"data_b64"`
}

var pipelineJSON = `{PIPELINE_JSON}`

func parseSeed(s string) []byte {
    if len(s) > 2 && (s[0:2] == "0x" || s[0:2] == "0X") {
        b, err := hex.DecodeString(s[2:])
        if err != nil { panic(err) }
        return b
    }
    return []byte(s)
}

func rollingKey(cur []byte, counter uint64, extra []byte) [32]byte {
    h := sha3.New512()
    h.Write(cur)
    var cbuf [8]byte
    for i:=0;i<8;i++ { cbuf[7-i] = byte(counter & 0xff); counter >>= 8 }
    h.Write(cbuf[:])
    h.Write(extra)
    sum := h.Sum(nil)
    var out [32]byte
    copy(out[:], sum[:32])
    return out
}

func aesgcmEncrypt(key *[32]byte, pt, aad []byte) (ct []byte, nonce [12]byte) {
    block, err := aes.NewCipher(key[:]); if err != nil { panic(err) }
    gcm, err := cipher.NewGCM(block); if err != nil { panic(err) }
    if _, err := io.ReadFull(rand.Reader, nonce[:]); err != nil { panic(err) }
    ct = gcm.Seal(nil, nonce[:], pt, aad)
    return
}

func aesgcmDecrypt(key *[32]byte, nonce [12]byte, ct, aad []byte) []byte {
    block, err := aes.NewCipher(key[:]); if err != nil { panic(err) }
    gcm, err := cipher.NewGCM(block); if err != nil { panic(err) }
    pt, err := gcm.Open(nil, nonce[:], ct, aad); if err != nil { panic(err) }
    return pt
}

func chachaEncrypt(key *[32]byte, pt, aad []byte) (ct []byte, nonce [12]byte) {
    aead, err := chacha20poly1305.New(key[:]); if err != nil { panic(err) }
    if _, err := io.ReadFull(rand.Reader, nonce[:]); err != nil { panic(err) }
    ct = aead.Seal(nil, nonce[:], pt, aad)
    return
}

func chachaDecrypt(key *[32]byte, nonce [12]byte, ct, aad []byte) []byte {
    aead, err := chacha20poly1305.New(key[:]); if err != nil { panic(err) }
    pt, err := aead.Open(nil, nonce[:], ct, aad); if err != nil { panic(err) }
    return pt
}

func b64e(b []byte) string { return base64.StdEncoding.EncodeToString(b) }
func b64d(s string) []byte {
    b, err := base64.StdEncoding.DecodeString(s); if err != nil { panic(err) }
    return b
}

func mustRead(p string) []byte {
    b, err := os.ReadFile(p); if err != nil { panic(err) }
    return b
}
func mustWrite(p string, b []byte) {
    if err := os.WriteFile(p, b, 0644); err != nil { panic(err) }
}

func main() {
    if len(os.Args) < 2 {
        fmt.Println("usage: cipher enc|dec -k <seed> -i infile -o outfile")
        os.Exit(2)
    }
    mode := os.Args[1]
    fs := flag.NewFlagSet(mode, flag.ExitOnError)
    key := fs.String("k", "", "seed string (raw or 0x-hex)")
    inF := fs.String("i", "", "input file")
    outF := fs.String("o", "", "output file")
    if err := fs.Parse(os.Args[2:]); err != nil { panic(err) }
    if *key == "" || *inF == "" || *outF == "" {
        fmt.Println("missing -k/-i/-o")
        os.Exit(2)
    }

    var steps []map[string]any
    if err := json.Unmarshal([]byte(pipelineJSON), &steps); err != nil { panic(err) }

    seedb := parseSeed(*key)
    var k [32]byte
    if len(seedb) >= 32 { copy(k[:], seedb[:32]) } else { copy(k[:], seedb) }

    switch mode {
    case "enc":
        data := mustRead(*inF)
        counter := uint64(1)
        outSteps := make([]StepOut, 0, len(steps))

        for _, s := range steps {
            op := s["op"].(string)
            switch op {
            case "rolling_key":
                extra := make([]byte, 8)
                for i:=0;i<8;i++ { extra[7-i] = byte(counter & 0xff); counter >>= 8 }
                k = rollingKey(k[:], counter+0, extra)
                counter++
                outSteps = append(outSteps, StepOut{Op: op})

            case "chacha20poly1305_enc":
                aad := []byte("")
                if v, ok := s["aad"].(string); ok { aad = []byte(v) }
                ct, nonce := chachaEncrypt(&k, data, aad)
                data = ct
                n := b64e(nonce[:]); a := b64e(aad)
                outSteps = append(outSteps, StepOut{Op: op, NonceB64: &n, AADB64: &a})

            case "aesgcm_enc":
                aad := []byte("")
                if v, ok := s["aad"].(string); ok { aad = []byte(v) }
                ct, nonce := aesgcmEncrypt(&k, data, aad)
                data = ct
                n := b64e(nonce[:]); a := b64e(aad)
                outSteps = append(outSteps, StepOut{Op: op, NonceB64: &n, AADB64: &a})

            default:
                panic("enc unsupported op: " + op)
            }
        }

        bundle := Bundle{
            ID:    fmt.Sprintf("%016x", randUint64()),
            Steps: outSteps,
            DataB64: b64e(data),
        }
        jb, _ := json.MarshalIndent(bundle, "", "  ")
        mustWrite(*outF, jb)

    case "dec":
        jb := mustRead(*inF)
        var b Bundle
        if err := json.Unmarshal(jb, &b); err != nil { panic(err) }
        data := b64d(b.DataB64)
        counter := uint64(1)

        for _, s := range b.Steps {
            switch s.Op {
            case "rolling_key":
                extra := make([]byte, 8)
                for i:=0;i<8;i++ { extra[7-i] = byte(counter & 0xff); counter >>= 8 }
                k = rollingKey(k[:], counter+0, extra)
                counter++
            case "chacha20poly1305_enc":
                nonce := b64d(*s.NonceB64)
                var n12 [12]byte; copy(n12[:], nonce)
                var aad []byte
                if s.AADB64 != nil { aad = b64d(*s.AADB64) }
                data = chachaDecrypt(&k, n12, data, aad)
            case "aesgcm_enc":
                nonce := b64d(*s.NonceB64)
                var n12 [12]byte; copy(n12[:], nonce)
                var aad []byte
                if s.AADB64 != nil { aad = b64d(*s.AADB64) }
                data = aesgcmDecrypt(&k, n12, data, aad)
            default:
                panic("dec unsupported step: " + s.Op)
            }
        }

        mustWrite(*outF, data)

    default:
        fmt.Println("mode must be enc or dec")
        os.Exit(2)
    }
}

func randUint64() uint64 {
    var b [8]byte
    if _, err := io.ReadFull(rand.Reader, b[:]); err != nil { panic(err) }
    var v uint64
    for i:=0;i<8;i++ { v = (v<<8) | uint64(b[i]) }
    return v
}
"""

def generate_go_project(steps, outdir):
    pipeline_json = json.dumps(steps, separators=(",",":"))
    main_go = MAIN_GO_TEMPLATE.replace("{PIPELINE_JSON}", pipeline_json)
    Path(outdir).mkdir(parents=True, exist_ok=True)
    (Path(outdir) / "main.go").write_text(main_go)
    # advise: user needs x/crypto
    go_mod = "module cipher\n\ngo 1.22.0\n\nrequire golang.org/x/crypto v0.28.0\n"
    (Path(outdir) / "go.mod").write_text(go_mod)
