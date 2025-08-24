#!/usr/bin/env python3
"""
Security Scanner Service - Semgrep Integration
Scans codebase for security vulnerabilities using Semgrep
"""

import os
import json
import time
import redis
import subprocess
import schedule
import logging
from datetime import datetime
from typing import Dict, List, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Redis connection
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', 6379))
rdb = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Configuration
SCAN_PATHS = ['/srv/auto-adsense']
SEMGREP_CONFIG = 'auto'  # Use Semgrep's curated ruleset
SCAN_INTERVAL_HOURS = 6

class SecurityScanner:
    def __init__(self):
        self.scan_results = []
        self.last_scan_time = None
        
    def run_semgrep_scan(self, scan_path: str) -> Dict[str, Any]:
        """Run Semgrep security scan on specified path"""
        try:
            logger.info(f"Starting Semgrep scan on: {scan_path}")
            
            # Build semgrep command
            cmd = [
                'semgrep', 
                '--config', SEMGREP_CONFIG,
                '--json',
                '--severity=WARNING',
                '--severity=ERROR',
                scan_path
            ]
            
            # Run semgrep
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0 or result.returncode == 1:  # 1 means findings found
                output = json.loads(result.stdout) if result.stdout else {"results": []}
                logger.info(f"Semgrep scan completed. Found {len(output.get('results', []))} issues")
                return {
                    'status': 'success',
                    'findings': output.get('results', []),
                    'scan_path': scan_path,
                    'timestamp': datetime.now().isoformat()
                }
            else:
                logger.error(f"Semgrep scan failed: {result.stderr}")
                return {
                    'status': 'error',
                    'error': result.stderr,
                    'scan_path': scan_path,
                    'timestamp': datetime.now().isoformat()
                }
                
        except subprocess.TimeoutExpired:
            logger.error("Semgrep scan timed out")
            return {
                'status': 'timeout',
                'error': 'Scan timeout after 5 minutes',
                'scan_path': scan_path,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Semgrep scan error: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'scan_path': scan_path,
                'timestamp': datetime.now().isoformat()
            }
    
    def categorize_findings(self, findings: List[Dict]) -> Dict[str, List]:
        """Categorize security findings by severity and type"""
        categories = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': [],
            'by_category': {}
        }
        
        for finding in findings:
            # Determine severity
            severity = finding.get('extra', {}).get('severity', 'INFO').lower()
            if severity in ['error', 'critical']:
                categories['critical'].append(finding)
            elif severity == 'warning':
                categories['high'].append(finding)
            else:
                categories['low'].append(finding)
            
            # Categorize by type
            category = finding.get('extra', {}).get('metadata', {}).get('category', 'other')
            if category not in categories['by_category']:
                categories['by_category'][category] = []
            categories['by_category'][category].append(finding)
        
        return categories
    
    def generate_security_report(self, scan_results: List[Dict]) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        all_findings = []
        scan_summary = {
            'total_scans': len(scan_results),
            'successful_scans': 0,
            'failed_scans': 0,
            'total_findings': 0
        }
        
        for result in scan_results:
            if result['status'] == 'success':
                scan_summary['successful_scans'] += 1
                findings = result.get('findings', [])
                all_findings.extend(findings)
                scan_summary['total_findings'] += len(findings)
            else:
                scan_summary['failed_scans'] += 1
        
        categorized = self.categorize_findings(all_findings)
        
        report = {
            'scan_summary': scan_summary,
            'timestamp': datetime.now().isoformat(),
            'findings_by_severity': {
                'critical': len(categorized['critical']),
                'high': len(categorized['high']),
                'medium': len(categorized['medium']),
                'low': len(categorized['low'])
            },
            'findings_by_category': {
                category: len(findings) 
                for category, findings in categorized['by_category'].items()
            },
            'detailed_findings': categorized,
            'recommendations': self.generate_recommendations(categorized)
        }
        
        return report
    
    def generate_recommendations(self, categorized_findings: Dict) -> List[str]:
        """Generate security recommendations based on findings"""
        recommendations = []
        
        if categorized_findings['critical']:
            recommendations.append("🚨 Critical security issues found - immediate action required!")
        
        if categorized_findings['high']:
            recommendations.append("⚠️ High-priority security issues need attention")
        
        # Category-based recommendations
        categories = categorized_findings['by_category']
        
        if 'security' in categories:
            recommendations.append("Review security-related code for vulnerabilities")
        
        if 'owasp' in categories:
            recommendations.append("Address OWASP security issues")
        
        if 'secrets' in categories:
            recommendations.append("🔑 Secrets or API keys detected - remove from code")
        
        if 'sql-injection' in categories:
            recommendations.append("SQL injection vulnerabilities found - use parameterized queries")
        
        if not recommendations:
            recommendations.append("✅ No major security issues found - continue monitoring")
        
        return recommendations
    
    def save_scan_results(self, report: Dict[str, Any]):
        """Save scan results to Redis"""
        try:
            # Save full report
            rdb.set('security:latest_scan', json.dumps(report))
            
            # Save scan history
            scan_id = f"security:scan:{int(time.time())}"
            rdb.set(scan_id, json.dumps(report))
            rdb.expire(scan_id, 86400 * 30)  # Keep for 30 days
            
            # Update scan metrics
            rdb.hset('security:metrics', mapping={
                'last_scan_time': report['timestamp'],
                'total_findings': report['scan_summary']['total_findings'],
                'critical_count': report['findings_by_severity']['critical'],
                'high_count': report['findings_by_severity']['high'],
                'scan_status': 'completed'
            })
            
            # Create alerts for critical findings
            if report['findings_by_severity']['critical'] > 0:
                alert = {
                    'id': f"security_alert_{int(time.time())}",
                    'type': 'security',
                    'severity': 'critical',
                    'title': 'Critical Security Issues Found',
                    'message': f"{report['findings_by_severity']['critical']} critical security issues detected",
                    'timestamp': datetime.now().isoformat(),
                    'acknowledged': False
                }
                rdb.set(f"alert:{alert['id']}", json.dumps(alert))
            
            logger.info("Security scan results saved to Redis")
            
        except Exception as e:
            logger.error(f"Failed to save scan results: {str(e)}")
    
    def run_full_security_scan(self):
        """Run complete security scan on all configured paths"""
        logger.info("Starting full security scan...")
        self.last_scan_time = datetime.now()
        
        # Update status
        rdb.hset('security:metrics', 'scan_status', 'running')
        
        scan_results = []
        for path in SCAN_PATHS:
            if os.path.exists(path):
                result = self.run_semgrep_scan(path)
                scan_results.append(result)
            else:
                logger.warning(f"Scan path does not exist: {path}")
        
        # Generate report
        report = self.generate_security_report(scan_results)
        
        # Save results
        self.save_scan_results(report)
        
        logger.info(f"Security scan completed. Found {report['scan_summary']['total_findings']} total issues")
        
        return report

def main():
    """Main service function"""
    logger.info("Security Scanner service starting...")
    
    scanner = SecurityScanner()
    
    # Schedule regular scans
    schedule.every(SCAN_INTERVAL_HOURS).hours.do(scanner.run_full_security_scan)
    
    # Run initial scan
    scanner.run_full_security_scan()
    
    # Service loop
    while True:
        try:
            # Check for manual scan triggers
            trigger = rdb.get("security:trigger_scan")
            if trigger == "requested":
                logger.info("Manual security scan triggered")
                rdb.delete("security:trigger_scan")
                scanner.run_full_security_scan()
            
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
        except KeyboardInterrupt:
            logger.info("Security scanner shutting down...")
            break
        except Exception as e:
            logger.error(f"Service error: {str(e)}")
            time.sleep(60)

if __name__ == "__main__":
    main()