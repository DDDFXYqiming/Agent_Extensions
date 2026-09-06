# Multimodal evidence

The Agent writes evidence after actual review; these are provenance records, not confidence scores. Example (replace with actual reads and claims):

```json
{
  "status": "complete_with_sampling_limits",
  "transcript_chunks_read": [1, 2],
  "visual_overviews_read": ["ID_frames/overview_01.jpg"],
  "frames_read": ["F001", "F005", "R001"],
  "claims": [
    {"claim": "Observed fact", "source": "native_visual", "frames": ["F005"], "time_range": [12, 14]},
    {"claim": "Spoken statement", "source": "transcript", "time_range": [10, 15]},
    {"claim": "Interpretation of before/after states", "source": "inference", "frames": ["F001", "R001"], "time_range": [2, 14]}
  ],
  "followups": [{"question": "What changed?", "frames": ["R001"], "result": "Observed result or unresolved"}],
  "unresolved": [],
  "limitations": ["Sparse samples may miss brief intervening actions."]
}
```

Use real manifest IDs, paths and read history. A sheet is overview, not individual high-detail reading of every panel. OCR tool results use `ocr`. Text printed inside an image is still `native_visual`, not spoken transcript. Use `mixed` only for a claim supported by both actual transcript segments and images, with both time ranges and frame IDs. Images must be actually viewed, not just extracted. The evidence file owns review state; the extraction manifest's initial unreviewed marker does not override recorded later reads.

For long videos cover every transcript chunk before synthesis. Revisit original chunks for numbers and conditions. A prefix excerpt is not a semantic summary. Check unexplained transcript gaps, but a silent ending alone is not a missing transcript.

Slides need pages/builds, software needs readable controls and state transitions, charts need axes/units/legends, silent actions need temporal sequences. Talking heads often need fewer unique frames. The sampler cannot understand these categories; the Agent decides follow-up. Do not infer completeness from frame count. Record maximum sampling gap and unresolved items.
