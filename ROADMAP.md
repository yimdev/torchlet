# Torchlet Roadmap

Torchlet is intentionally narrow. The roadmap focuses on one model family and
one attention path:

- Qwen2.5-style decoder-only models.
- Grouped Query Attention (GQA).
- Greedy generation with simple stop-token handling.
- Small, comparable version-to-version changes.

It is not trying to become a general-purpose inference framework. The project
does not aim to support many model architectures, every attention variant, a
large sampler stack, or a plugin-style backend system.

## Version Themes

The future versions are planned as small learning steps. Each version should
make the next idea visible in code and keep the diff from the previous version
easy to inspect.

```text
v00_full_recompute        Qwen2.5 single request, full recompute
v01_0_ragged_batch        Ragged batch with req_indptr
v01_1_split_gqa           Split GQA forward into readable phases

v02_kv_cache              Simple GQA KV cache + prefill/decode
v03_request_states        Request states: waiting/running/finished
v04_continuous_batching   Continuous batching for Qwen2.5 decode
v05_decode_slots          Fixed decode slots
v06_static_buffers        Static decode buffers
v07_cuda_graph            CUDA Graph replay for static decode

v08_paged_gqa_py          Block pool + block table + PyTorch paged GQA
v09_triton_basics         Triton basics with a small GQA-related kernel
v10_triton_paged_gqa      Triton paged GQA attention
v11_cuda_graph_triton_paged  CUDA Graph replay for Triton paged decode
```

The order is meant to follow the inference data flow:

- `v01_1_split_gqa` is a cleanup checkpoint before KV cache.
- `v02_kv_cache` explains why generation should stop recomputing all historical K/V.
- `v03_request_states` to `v04_continuous_batching` explain how requests move through a tiny generation engine.
- `v05_decode_slots` to `v07_cuda_graph` prepare a static decode shape, then use CUDA Graph replay.
  `v06_static_buffers` only keeps decode model inputs at stable shapes and
  addresses; prefill, Python scheduling, and KV cache growth remain dynamic.
- `v08_paged_gqa_py` moves from slot-owned contiguous KV cache to a block pool,
  block table, and a clear PyTorch paged GQA implementation. It can keep Python
  loops so the logical-block to physical-block mapping stays visible.
- `v09_triton_basics` to `v10_triton_paged_gqa` move the same paged GQA idea
  from readable PyTorch code to Triton kernels.
- `v11_cuda_graph_triton_paged` captures the Triton paged decode path after the
  block-table layout and kernel launch shape are stable.

CUDA Graph appears twice for two separate lessons. `v07_cuda_graph` shows the
basic static decode capture before paged KV exists. `v11_cuda_graph_triton_paged`
returns to graph replay after paged attention has moved into a fixed Triton
decode path.

`torch.compile` is intentionally not part of the core roadmap. It can still be
an optional comparison experiment, but the main path keeps CUDA Graph and
Triton explicit so the inference data flow remains visible.

## Optional Distributed Extension

Tensor Parallelism (TP) is a reasonable extension after the single-GPU GQA path
is complete. It should not be mixed into the core roadmap, because TP introduces
distributed concepts that would distract from the main Qwen2.5 GQA inference
path: ranks, process groups, collective communication, sharded weights, and
rank-local KV cache.

If the core single-GPU roadmap is complete, TP can become a second learning
track:

```text
v12_tp_basics        Tensor parallel basics: rank/world_size/process group
v13_tp_linear        Sharded linear layers: ColumnParallelLinear and RowParallelLinear
v14_tp_ffn           Tensor-parallel Qwen2.5 SwiGLU FFN
v15_tp_gqa_proj      Tensor-parallel Qwen2.5 GQA projections
v16_tp_kv_cache      Tensor-parallel KV cache by KV heads
v17_tp_decode        Tensor-parallel full decode step
v18_tp_cuda_graph    Tensor-parallel CUDA Graph constraints
```

This extension should stay narrow:

- Only Qwen2.5-style models.
- Only GQA.
- A small fixed world size is enough for learning.
- No pipeline parallelism or data parallelism.
- No general multi-node serving runtime.

The goal is to answer one follow-up question after the single-GPU path is clear:
if the model no longer fits on one GPU, how does the same Qwen2.5 decode path
split across multiple GPUs?

## Backend Abstraction

Torchlet avoids a complex plugin-style backend abstraction. A full backend
system would usually need interfaces, registries, runtime capability checks,
fallback policies, dtype/device constraints, autotuning, graph caches, and
backend-specific metadata. Those pieces are useful in a production inference
framework, but they would obscure the main learning path here.

Instead, each version can keep the GQA implementation direct. When a later
version replaces PyTorch GQA with Triton GQA, the code should make that change
visible instead of hiding it behind a large registry or plugin layer.
