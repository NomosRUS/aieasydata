import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any
import html as html_lib

class ReportGenerator:
    """Генерирует HTML-отчеты по результатам выполнения сценариев."""

    def __init__(self, reports_path: str = "reports"):
        self.reports_path = Path(reports_path)
        self.reports_path.mkdir(parents=True, exist_ok=True)

    def generate_html_report(self, results: List[Dict[str, Any]], execution_time: float) -> str:
        """Генерирует HTML-отчет на основе списка результатов."""
        total_scenarios = len(results)
        passed_scenarios = sum(1 for r in results if r['result'].success)
        failed_scenarios = total_scenarios - passed_scenarios
        pass_rate = (passed_scenarios / total_scenarios * 100) if total_scenarios > 0 else 0

        html = f"""\
        <html>
        <head>
            <title>Test Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 40px; }}
                .summary {{ background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: .25rem; padding: 20px; margin-bottom: 20px; }}
                .scenario {{ border: 1px solid #dee2e6; border-radius: .25rem; margin-bottom: 10px; }}
                .scenario-header {{ padding: 10px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }}
                .passed {{ border-left: 5px solid #28a745; }}
                .failed {{ border-left: 5px solid #dc3545; }}
                .passed .scenario-header {{ background-color: #d4edda; }}
                .failed .scenario-header {{ background-color: #f8d7da; }}
                .trajectory {{ display: none; padding: 10px; border-top: 1px solid #dee2e6; background-color: #fff; }}
                pre {{ background-color: #e9ecef; padding: 10px; border-radius: .25rem; white-space: pre-wrap; word-wrap: break-word; }}
            </style>
            <script>
                function toggleTrajectory(element) {{
                    var content = element.nextElementSibling;
                    if (content.style.display === "block") {{
                        content.style.display = "none";
                    }} else {{
                        content.style.display = "block";
                    }}
                }}
            </script>
        </head>
        <body>
            <h1>Test Execution Report</h1>
            <div class='summary'>
                <h2>Summary</h2>
                <p>Total Scenarios: {total_scenarios}</p>
                <p>Passed: {passed_scenarios}</p>
                <p>Failed: {failed_scenarios}</p>
                <p>Pass Rate: <strong>{pass_rate:.2f}%</strong></p>
                <p>Total Execution Time: {execution_time:.2f}s</p>
            </div>
            <h2>Scenario Details</h2>
        """

        for res in results:
            scenario_name = res['scenario'].name
            status = "PASSED" if res['result'].success else "FAILED"
            status_class = "passed" if res['result'].success else "failed"
            error_message = f"<p><strong>Error:</strong> {res['result'].error}</p>" if not res['result'].success else ""
            
            trajectory_html = "<pre>" + html_lib.escape(json.dumps(res['result'].trajectory, indent=2, ensure_ascii=False)) + "</pre>"

            html += f"""\
            <div class='scenario {status_class}'>
                <div class='scenario-header' onclick='toggleTrajectory(this)'>
                    <span><strong>{scenario_name}</strong> - {status}</span>
                    <span>Click to expand</span>
                </div>
                <div class='trajectory'>
                    {error_message}
                    <h4>Execution Trajectory:</h4>
                    {trajectory_html}
                </div>
            </div>
            """

        html += "</body></html>"

        report_file = self.reports_path / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html)

        return str(report_file)
