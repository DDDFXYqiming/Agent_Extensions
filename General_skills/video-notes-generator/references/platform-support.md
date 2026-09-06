# Platform and transcription support

The current script detects Bilibili, YouTube, Douyin, Kuaishou and local media. Site support depends on yt-dlp. It does not include the old BiliNote custom subtitle fetchers, Groq, bcut, MLX or podcast integrations.

Bilibili/YouTube try yt-dlp subtitles before local transcription. Bilibili HTTP 412 falls back to public metadata/playurl DASH downloads. Public responses may offer lower resolution than authenticated playback; preserve the downloaded source and disclose unreadable details. Other sites use the configured local transcription backend.

`TRANSCRIBER_TYPE=faster-whisper` (default) requires that package in the selected Python runtime. It tries CUDA where available, otherwise CPU/int8; errors fall back to CPU. `WHISPER_DEVICE` and `WHISPER_COMPUTE_TYPE` override selection. `WHISPER_MODEL=base` is the default; choose a larger installed model when ASR quality needs it, not merely because the summarizer changed.

`TRANSCRIBER_TYPE=whisper.cpp` uses the `WHISPER_CPP` binary (or the script's existing build path). GPU support depends on that build: Vulkan for compatible AMD/Intel hardware, Metal for Apple, or CPU. Do not assume a CUDA runtime works with another GPU vendor. The script searches existing CUDA libraries on Windows; a missing library is a fallback condition, not permission to alter other services.

The extraction pipeline uses Python's standard library and ffmpeg/ffprobe plus yt-dlp. Pillow is optional for contact sheets. Dependencies are installed by the operator, never by the extraction script. No OpenAI SDK or external vision engine is required for native Agent image review.

Long-video timestamped text chunks are complete, but the faster-whisper backend currently transcribes the full audio in one invocation. If RAM is insufficient, use the bounded audio workflow in bilibili-windows-ssl-and-long-audio.md; do not claim automatic audio splitting is implemented.
