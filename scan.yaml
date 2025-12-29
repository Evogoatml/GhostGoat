use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::io::{self, Write};

#[derive(Debug, Clone)]
struct Vulnerability {
    severity: Severity,
    file: String,
    line: usize,
    code: String,
    description: String,
    recommendation: String,
}

#[derive(Debug, Clone, PartialEq)]
enum Severity {
    Critical,
    High,
    Medium,
    Low,
}

impl Severity {
    fn color(&self) -> &str {
        match self {
            Severity::Critical => "\x1b[91m",
            Severity::High => "\x1b[31m",
            Severity::Medium => "\x1b[33m",
            Severity::Low => "\x1b[93m",
        }
    }
    
    fn as_str(&self) -> &str {
        match self {
            Severity::Critical => "CRITICAL",
            Severity::High => "HIGH",
            Severity::Medium => "MEDIUM",
            Severity::Low => "LOW",
        }
    }
}

struct Scanner {
    patterns: Vec<Pattern>,
}

struct Pattern {
    name: String,
    regex: String,
    severity: Severity,
    description: String,
    recommendation: String,
}

impl Scanner {
    fn new() -> Self {
        let patterns = vec![
            Pattern {
                name: "SQL Injection".to_string(),
                regex: r#"(?i)(execute|query|prepare)\s*\(\s*['"](.*?\$.*?|.*?\+.*?)['"]\s*\)"#.to_string(),
                severity: Severity::Critical,
                description: "Potential SQL injection vulnerability detected".to_string(),
                recommendation: "Use parameterized queries or prepared statements".to_string(),
            },
            Pattern {
                name: "XSS Vulnerability".to_string(),
                regex: r#"(?i)(innerHTML|outerHTML|document\.write)\s*=\s*.*?(\$|user|input|req\.)"#.to_string(),
                severity: Severity::High,
                description: "Potential Cross-Site Scripting (XSS) vulnerability".to_string(),
                recommendation: "Sanitize user input and use textContent or secure templating".to_string(),
            },
            Pattern {
                name: "Hard-coded Credentials".to_string(),
                regex: r#"(?i)(password|passwd|pwd|secret|api_key|apikey|token)\s*=\s*['"]\w+"#.to_string(),
                severity: Severity::Critical,
                description: "Hard-coded credentials found in source code".to_string(),
                recommendation: "Use environment variables or secure credential management".to_string(),
            },
            Pattern {
                name: "Command Injection".to_string(),
                regex: r#"(?i)(exec|system|shell_exec|popen|eval)\s*\(.*?(\$|user|input|req\.)"#.to_string(),
                severity: Severity::Critical,
                description: "Potential command injection vulnerability".to_string(),
                recommendation: "Avoid executing user input, validate and sanitize all inputs".to_string(),
            },
            Pattern {
                name: "Path Traversal".to_string(),
                regex: r#"(?i)(fopen|file_get_contents|readfile|include|require).*?\.\."#.to_string(),
                severity: Severity::High,
                description: "Potential path traversal vulnerability".to_string(),
                recommendation: "Validate file paths and use whitelisting for allowed paths".to_string(),
            },
            Pattern {
                name: "Insecure Deserialization".to_string(),
                regex: r#"(?i)(unserialize|pickle\.loads|yaml\.load)\s*\("#.to_string(),
                severity: Severity::High,
                description: "Insecure deserialization detected".to_string(),
                recommendation: "Use safe deserialization methods and validate input data".to_string(),
            },
            Pattern {
                name: "Weak Cryptography".to_string(),
                regex: r#"(?i)(md5|sha1|des|rc4)\s*\("#.to_string(),
                severity: Severity::Medium,
                description: "Weak cryptographic algorithm detected".to_string(),
                recommendation: "Use SHA-256, SHA-3, or modern encryption like AES-256".to_string(),
            },
            Pattern {
                name: "Debug Mode Enabled".to_string(),
                regex: r#"(?i)(debug\s*=\s*true|app\.debug\s*=\s*true|console\.log)"#.to_string(),
                severity: Severity::Low,
                description: "Debug mode or logging detected".to_string(),
                recommendation: "Disable debug mode in production environments".to_string(),
            },
        ];
        
        Scanner { patterns }
    }
    
