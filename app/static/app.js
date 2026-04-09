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

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

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

function renderTranscript(payload) {
  plainOutput.textContent = payload.text || "No transcript text returned.";

  const timestampLines = (payload.segments || []).map((segment) => {
    const start = Number(segment.start || 0).toFixed(2);
    const end = Number(segment.end || 0).toFixed(2);
    return `[${start}s -> ${end}s] ${segment.text}`;
  });
  timestampOutput.textContent = timestampLines.join("\n") || "No segments returned.";

  downloadTxt.href = `/api/transcripts/${payload.transcript_id}/download/txt`;
  downloadSrt.href = `/api/transcripts/${payload.transcript_id}/download/srt`;
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
  status.textContent = "Uploading file and creating transcription job...";

  try {
    const response = await fetch("/api/transcribe/jobs", {
      method: "POST",
      body: formData,
    });

    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Transcription failed.");
    }

    const jobId = payload.job_id;
    if (!jobId) {
      throw new Error("Transcription job id was not returned.");
    }

    status.textContent = "Job started. Waiting for transcription progress...";

    while (true) {
      const statusResponse = await fetch(`/api/transcribe/jobs/${jobId}/status`);
      const statusPayload = await statusResponse.json();

      if (!statusResponse.ok) {
        throw new Error(statusPayload.detail || "Failed to fetch job status.");
      }

      setProgress(statusPayload.state, statusPayload.progress);
      status.textContent = statusPayload.message || "Transcribing...";

      if (statusPayload.state === "completed") {
        break;
      }

      if (statusPayload.state === "failed") {
        throw new Error(statusPayload.error || statusPayload.message || "Transcription failed.");
      }

      await delay(1200);
    }

    const resultResponse = await fetch(`/api/transcribe/jobs/${jobId}/result`);
    const resultPayload = await resultResponse.json();

    if (!resultResponse.ok) {
      throw new Error(resultPayload.detail || "Unable to load transcription result.");
    }

    renderTranscript(resultPayload);
    setProgress("completed", 100);
    status.textContent = `Done. Detected language: ${resultPayload.language || "unknown"}.`;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Unexpected error.";
    showProgress(false);
    status.textContent = `Error: ${message}`;
  } finally {
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
