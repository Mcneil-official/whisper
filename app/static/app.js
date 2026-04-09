const form = document.getElementById("upload-form");
const input = document.getElementById("audio-file");
const chooseFileButton = document.getElementById("choose-file-btn");
const submitButton = document.getElementById("submit-btn");
const fileChip = document.getElementById("file-chip");
const fileChipName = document.getElementById("file-chip-name");
const removeFileButton = document.getElementById("remove-file-btn");
const status = document.getElementById("status");
const progressWrap = document.getElementById("progress-wrap");
const progressStage = document.getElementById("progress-stage");
const progressPercent = document.getElementById("progress-percent");
const progressBar = document.getElementById("progress-bar");
const plainOutput = document.getElementById("plain-output");
const timestampOutput = document.getElementById("timestamp-output");
const downloads = document.getElementById("downloads");
const downloadTxt = document.getElementById("download-txt");
const downloadSrt = document.getElementById("download-srt");
let activeFile = null;
let estimatedProgressTimer = null;
let downloadObjectUrls = [];

function titleCase(text) {
  return text
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function showProgress(show) {
  progressWrap.classList.toggle("hidden", !show);
}

function setProgress(state, progress) {
  const safeProgress = Number.isFinite(progress) ? Math.max(0, Math.min(100, Math.round(progress))) : 0;
  progressStage.textContent = titleCase(state || "queued");
  progressPercent.textContent = `${safeProgress}%`;
  progressBar.style.width = `${safeProgress}%`;
}

function startEstimatedProgress() {
  stopEstimatedProgress();
  let progress = 12;
  setProgress("transcribing", progress);
  estimatedProgressTimer = window.setInterval(() => {
    progress = Math.min(progress + Math.max(2, Math.round(Math.random() * 8)), 92);
    setProgress("transcribing", progress);
  }, 420);
}

function stopEstimatedProgress() {
  if (estimatedProgressTimer) {
    window.clearInterval(estimatedProgressTimer);
    estimatedProgressTimer = null;
  }
}

function revokeDownloadUrls() {
  for (const objectUrl of downloadObjectUrls) {
    URL.revokeObjectURL(objectUrl);
  }
  downloadObjectUrls = [];
}

function fileBaseName(name) {
  return name.replace(/\.[^.]+$/, "");
}

function buildTimestampedText(segments) {
  return segments
    .map((segment) => {
      const start = Number(segment.start || 0).toFixed(2);
      const end = Number(segment.end || 0).toFixed(2);
      return `[${start}s -> ${end}s] ${segment.text}`;
    })
    .join("\n");
}

function formatSrtTimestamp(seconds) {
  const totalMilliseconds = Math.max(0, Math.round(Number(seconds || 0) * 1000));
  const hours = Math.floor(totalMilliseconds / 3_600_000);
  const remainingAfterHours = totalMilliseconds % 3_600_000;
  const minutes = Math.floor(remainingAfterHours / 60_000);
  const remainingAfterMinutes = remainingAfterHours % 60_000;
  const secs = Math.floor(remainingAfterMinutes / 1000);
  const milliseconds = remainingAfterMinutes % 1000;
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(secs).padStart(2, "0")},${String(milliseconds).padStart(3, "0")}`;
}

function buildSrt(segments) {
  return segments
    .map((segment, index) => {
      const start = formatSrtTimestamp(segment.start);
      const end = formatSrtTimestamp(segment.end);
      return `${index + 1}\n${start} --> ${end}\n${segment.text.trim()}\n`;
    })
    .join("\n");
}

function renderTranscript(payload) {
  plainOutput.textContent = payload.text || "No transcript text returned.";

  const segments = payload.segments || [];
  timestampOutput.textContent = buildTimestampedText(segments) || "No segments returned.";

  revokeDownloadUrls();
  const transcriptText = payload.text || "";
  const srtText = buildSrt(segments);

  const txtBlob = new Blob([transcriptText], { type: "text/plain;charset=utf-8" });
  const srtBlob = new Blob([srtText], { type: "application/x-subrip;charset=utf-8" });

  const txtUrl = URL.createObjectURL(txtBlob);
  const srtUrl = URL.createObjectURL(srtBlob);
  downloadObjectUrls.push(txtUrl, srtUrl);

  downloadTxt.href = txtUrl;
  downloadSrt.href = srtUrl;
  downloadTxt.download = `${fileBaseName(activeFile?.name || "transcript")}.txt`;
  downloadSrt.download = `${fileBaseName(activeFile?.name || "transcript")}.srt`;
  downloads.classList.remove("hidden");
}

function resetResults() {
  plainOutput.textContent = "Your transcript will appear here.";
  timestampOutput.textContent = "Timestamped lines will appear here.";
  downloads.classList.add("hidden");
  downloadTxt.removeAttribute("href");
  downloadSrt.removeAttribute("href");
}

function updateFileSelectionState() {
  const hasFile = Boolean(activeFile);
  chooseFileButton.classList.toggle("hidden", hasFile);
  fileChip.classList.toggle("hidden", !hasFile);
  fileChipName.textContent = activeFile ? activeFile.name : "";
}

function clearSelectedFile() {
  activeFile = null;
  input.value = "";
  updateFileSelectionState();
  status.textContent = "Ready for upload.";
  showProgress(false);
  setProgress("queued", 0);
  stopEstimatedProgress();
  setLoading(false);
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  chooseFileButton.style.pointerEvents = isLoading ? "none" : "auto";
  removeFileButton.disabled = isLoading;
  submitButton.textContent = isLoading ? "Transcribing..." : "Transcribe";
}

async function transcribeSelectedFile() {
  if (!activeFile) {
    return;
  }

  const formData = new FormData();
  formData.append("file", activeFile);

  setLoading(true);
  resetResults();
  showProgress(true);
  setProgress("queued", 0);
  status.textContent = "Uploading file and transcribing...";
  startEstimatedProgress();

  try {
    const response = await fetch("/api/transcribe", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Transcription failed.");
    }
    stopEstimatedProgress();
    setProgress("completed", 100);
    renderTranscript(payload);
    setProgress("completed", 100);
    status.textContent = `Done. Detected language: ${payload.language || "unknown"}.`;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unexpected error.";
    stopEstimatedProgress();
    showProgress(false);
    status.textContent = `Error: ${message}`;
  } finally {
    stopEstimatedProgress();
    setLoading(false);
  }
}

input.addEventListener("change", () => {
  const selectedFile = input.files?.[0] || null;
  activeFile = selectedFile;
  updateFileSelectionState();

  if (!selectedFile) {
    resetResults();
    status.textContent = "Ready for upload.";
    return;
  }

  resetResults();
  status.textContent = `Selected ${selectedFile.name}. Click Transcribe to start.`;
});

removeFileButton.addEventListener("click", () => {
  clearSelectedFile();
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!activeFile) {
    status.textContent = "Please choose a file first.";
    return;
  }
  await transcribeSelectedFile();
});
