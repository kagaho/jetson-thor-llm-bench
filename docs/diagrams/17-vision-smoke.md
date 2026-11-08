# Vision smoke test: from selected file to API verdict

```mermaid
flowchart TD
    A[Operator explicitly selects a local image file] --> B{File exists, at most 8 MiB, supported filename MIME type?}
    B -->|No| X[Reject input before inference]
    B -->|Yes| C[Read image bytes and encode as a base64 data URI]
    C --> D[Build multimodal request with one short description instruction]
    D --> W[Run excluded warmups]
    W --> E[Run N measured nonstreaming image requests]
    E --> F{Response finishes with stop and nonempty visible content?}
    F -->|Yes| P[PASS API smoke test]
    F -->|No or request error| Q[FAIL API smoke test]
    P --> R[Save latency, available usage and verdict]
    Q --> R
    R --> S[Exclude image bytes, input path and raw answer from report]
```

Supported filename MIME types are JPEG, PNG and WebP. Local validation uses the file name/type and byte size; it does not independently decode or score the image. The configured model server processes the image payload.

The benchmark program reads the file selected with `--image`; this is not a model-selected repository tool or permission for an agent to read arbitrary host files. The simulated-agent evaluators keep their separate in-memory boundary.

PASS establishes API completion and a nonempty visible response. There are no reference labels, semantic image scores, camera-frame-rate measurements or object-detection metrics. Nonstreaming requests provide request latency and available usage, not streamed TTFT/TTFC. Default warmups are excluded, failures remain in request counts and latency summaries use successful rows.

See the [suite guide](../BENCHMARK_VISUAL_GUIDE.md#vision-api-smoke-test) and [methodology](../METHODOLOGY.md).
