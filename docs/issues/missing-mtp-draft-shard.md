# MTP draft-model shard missing in Jetson AI Lab Thor vLLM image

The main Qwen3.8 Flash Next NVFP4 checkpoint loaded **40/40 shards** on JetPack 7.2.1, but startup failed when MTP speculative decoding attempted to load this file:

```text
FileNotFoundError: /opt/qwen38-mtp-model/model-00001-of-00034.safetensors
```

The initial command used `--speculative-config '{"method":"mtp","num_speculative_tokens":3,"model":"/opt/qwen38-mtp-model"}'`.

Disabling that flag allowed the main model to load. Please check whether this image has a stale draft-model index, missing file, or incorrect embedded checkpoint reference. A reproduction should pin the container digest and inspect the file layout inside `/opt/qwen38-mtp-model`. **Do not assume the full MTP model is correctly packaged based solely on this trace.**
