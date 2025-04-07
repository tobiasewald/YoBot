# /app/analyzer.py
import json

# Load Trivy scan report
def load_trivy_report(report_path):
    try:
        with open(report_path, 'r') as file:
            data = json.load(file)
        return data
    except Exception as e:
        print(f"Error loading Trivy report: {e}")
        return {}

# Analyze the logs and extract useful details
def analyze_logs(report_data):
    if not report_data:
        return {"severity": "Unknown", "vuln_name": "No data"}

    # Flatten vulnerabilities (can come from multiple targets)
    vulnerabilities = []
    for result in report_data.get("Results", []):
        for vuln in result.get("Vulnerabilities", []):
            vulnerabilities.append(vuln)

    # Prioritize vulnerabilities by severity
    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "UNKNOWN"]
    sorted_vulns = sorted(
        vulnerabilities, 
        key=lambda v: severity_order.index(v.get("Severity", "UNKNOWN").upper())
    )

    if not sorted_vulns:
        return {"severity": "Low", "vuln_name": "No vulnerabilities found 🛡️"}

    top_vuln = sorted_vulns[0]
    return {
        "severity": top_vuln.get("Severity", "Unknown").capitalize(),
        "vuln_name": top_vuln.get("VulnerabilityID", "Unnamed vuln")
    }
