from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mcp_server.openapi_loader import load_openapi_index


SPEC_TEXT = """
openapi: 3.0.3
info:
  title: Loader Test API
  version: 1.0.0
paths:
  /accounts/{accountId}:
    get:
      operationId: getAccount
      parameters:
        - $ref: '#/components/parameters/AccountId'
      responses:
        '200':
          description: ok
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Account'
  /loan-offers:
    post:
      summary: Create a loan offer
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                amount:
                  type: number
      responses:
        '201':
          description: created
components:
  parameters:
    AccountId:
      name: accountId
      in: path
      required: true
      schema:
        type: string
        example: ACC-001
  schemas:
    Account:
      type: object
      properties:
        accountId:
          type: string
        status:
          type: string
          enum: [active, closed]
"""


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        spec_path = Path(tmp_dir) / "loader_test.yaml"
        spec_path.write_text(SPEC_TEXT, encoding="utf-8")

        index = load_openapi_index(tmp_dir)

        assert index.spec_count == 1
        assert index.operation_count == 2

        get_account = index.get_operation("getAccount")
        assert get_account is not None
        assert get_account["parameters"][0]["name"] == "accountId"
        assert get_account["responses"]["200"]["content"]["application/json"]["schema"]["properties"]["status"]["enum"][0] == "active"

        search_results = index.search_operations(query="loan offer")
        assert search_results, "Expected search results for loan offer"
        assert search_results[0]["operationId"] == "post_loan_offers"

    print("Module 11 loader smoke test passed.")


if __name__ == "__main__":
    main()
