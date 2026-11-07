# Security and publication policy

- This project sends prompts to an **existing** OpenAI-compatible endpoint; it never starts or exposes a server unless you explicitly execute `scripts/serve_qwen.sh`.
- By default, target `http://127.0.0.1:8000` **on the Jetson itself**. Avoid binding vLLM to a public network interface. vLLM API keys alone may not protect all inference endpoints.
- Results stay in `results/` and are gitignored. Prompts, image data, answer contents, credentials, IP addresses, usernames, and device serial numbers are not written to reports.
- Do not commit Hugging Face tokens, `.env` files, full container logs, screenshots with private details, or model weights.
- Inspect `git status`, `git diff --cached`, and `git log -p` before pushing any public repository.
- Use an SSH tunnel for remote access or a properly authenticated reverse proxy; do not put vLLM directly on the internet.
- The MIT license covers **this benchmark code only**, not the Qwen checkpoint, Docker images, or upstream software.
