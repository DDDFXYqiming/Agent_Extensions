"""Behavioral checks with synthetic media; no network or model calls."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import video_to_notes as video
import visual_sampling as visual


class MaterialsTest(unittest.TestCase):
    def test_transcript_tail_is_preserved(self):
        segments = [{"start": i, "end": i+1, "text": f"segment-{i}:" + "x"*100} for i in range(100)]
        segments[-1]["text"] = "IMPORTANT FINAL QUALIFICATION"
        output = video.TranscribeOutput(segments=segments)
        text = video.build_chunk_summaries_markdown(output, "test")
        for seg in segments:
            self.assertIn(seg["text"], text)
        self.assertEqual(sum(len(c["segments"]) for c in video.chunk_transcript_segments(segments)), 100)

    def test_sampling_budget_interval_and_silent_changes(self):
        scores = [{"timestamp": 43, "change_score": .7}, {"timestamp": 87, "change_score": .5}]
        frames = visual.choose_candidates(120, 30, 12, scores, [])
        self.assertIn(43, [f["timestamp"] for f in frames])
        self.assertIn(87, [f["timestamp"] for f in frames])
        self.assertLess(frames[0]["timestamp"], 1)
        self.assertGreater(frames[-1]["timestamp"], 119)
        self.assertLessEqual(len(frames), 12)
        self.assertGreater(len(visual.choose_candidates(120, 10, 24, [], [])),
                           len(visual.choose_candidates(120, 60, 24, [], [])))

    def test_explicit_budget_not_clamped_by_environment(self):
        with patch.object(video, "MAX_AGENT_FRAMES", 3):
            self.assertGreater(len(visual.choose_candidates(120, 10, 16, [], [])), 3)

    def test_change_dedup_keeps_coverage(self):
        scores = [{"timestamp": t, "change_score": .7, "signature": [30]*10} for t in [43, 47, 51]]
        frames = visual.choose_candidates(120, 30, 12, scores, [])
        self.assertEqual(sum(f["selection_reason"] == "regional_change" for f in frames), 1)
        self.assertEqual(sum(f["selection_reason"] == "coverage" for f in frames), 5)

    def test_media_cache_and_supplement(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"test.mp4"
            subprocess.run([video.FFMPEG, "-v", "error", "-y", "-f", "lavfi", "-i",
                            "testsrc2=size=640x360:rate=10:duration=6", "-c:v", "libx264", str(source)], check=True)
            data = visual.prepare_visuals(video.FFMPEG, source, Path(folder)/"frames", [], 2, 8, 480)
            self.assertGreater(len(data["frames"]), 3)
            self.assertGreater(data["sampling"]["candidate_scan_count"], 0)
            with patch.object(visual, "scan_changes", side_effect=AssertionError("cache missed")):
                self.assertEqual(data, visual.prepare_visuals(video.FFMPEG, source, Path(folder)/"frames", [], 2, 8, 480))
            manifest = Path(folder)/"manifest.json"
            manifest.write_text(json.dumps(data), encoding="utf-8")
            frames = visual.supplement(video.FFMPEG, manifest, [1.2], crop=[10,10,300,200])
            self.assertTrue(Path(frames[0]["image_path"]).is_file())
            self.assertEqual(len(visual.supplement(video.FFMPEG, manifest, [1.2], crop=[10,10,300,200])), 1)
            with self.assertRaises(ValueError):
                visual.supplement(video.FFMPEG, manifest, [9])

    def test_draft_does_not_claim_summary(self):
        draft = video.build_notes_markdown(video.TranscribeOutput(transcript_text="a claim"), "test")
        self.assertNotIn("a claim", draft)
        self.assertIn("awaiting_agent_review", draft)

    def test_retry_retains_review_ids_and_flags_changed_sampling(self):
        old = {"source_identity": {"size": 123}, "cache_key": {"budget": 24},
               "supplemental_frames": [{"id": "R001", "timestamp": 15}]}
        new = {"source_identity": {"size": 123}, "cache_key": {"budget": 12}, "sampling": {"warnings": []}}
        merged = visual.preserve_review_history(new, old)
        self.assertEqual(merged["supplemental_frames"][0]["id"], "R001")
        self.assertTrue(merged["sampling"]["warnings"])

    def test_visual_failure_preserves_transcript_and_existing_final(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder)/"fixture.mp4"
            source.touch()
            final = Path(folder)/"fixture_final_notes.md"
            final.write_text("Agent final must survive material retries", encoding="utf-8")
            with patch.object(video, "check_deps", return_value=[]), \
                 patch.object(video, "get_video_info", return_value=video.VideoInfo(title="fixture", duration=10)), \
                 patch.object(video, "download_audio", return_value=video.AudioMeta(file_path=str(source))), \
                 patch.object(video, "transcribe_via_faster_whisper", return_value=[video.TranscriptSegment(0,10,"retained tail")]), \
                 patch.object(video, "download_video_for_frames", return_value=str(source)), \
                 patch.object(video, "prepare_visuals", side_effect=RuntimeError("decoder failure")), \
                 patch.dict(os.environ, {"WHISPER_CPP": ""}), \
                 patch.object(video, "TRANSCRIBER_TYPE", "faster-whisper"):
                result = video.generate_transcript(str(source), folder, extract_frames=True)
            self.assertIn("retained tail", Path(result.transcript_chunks_file).read_text(encoding="utf-8"))
            self.assertEqual(Path(result.final_notes_file), final)
            self.assertEqual(final.read_text(encoding="utf-8"), "Agent final must survive material retries")
            self.assertEqual(result.visual_warnings, ["decoder failure"])
            self.assertEqual(json.loads(Path(result.output_file).read_text(encoding="utf-8"))["audio_file"], str(source))


if __name__ == "__main__":
    unittest.main()
