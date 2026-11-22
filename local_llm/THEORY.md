# Theoretical ceilings: Inkling 2 Mini UD-Q4_K_M on a 5900X + RTX 3070

Spec-sheet bandwidths for now; replace them with measured values (O3).

## Model, from the GGUF header

| Item | Value |
|---|---|
| Stored blocks | 24 (`blk.0`–`blk.23`) |
| Looped core | blocks 6–17, run 3 times (`num_loops` 3, `core_start` 6, `core_end` 18) |
| Layer passes per token | 6 + 12×3 + 6 = **48** |
| Experts | 128 per block, top-8 routed (1/16 read per pass) |
| Hidden size / expert FFN | 2304 / 1152 |
| Attention | 24 query heads, 8 KV heads, head dim 128; sliding window 1024 on 5 of every 6 layers |
| Vocabulary | 201,024 (LM head Q8_0, 0.49 GB) |

| Role | GB stored |
|---|---:|
| Routed experts (quant type 40, Unsloth-specific, plus some Q8_0/Q5_K) | 14.78 |
| Attention (Q8_0, some BF16/F32) | 0.72 |
| LM head | 0.49 |
| Token embedding (lookup only, not read per token) | 0.49 |
| Router, norms, other dense | 0.12 |

## Decode (memory-bandwidth bound)

Bytes per token:

| Part | Calculation | GB/token | Where it lives |
|---|---|---:|---|
| Experts | 14.78/24 × 1/16 × 48 passes | 1.85 | RAM (`--cpu-moe`) |
| Attention + dense | (0.72 + 0.12)/24 × 48 | 1.68 | GPU |
| LM head | | 0.49 | GPU |

Assumptions: RAM ~34 GB/s practical (2666 dual channel, 42.7 spec); GPU ~380 GB/s practical (448 spec).

- RAM part: 1.85 / 34 = 54 ms. GPU part: 2.17 / 380 = 6 ms. CPU and GPU work alternate per layer, so the
  times add: **~60 ms → ~17 tok/s** with all experts in RAM.
- At RAM 3200 (XMP, ~41 GB/s): ~51 ms → ~20 tok/s.
- **Experts on the GPU.** Each block's experts are 0.62 GB. A looped core block removes 3 of 48 passes
  from the RAM side; an outer block removes 1. Using ~2–2.5 GB of free VRAM for experts:
  - 4 core blocks (2.46 GB): RAM passes 48 → 36, about 47 ms → ~21 tok/s.
  - 4 last blocks (what `--n-cpu-moe 20` does): 48 → 44 passes → ~18 tok/s.

## Prompt reading (prefill)

With the GPU on, llama.cpp copies each layer's expert weights to the GPU per micro-batch for large
batches. The limit is then the PCIe copy, not compute:
- Experts copied per micro-batch: 48 passes × 0.62 GB ≈ 29.6 GB if looped blocks are re-copied per loop,
  14.8 GB if not. At ~25 GB/s (PCIe 4.0 x16 practical): 0.6–1.2 s per micro-batch.
- Micro-batch 512 → ~430–850 tok/s; 2048 → ~1,700–3,400 tok/s. Compute (2 × 3.4B FLOP/token at 50% of
  ~40 TFLOPS FP16 tensor) is ~2,900 tok/s, so it caps the larger micro-batches.
- First measured: 206 tok/s at prompt 512 (default micro-batch 512), about 25–50% of this ceiling.

## KV cache

Full-attention layers: 1 of every 6 stored blocks with a sliding-window pattern, so KV grows with context
on only ~8 of 48 passes; the other passes cap at 1024 tokens. At f16, 8 KV heads × 128 × 2 (K,V) × 2 bytes
= 4 KB per token per full layer. At 16K context that's tens of MB, so the KV cache isn't a constraint here.
