"""Validate retained synthetic Web/Android UI traces after the UI checks."""

import json
from pathlib import Path

import httpx
from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import (
    ExportTraceServiceRequest,
)


def main():
    report = {}
    with httpx.Client(timeout=10, trust_env=False) as client:

        def logs(query):
            response = client.get(
                "http://127.0.0.1:19428/select/logsql/query", params={"query": query}
            )
            response.raise_for_status()
            return [
                json.loads(line) for line in response.text.splitlines() if line.strip()
            ]

        def spans(trace_id):
            response = client.get(
                f"http://127.0.0.1:13200/api/traces/{trace_id}",
                headers={"Accept": "application/protobuf"},
            )
            response.raise_for_status()
            payload = ExportTraceServiceRequest.FromString(response.content)
            return [
                s
                for b in payload.resource_spans
                for ss in b.scope_spans
                for s in ss.spans
            ], payload

        refreshed = logs(
            "environment:=test origin:=server code:=tokens_refreshed | limit 100"
        )
        for platform in ("web", "android"):
            errors = logs(
                f"environment:=test origin:=client platform:={platform} code:=client_http | limit 20"
            )
            assert errors, platform
            error = errors[0]
            tree, _ = spans(error["trace_id"])
            ids = {span.span_id for span in tree}
            assert len(ids) == len(tree)
            assert all(not s.parent_span_id or s.parent_span_id in ids for s in tree)
            assert any(s.name == "sqlite.read" for s in tree)
            assert any(s.kind == 2 for s in tree) and any(s.kind == 3 for s in tree)
            same_error = logs(
                f'environment:=test origin:=client trace_id:="{error["trace_id"]}" code:=client_http'
            )
            assert len(same_error) == 1
            refresh_trace = None
            for row in refreshed:
                tree, payload = spans(row["trace_id"])
                platforms = {
                    attr.value.string_value
                    for resource in payload.resource_spans
                    for attr in resource.resource.attributes
                    if attr.key == "platform"
                }
                if platform not in platforms:
                    continue
                statuses = [
                    attr.value.int_value
                    for span in tree
                    for attr in span.attributes
                    if attr.key == "status"
                ]
                if 401 not in statuses or 200 not in statuses:
                    continue
                ids = {s.span_id for s in tree}
                assert all(
                    not s.parent_span_id or s.parent_span_id in ids for s in tree
                )
                assert any(s.name == "POST /api/refresh" for s in tree)
                assert any(s.name == "sqlite.read" for s in tree)
                refresh_trace = row["trace_id"]
                break
            assert refresh_trace, f"No complete UI refresh/DB trace for {platform}"
            report[platform] = {
                "error_trace": error["trace_id"],
                "refresh_trace": refresh_trace,
                "single_error": True,
            }
    Path(
        "/private/tmp/expenis-observability-e2e/ui-correlation-result.json"
    ).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