    fn scan_file(&self, path: &Path) -> io::Result<Vec<Vulnerability>> {
        let content = fs::read_to_string(path)?;
        let mut vulnerabilities = Vec::new();
        
        for (line_num, line) in content.lines().enumerate() {
            for pattern in &self.patterns {
                let re = regex::Regex::new(&pattern.regex).unwrap();
                if re.is_match(line) {
                    vulnerabilities.push(Vulnerability {
                        severity: pattern.severity.clone(),
                        file: path.display().to_string(),
                        line: line_num + 1,
                        code: line.trim().to_string(),
                        description: pattern.description.clone(),
                        recommendation: pattern.recommendation.clone(),
                    });
                }
            }
        }
        
        Ok(vulnerabilities)
    }
    
    fn scan_directory(&self, dir: &Path) -> io::Result<Vec<Vulnerability>> {
        let mut all_vulns = Vec::new();
        
        if dir.is_file() {
            return self.scan_file(dir);
        }
        
        for entry in walkdir::WalkDir::new(dir)
            .follow_links(false)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();
            if path.is_file() {
                if let Some(ext) = path.extension() {
                    let ext_str = ext.to_string_lossy();
                    if matches!(ext_str.as_ref(), "rs" | "py" | "js" | "php" | "java" | "go" | "rb" | "c" | "cpp" | "ts" | "jsx" | "tsx") {
                        if let Ok(vulns) = self.scan_file(path) {
                            all_vulns.extend(vulns);
                        }
                    }
                }
            }
        }
        
        Ok(all_vulns)
    }
}

struct Reporter;

impl Reporter {
    fn generate_report(vulnerabilities: &[Vulnerability]) {
        let reset = "\x1b[0m";
        let bold = "\x1b[1m";
        
        println!("\n{}╔═══════════════════════════════════════════════════════════════════╗{}", bold, reset);
        println!("{}║                   GhostGoat Security Scan Report                  ║{}", bold, reset);
        println!("{}╚═══════════════════════════════════════════════════════════════════╝{}\n", bold, reset);
        
        if vulnerabilities.is_empty() {
            println!("{}✓ No vulnerabilities detected!{}\n", "\x1b[32m", reset);
            return;
        }
        
        let mut severity_count: HashMap<String, usize> = HashMap::new();
        for vuln in vulnerabilities {
            *severity_count.entry(vuln.severity.as_str().to_string()).or_insert(0) += 1;
        }
        
        println!("{}Summary:{}", bold, reset);
        println!("  Total Issues: {}", vulnerabilities.len());
        for (severity, count) in &severity_count {
            let color = match severity.as_str() {
                "CRITICAL" => Severity::Critical.color(),
                "HIGH" => Severity::High.color(),
                "MEDIUM" => Severity::Medium.color(),
                _ => Severity::Low.color(),
            };
            println!("  {}{}: {}{}", color, severity, count, reset);
        }
        println!();
        
        let mut sorted_vulns = vulnerabilities.to_vec();
        sorted_vulns.sort_by(|a, b| {
            let order_a = match a.severity {
                Severity::Critical => 0,
                Severity::High => 1,
                Severity::Medium => 2,
                Severity::Low => 3,
            };
            let order_b = match b.severity {
                Severity::Critical => 0,
                Severity::High => 1,
                Severity::Medium => 2,
                Severity::Low => 3,
            };
            order_a.cmp(&order_b)
        });
        
        for (idx, vuln) in sorted_vulns.iter().enumerate() {
            let color = vuln.severity.color();
            println!("{}[{}] {}{}  {}", bold, idx + 1, color, vuln.severity.as_str(), reset);
            println!("{}File:{} {}", bold, reset, vuln.file);
            println!("{}Line:{} {}", bold, reset, vuln.line);
            println!("{}Description:{} {}", bold, reset, vuln.description);
            println!("{}Code:{} {}", bold, reset, vuln.code);
            println!("{}Recommendation:{} {}", bold, reset, vuln.recommendation);
            println!("{}", "─".repeat(70));
        }
    }
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    
    if args.len() < 2 {
        eprintln!("Usage: ghostgoat <directory_or_file>");
        eprintln!("\nExample: ghostgoat ./src");
        std::process::exit(1);
    }
    
    let target = Path::new(&args[1]);
    
    if !target.exists() {
        eprintln!("Error: Path '{}' does not exist", target.display());
        std::process::exit(1);
    }
    
    println!("\nGhostGoat Security Scanner");
    println!("Scanning: {}\n", target.display());
    
    let scanner = Scanner::new();
    
    match scanner.scan_directory(target) {
        Ok(vulnerabilities) => {
            Reporter::generate_report(&vulnerabilities);
        }
        Err(e) => {
            eprintln!("Error during scan: {}", e);
            std::process::exit(1);
        }
    }
}
