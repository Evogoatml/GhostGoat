#!/usr/bin/env python3
"""
Automated Code Security Auditor
Performs static analysis, dependency scanning, and security checks
"""

import os
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CodeAuditor:
    """Main code auditing orchestrator"""
    
    def __init__(self, code_path: str, report_path: str):
        self.code_path = Path(code_path)
        self.report_path = Path(report_path)
        self.report_path.mkdir(parents=True, exist_ok=True)
        self.findings = {
            'timestamp': datetime.now().isoformat(),
            'code_path': str(code_path),
            'vulnerabilities': [],
            'code_quality': [],
            'secrets': [],
            'dependencies': [],
            'summary': {}
        }
    
    def run_bandit(self) -> Dict[str, Any]:
        """Run Bandit for Python security issues"""
        logger.info("Running Bandit security scanner...")
        try:
            result = subprocess.run(
                ['bandit', '-r', str(self.code_path), '-f', 'json'],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.stdout:
                bandit_results = json.loads(result.stdout)
                self.findings['vulnerabilities'].extend(
                    self._parse_bandit_results(bandit_results)
                )
                logger.info(f"Bandit found {len(bandit_results.get('results', []))} issues")
                return bandit_results
        except Exception as e:
            logger.error(f"Bandit scan failed: {e}")
            return {}
    
    def run_semgrep(self) -> Dict[str, Any]:
        """Run Semgrep for multi-language security patterns"""
        logger.info("Running Semgrep security scanner...")
        try:
            result = subprocess.run(
                [
                    'semgrep',
                    '--config=auto',
                    '--json',
                    str(self.code_path)
                ],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.stdout:
                semgrep_results = json.loads(result.stdout)
                self.findings['vulnerabilities'].extend(
                    self._parse_semgrep_results(semgrep_results)
                )
                logger.info(f"Semgrep found {len(semgrep_results.get('results', []))} issues")
                return semgrep_results
        except Exception as e:
            logger.error(f"Semgrep scan failed: {e}")
            return {}
    
    def run_safety(self) -> Dict[str, Any]:
        """Check Python dependencies for known vulnerabilities"""
        logger.info("Running Safety dependency checker...")
        try:
            result = subprocess.run(
                ['safety', 'check', '--json', '--file', 
                 str(self.code_path / 'requirements.txt')],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.stdout:
                safety_results = json.loads(result.stdout)
                self.findings['dependencies'].extend(
                    self._parse_safety_results(safety_results)
                )
                logger.info(f"Safety found {len(safety_results)} vulnerable dependencies")
                return safety_results
        except Exception as e:
            logger.error(f"Safety check failed: {e}")
            return {}
    
    def run_gitleaks(self) -> Dict[str, Any]:
        """Scan for secrets and credentials"""
        logger.info("Running Gitleaks secret scanner...")
        try:
            result = subprocess.run(
                [
                    'gitleaks',
                    'detect',
                    '--source', str(self.code_path),
                    '--report-format', 'json',
                    '--no-git'
                ],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if result.stdout:
                gitleaks_results = json.loads(result.stdout)
                self.findings['secrets'].extend(
                    self._parse_gitleaks_results(gitleaks_results)
                )
                logger.info(f"Gitleaks found {len(gitleaks_results)} potential secrets")
                return gitleaks_results
        except Exception as e:
            logger.error(f"Gitleaks scan failed: {e}")
            return {}
    
    def run_trivy(self) -> Dict[str, Any]:
        """Scan for vulnerabilities in containers and dependencies"""
        logger.info("Running Trivy vulnerability scanner...")
        try:
            result = subprocess.run(
                [
                    'trivy',
                    'fs',
                    '--format', 'json',
                    '--severity', 'CRITICAL,HIGH,MEDIUM',
                    str(self.code_path)
                ],
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.stdout:
                trivy_results = json.loads(result.stdout)
                self.findings['dependencies'].extend(
                    self._parse_trivy_results(trivy_results)
                )
                logger.info("Trivy scan completed")
                return trivy_results
        except Exception as e:
            logger.error(f"Trivy scan failed: {e}")
            return {}
    
    def check_security_headers(self) -> List[Dict[str, Any]]:
        """Check for security best practices in web configurations"""
        logger.info("Checking security configurations...")
        issues = []
        
        # Check for common config files
        nginx_configs = list(self.code_path.rglob("nginx.conf"))
        apache_configs = list(self.code_path.rglob("*.htaccess"))
        
        for config in nginx_configs + apache_configs:
            try:
                content = config.read_text()
                
                # Check for security headers
                required_headers = [
                    'X-Frame-Options',
                    'X-Content-Type-Options',
                    'Strict-Transport-Security',
                    'Content-Security-Policy'
                ]
                
                for header in required_headers:
                    if header not in content:
                        issues.append({
                            'type': 'missing_security_header',
                            'severity': 'MEDIUM',
                            'file': str(config),
                            'header': header,
                            'description': f'Missing security header: {header}'
                        })
            except Exception as e:
                logger.error(f"Error checking config {config}: {e}")
        
        self.findings['code_quality'].extend(issues)
        return issues
    
    def _parse_bandit_results(self, results: Dict) -> List[Dict]:
        """Parse Bandit output into standardized format"""
        parsed = []
        for issue in results.get('results', []):
            parsed.append({
                'tool': 'bandit',
                'severity': issue.get('issue_severity', 'UNKNOWN'),
                'confidence': issue.get('issue_confidence', 'UNKNOWN'),
                'title': issue.get('issue_text', ''),
                'file': issue.get('filename', ''),
                'line': issue.get('line_number', 0),
                'code': issue.get('code', ''),
                'cwe': issue.get('issue_cwe', {}).get('id', 'N/A')
            })
        return parsed
    
    def _parse_semgrep_results(self, results: Dict) -> List[Dict]:
        """Parse Semgrep output into standardized format"""
        parsed = []
        for result in results.get('results', []):
            parsed.append({
                'tool': 'semgrep',
                'severity': result.get('extra', {}).get('severity', 'UNKNOWN'),
                'title': result.get('check_id', ''),
                'file': result.get('path', ''),
                'line': result.get('start', {}).get('line', 0),
                'message': result.get('extra', {}).get('message', ''),
                'cwe': result.get('extra', {}).get('metadata', {}).get('cwe', 'N/A')
            })
        return parsed
    
    def _parse_safety_results(self, results: List) -> List[Dict]:
        """Parse Safety output into standardized format"""
        parsed = []
        for vuln in results:
            parsed.append({
                'tool': 'safety',
                'severity': 'HIGH',
                'package': vuln[0],
                'installed_version': vuln[1],
                'vulnerability': vuln[2],
                'affected_versions': vuln[3],
                'description': vuln[4]
            })
        return parsed
    
    def _parse_gitleaks_results(self, results: List) -> List[Dict]:
        """Parse Gitleaks output into standardized format"""
        parsed = []
        for secret in results:
            parsed.append({
                'tool': 'gitleaks',
                'severity': 'CRITICAL',
                'type': secret.get('Description', ''),
                'file': secret.get('File', ''),
                'line': secret.get('StartLine', 0),
                'match': secret.get('Match', '')[:50] + '...'  # Truncate for safety
            })
        return parsed
    
    def _parse_trivy_results(self, results: Dict) -> List[Dict]:
        """Parse Trivy output into standardized format"""
        parsed = []
        for target in results.get('Results', []):
            for vuln in target.get('Vulnerabilities', []):
                parsed.append({
                    'tool': 'trivy',
                    'severity': vuln.get('Severity', 'UNKNOWN'),
                    'package': vuln.get('PkgName', ''),
                    'installed_version': vuln.get('InstalledVersion', ''),
                    'fixed_version': vuln.get('FixedVersion', ''),
                    'vulnerability_id': vuln.get('VulnerabilityID', ''),
                    'title': vuln.get('Title', ''),
                    'description': vuln.get('Description', '')
                })
        return parsed
    
    def generate_summary(self):
        """Generate summary statistics"""
        self.findings['summary'] = {
            'total_vulnerabilities': len(self.findings['vulnerabilities']),
            'critical': sum(1 for v in self.findings['vulnerabilities'] 
                          if v.get('severity') == 'CRITICAL'),
            'high': sum(1 for v in self.findings['vulnerabilities'] 
                       if v.get('severity') == 'HIGH'),
            'medium': sum(1 for v in self.findings['vulnerabilities'] 
                         if v.get('severity') == 'MEDIUM'),
            'low': sum(1 for v in self.findings['vulnerabilities'] 
                      if v.get('severity') == 'LOW'),
            'secrets_found': len(self.findings['secrets']),
            'vulnerable_dependencies': len(self.findings['dependencies']),
            'code_quality_issues': len(self.findings['code_quality'])
        }
    
    def save_report(self):
        """Save findings to JSON report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.report_path / f"security_audit_{timestamp}.json"
        
        with open(report_file, 'w') as f:
            json.dump(self.findings, f, indent=2)
        
        logger.info(f"Report saved to {report_file}")
        return report_file
    
    def send_notification(self, webhook_url: str = None):
        """Send notification to Slack or other webhook"""
        if not webhook_url:
            webhook_url = os.getenv('SLACK_WEBHOOK_URL')
        
        if not webhook_url:
            logger.warning("No webhook URL configured for notifications")
            return
        
        summary = self.findings['summary']
        
        message = {
            "text": "Security Audit Report",
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔒 Security Audit Completed"
                    }
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Critical:* {summary['critical']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*High:* {summary['high']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Secrets Found:* {summary['secrets_found']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Vulnerable Deps:* {summary['vulnerable_dependencies']}"
                        }
                    ]
                }
            ]
        }
        
        try:
            response = requests.post(webhook_url, json=message, timeout=10)
            if response.status_code == 200:
                logger.info("Notification sent successfully")
            else:
                logger.error(f"Failed to send notification: {response.status_code}")
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    def run_full_audit(self):
        """Execute complete security audit"""
        logger.info(f"Starting full security audit of {self.code_path}")
        
        # Run all scanners
        self.run_bandit()
        self.run_semgrep()
        self.run_safety()
        self.run_gitleaks()
        self.run_trivy()
        self.check_security_headers()
        
        # Generate summary and save report
        self.generate_summary()
        report_file = self.save_report()
        
        # Send notifications
        self.send_notification()
        
        logger.info("Security audit completed")
        logger.info(f"Summary: {json.dumps(self.findings['summary'], indent=2)}")
        
        return report_file


def main():
    """Main entry point"""
    code_path = os.getenv('CODE_PATH', '/code_to_audit')
    report_path = os.getenv('REPORT_PATH', '/reports')
    
    auditor = CodeAuditor(code_path, report_path)
    auditor.run_full_audit()


if __name__ == '__main__':
    main()
