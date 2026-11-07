# 05 — Controlled optimization and release workflow

```mermaid
flowchart TD
    A[Baseline v0.2.0: validated Docker flags] --> B[Capture sanitized live Docker flags + software metadata]
    B --> C[Benchmark quick / reasoning / prefix / context]
    C --> D[Create feature branch + hypothesis + expected tradeoff]
    D --> E[Change ONE feature in a new profile / isolated service restart]
    E --> F[Same prompts, clocks, power, samples, cache policy]
    F --> G{Correctness, stability, safety gates pass?}
    G -- No --> H[Revert feature, log issue and evidence]
    G -- Yes --> I[Compare p50/p95 TTFT, output rate and agent success]
    I --> J[PR with anonymized data + CI review]
    J --> K[Merge to main + versioned tag]
```

**Don't confuse faster tokens with faster agents:** a response can decode faster and still be unusable due to broken JSON, bad tool arguments, dropped requests, context failures or long-run over-current. Record all separately. `main` remains stable, model profiles remain immutable after publication, and results stay gitignored until anonymized and reviewed.
