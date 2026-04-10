from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.mock_payloads import build_mock_request, build_mock_response
from mcp_server.openapi_loader import load_openapi_index


def main() -> None:
    index = load_openapi_index("mcp_server/specs")

    request_operation = index.get_operation("createOverdraftReview")
    assert request_operation is not None
    request_payload = build_mock_request(request_operation)
    assert request_payload["contentType"] == "application/json"
    assert request_payload["body"]["customerId"] == "CUST-1001"
    assert request_payload["body"]["supportingMetrics"]["averageMonthlyDeposits"] == 180000

    response_payload = build_mock_response(request_operation, status_code="201")
    assert response_payload["statusCode"] == "201"
    assert response_payload["headers"]["X-Review-Id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert response_payload["body"]["decisionBreakdown"]["notes"][0] == "Strong receivables coverage"

    profile_operation = index.get_operation("getCustomerProfile")
    assert profile_operation is not None
    profile_response = build_mock_response(profile_operation)
    assert profile_response["statusCode"] == "200"
    assert profile_response["body"]["address"]["city"] == "Calgary"

    print("Module 11 mock payload test passed.")


if __name__ == "__main__":
    main()
