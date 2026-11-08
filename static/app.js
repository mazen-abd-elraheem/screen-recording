// Automated Resume Screening - Client App Logic with Interactive Voice AI

let currentTab = 'text';
let uploadedFiles = [];
let presetsData = [];
let currentRankedResults = [];

// Voice Recording State
let isRecording = false;
let audioContext = null;
let mediaStream = null;
let scriptProcessor = null;
let recordedBuffers = [];
let recordingStartTime = null;
let recordingTimerInterval = null;
let speechRecognitionInstance = null;
let liveSpeechTranscript = '';

document.addEventListener('DOMContentLoaded', async () => {
  // Fetch presets
  try {
    const res = await fetch('/api/presets');
    if (res.ok) {
      presetsData = await res.json();
      loadPreset('data-engineer');
    }
  } catch (e) {
    console.error('Failed to load presets:', e);
    addCandidateRow('Candidate 1', '');
    addCandidateRow('Candidate 2', '');
  }

  setupDropzone();
  setupAudioPlayerEvents();
  setupTutorialPlayerEvents();
  fetchOllamaModels();
});

function switchCandidateTab(tab) {
  currentTab = tab;
  document.getElementById('tabTextBtn').classList.toggle('active', tab === 'text');
  document.getElementById('tabUploadBtn').classList.toggle('active', tab === 'upload');
  document.getElementById('tabTextContent').classList.toggle('active', tab === 'text');
  document.getElementById('tabUploadContent').classList.toggle('active', tab === 'upload');
}

function addCandidateRow(name = '', text = '') {
  const container = document.getElementById('candidatesList');
  const index = container.children.length + 1;
  const row = document.createElement('div');
  row.className = 'candidate-row';
  row.innerHTML = `
    <div class="candidate-row-header">
      <input type="text" class="candidate-name-input" placeholder="Candidate Name (e.g. Sarah)" value="${escapeHtml(name || `Candidate ${index}`)}">
      <div style="display:flex; align-items:center; gap:6px;">
        <button type="button" class="btn-dictate-mini" onclick="dictateCandidateRow(this)" title="Dictate Resume Text">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path><path d="M19 10v2a7 7 0 0 1-14 0v-2"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
          <span>Dictate</span>
        </button>
        <button type="button" class="btn-remove-row" title="Remove Candidate" onclick="this.closest('.candidate-row').remove()">
          <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>
      </div>
    </div>
    <textarea class="candidate-text-area" rows="3" placeholder="Paste resume text or skills profile...">${escapeHtml(text)}</textarea>
  `;
  container.appendChild(row);
}

function clearAll() {
  document.getElementById('jobDescription').value = '';
  document.getElementById('candidatesList').innerHTML = '';
  uploadedFiles = [];
  renderFilesList();
  addCandidateRow('Candidate 1', '');
  addCandidateRow('Candidate 2', '');
  document.getElementById('resultsContainer').style.display = 'none';
  document.getElementById('emptyState').style.display = 'block';
  currentRankedResults = [];
}

function loadPreset(presetId) {
  const preset = presetsData.find(p => p.id === presetId);
  if (!preset) return;

  document.getElementById('jobDescription').value = preset.job_desc;
  const container = document.getElementById('candidatesList');
  container.innerHTML = '';

  preset.candidates.forEach(c => {
    addCandidateRow(c.name, c.text);
  });

  switchCandidateTab('text');
}

// ============================================================================
// File Dropzone Logic (.pdf, .docx, .txt)
// ============================================================================
function setupDropzone() {
  const dropzone = document.getElementById('dropzone');
  if (!dropzone) return;

  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer.files;
    handleFiles(files);
  });
}

function handleFileSelect(e) {
  handleFiles(e.target.files);
}

function handleFiles(files) {
  for (let i = 0; i < files.length; i++) {
    const file = files[i];
    if (!uploadedFiles.some(f => f.name === file.name)) {
      uploadedFiles.push(file);
    }
  }
  renderFilesList();
}

function renderFilesList() {
  const container = document.getElementById('selectedFilesList');
  if (!container) return;

  if (uploadedFiles.length === 0) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = uploadedFiles.map((file, idx) => `
    <div class="file-item">
      <div class="file-name-wrap">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line></svg>
        <span class="file-name">${escapeHtml(file.name)} (${(file.size / 1024).toFixed(1)} KB)</span>
      </div>
      <button type="button" class="btn-remove-row" onclick="removeFile(${idx})" title="Remove file">
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
      </button>
    </div>
  `).join('');
}

function removeFile(index) {
  uploadedFiles.splice(index, 1);
  renderFilesList();
}

// ============================================================================
// Screening Execution
// ============================================================================
async function runScreening() {
  const jobDesc = document.getElementById('jobDescription').value.trim();
  if (!jobDesc) {
    alert('Please enter a Job Description.');
    return;
  }

  const loading = document.getElementById('loadingState');
  const empty = document.getElementById('emptyState');
  const container = document.getElementById('resultsContainer');

  loading.style.display = 'block';
  empty.style.display = 'none';
  container.style.display = 'none';

  try {
    let response;

    if (currentTab === 'upload' && uploadedFiles.length > 0) {
      const formData = new FormData();
      formData.append('job_description', jobDesc);
      uploadedFiles.forEach(file => {
        formData.append('files[]', file);
      });
      response = await fetch('/api/screen', {
        method: 'POST',
        body: formData
      });
    } else {
      const candidateRows = document.querySelectorAll('.candidate-row');
      const candidates = [];
      candidateRows.forEach(row => {
        const nameInput = row.querySelector('.candidate-name-input');
        const textInput = row.querySelector('.candidate-text-area');
        const name = nameInput ? nameInput.value.trim() : '';
        const text = textInput ? textInput.value.trim() : '';
        if (name && text) {
          candidates.push({ name, text });
        }
      });

      if (candidates.length === 0) {
        alert('Please enter at least one candidate with a name and resume text.');
        loading.style.display = 'none';
        empty.style.display = 'block';
        return;
      }

      response = await fetch('/api/screen', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_description: jobDesc,
          candidates: candidates
        })
      });
    }

    const data = await response.json();
    loading.style.display = 'none';

    if (!response.ok) {
      alert(data.error || 'Failed to screen resumes.');
      empty.style.display = 'block';
      return;
    }

    displayResults(data);

  } catch (err) {
    loading.style.display = 'none';
    empty.style.display = 'block';
    alert('Network error: ' + err.message);
  }
}

function displayResults(data) {
  const empty = document.getElementById('emptyState');
  const container = document.getElementById('resultsContainer');
  const rankList = document.getElementById('rankList');

  empty.style.display = 'none';
  container.style.display = 'block';

  currentRankedResults = data.ranked || [];

  // Winner banner
  const top = currentRankedResults[0];
  if (top) {
    document.getElementById('winnerName').textContent = top.name;
    document.getElementById('winnerScore').textContent = `${top.score_percent} Match Score`;
  }

  // Render cards
  rankList.innerHTML = currentRankedResults.map((c, i) => {
    const isFirst = i === 0;
    const progressWidth = Math.min(100, Math.max(5, c.score * 100));

    const matchedChips = (c.matched_keywords && c.matched_keywords.length)
      ? c.matched_keywords.map(k => `<span class="chip matched"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"></polyline></svg>${escapeHtml(k)}</span>`).join('')
      : '<span class="chip chip-empty">None detected</span>';

    const missingChips = (c.missing_keywords && c.missing_keywords.length)
      ? c.missing_keywords.map(k => `<span class="chip missing"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>${escapeHtml(k)}</span>`).join('')
      : '<span class="chip chip-empty">None missing</span>';

    const negatedChips = (c.negated_keywords && c.negated_keywords.length)
      ? c.negated_keywords.map(k => `<span class="chip negated"><svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>Negated: ${escapeHtml(k)}</span>`).join('')
      : '';

    return `
      <div class="rank-card ${isFirst ? 'rank-1' : ''}">
        <div class="rank-card-header">
          <div class="rank-badge-wrap">
            <span class="rank-position">#${c.rank}</span>
            <span class="rank-name">${escapeHtml(c.name)}</span>
          </div>
          <span class="tier-badge ${c.tier}">${c.badge}</span>
        </div>

        <div class="score-progress-wrap">
          <div class="score-header">
            <span>Overall Recruitment Match Score</span>
            <span class="score-percentage">${c.score_percent}</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${progressWidth}%"></div>
          </div>
          <div class="sub-scores-row">
            <span class="sub-score-item">
              <span class="sub-score-label">Skills Match (80%):</span>
              <strong class="sub-score-val">${c.skill_match_percent || c.score_percent}</strong>
              <span class="sub-score-detail">(${c.skills_ratio || ''})</span>
            </span>
            <span class="sub-score-item">
              <span class="sub-score-label">Context Relevance (20%):</span>
              <strong class="sub-score-val">${c.context_match_percent || c.score_percent}</strong>
            </span>
          </div>
        </div>

        <div class="keywords-section">
          ${c.negated_keywords && c.negated_keywords.length ? `
          <div class="chip-row">
            <span class="chip-label" style="color: #dc2626;">Penalized:</span>
            ${negatedChips}
          </div>` : ''}
          <div class="chip-row">
            <span class="chip-label">Matched:</span>
            ${matchedChips}
          </div>
          <div class="chip-row">
            <span class="chip-label">Missing:</span>
            ${missingChips}
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ============================================================================
// Interactive Voice Recording & Voice AI Pipeline
// ============================================================================

async function toggleVoiceRecording() {
  if (!isRecording) {
    await startVoiceRecording();
  } else {
    await stopVoiceRecordingAndSend();
  }
}

async function startVoiceRecording() {
  try {
    // Request microphone access
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    // Setup Web Audio API for PCM WAV capture
    audioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const sourceNode = audioContext.createMediaStreamSource(mediaStream);
    
    // ScriptProcessor for raw Float32 mono samples
    scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
    recordedBuffers = [];

    scriptProcessor.onaudioprocess = (e) => {
      if (!isRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      recordedBuffers.push(new Float32Array(inputData));
    };

    sourceNode.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);

    // Optional: Start Web Speech API transcription in parallel for instant client feedback
    liveSpeechTranscript = '';
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        speechRecognitionInstance = new SpeechRec();
        const selectedLang = document.getElementById('voiceLangSelect').value;
        speechRecognitionInstance.lang = selectedLang === 'ar' ? 'ar-EG' : (selectedLang === 'en' ? 'en-US' : 'en-US');
        speechRecognitionInstance.continuous = true;
        speechRecognitionInstance.interimResults = true;
        speechRecognitionInstance.onresult = (evt) => {
          let text = '';
          for (let i = 0; i < evt.results.length; ++i) {
            text += evt.results[i][0].transcript;
          }
          liveSpeechTranscript = text;
          if (text) {
            document.getElementById('recordingStatusText').textContent = `Hearing: "${text}"`;
          }
        };
        speechRecognitionInstance.start();
      } catch (err) {
        console.warn('SpeechRecognition initialization note:', err);
      }
    }

    // UI Updates
    isRecording = true;
    recordingStartTime = Date.now();
    
    const recordBtn = document.getElementById('btnVoiceRecord');
    recordBtn.classList.add('recording');
    document.getElementById('voiceMicIcon').innerHTML = `
      <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
        <rect x="6" y="6" width="12" height="12" rx="2"></rect>
      </svg>
    `;
    document.getElementById('voiceRecordText').textContent = 'Stop & Send Recording';
    document.getElementById('voiceTimer').style.display = 'inline-block';
    document.getElementById('recordingVisualizer').style.display = 'flex';
    document.getElementById('recordingStatusText').textContent = 'Recording your voice... Speak now!';

    // Timer interval
    clearInterval(recordingTimerInterval);
    recordingTimerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const secs = String(elapsed % 60).padStart(2, '0');
      document.getElementById('voiceTimer').textContent = `${mins}:${secs}`;
    }, 500);

  } catch (err) {
    console.error('Microphone access failed:', err);
    alert('Microphone access denied or unavailable: ' + err.message + '\nYou can also upload an audio file using the "Upload Audio File" button.');
  }
}

async function stopVoiceRecordingAndSend() {
  if (!isRecording) return;
  isRecording = false;

  // Clear timer
  clearInterval(recordingTimerInterval);

  // Stop Web Speech if active
  if (speechRecognitionInstance) {
    try { speechRecognitionInstance.stop(); } catch (e) {}
  }

  // Disconnect Audio Nodes
  if (scriptProcessor) scriptProcessor.disconnect();
  if (mediaStream) {
    mediaStream.getTracks().forEach(track => track.stop());
  }

  // Reset Record Button UI
  const recordBtn = document.getElementById('btnVoiceRecord');
  recordBtn.classList.remove('recording');
  document.getElementById('voiceMicIcon').innerHTML = `
    <svg class="icon-record-mic" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
      <line x1="12" y1="19" x2="12" y2="23"></line>
      <line x1="8" y1="23" x2="16" y2="23"></line>
    </svg>
  `;
  document.getElementById('voiceRecordText').textContent = 'Start Voice Recording';
  document.getElementById('voiceTimer').style.display = 'none';
  document.getElementById('recordingVisualizer').style.display = 'none';

  // Merge audio buffers into a single PCM Float32Array
  let totalLength = 0;
  for (const b of recordedBuffers) totalLength += b.length;
  const mergedSamples = new Float32Array(totalLength);
  let offset = 0;
  for (const b of recordedBuffers) {
    mergedSamples.set(b, offset);
    offset += b.length;
  }

  const sampleRate = (audioContext && audioContext.sampleRate) ? audioContext.sampleRate : 16000;
  if (audioContext) {
    try { audioContext.close(); } catch (e) {}
  }

  // Encode to Standard 16-bit PCM WAV Blob
  const wavBlob = encodeWAV(mergedSamples, sampleRate);

  // Send to backend Voice Interaction endpoint
  await sendVoiceInteraction(wavBlob, liveSpeechTranscript);
}

// Standard 16-bit mono PCM WAV Encoder
function encodeWAV(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  // RIFF identifier
  writeString(view, 0, 'RIFF');
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(view, 8, 'WAVE');
  
  // Format chunk identifier
  writeString(view, 12, 'fmt ');
  view.setUint32(16, 16, true);          // SubChunk1Size (16 for PCM)
  view.setUint16(20, 1, true);           // AudioFormat (1 = PCM)
  view.setUint16(22, 1, true);           // NumChannels (1 = Mono)
  view.setUint32(24, sampleRate, true);  // SampleRate
  view.setUint32(28, sampleRate * 2, true); // ByteRate (SampleRate * NumChannels * BitsPerSample/8)
  view.setUint16(32, 2, true);           // BlockAlign (NumChannels * BitsPerSample/8)
  view.setUint16(34, 16, true);          // BitsPerSample (16 bits)

  // Data chunk identifier
  writeString(view, 36, 'data');
  view.setUint32(40, samples.length * 2, true);

  // Float32 to 16-bit PCM
  let index = 44;
  for (let i = 0; i < samples.length; i++, index += 2) {
    let s = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(index, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
  }

  return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

// Handle Uploading an Audio File
async function handleAudioUpload(event) {
  const file = event.target.files[0];
  if (!file) return;

  await sendVoiceInteraction(file, '');
  event.target.value = ''; // Reset input
}

// Send Voice Interaction to Backend
async function sendVoiceInteraction(audioBlobOrFile, fallbackText = '') {
  const convBox = document.getElementById('voiceConversationBox');
  const userText = document.getElementById('userTranscriptText');
  const aiText = document.getElementById('aiTranscriptText');
  const userPlayer = document.getElementById('userAudioPlayer');
  const actionTag = document.getElementById('voiceActionTag');

  convBox.style.display = 'flex';
  userText.textContent = fallbackText || 'Processing and transcribing your voice record...';
  aiText.textContent = 'Analyzing voice input and generating audio response...';
  actionTag.textContent = 'Processing...';

  // If user provided a local audio blob, show player
  if (audioBlobOrFile instanceof Blob) {
    userPlayer.src = URL.createObjectURL(audioBlobOrFile);
    userPlayer.style.display = 'block';
  } else {
    userPlayer.style.display = 'none';
  }

  // Gather current job description and candidates
  const jobDesc = document.getElementById('jobDescription').value.trim();
  const candidateRows = document.querySelectorAll('.candidate-row');
  const candidateNames = [];
  const candidateTexts = [];
  candidateRows.forEach(row => {
    const n = row.querySelector('.candidate-name-input')?.value.trim();
    const t = row.querySelector('.candidate-text-area')?.value.trim();
    if (n && t) {
      candidateNames.push(n);
      candidateTexts.push(t);
    }
  });

  const selectedLang = document.getElementById('voiceLangSelect').value;

  const formData = new FormData();
  if (audioBlobOrFile) {
    formData.append('audio', audioBlobOrFile, 'recording.wav');
  }
  if (fallbackText) {
    formData.append('fallback_text', fallbackText);
  }
  formData.append('language', selectedLang);
  formData.append('job_description', jobDesc);
  candidateNames.forEach(n => formData.append('candidate_names[]', n));
  candidateTexts.forEach(t => formData.append('candidate_texts[]', t));

  try {
    const res = await fetch('/api/voice/interact', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    if (!res.ok) {
      userText.textContent = fallbackText || 'Audio record processed.';
      aiText.textContent = data.error || 'Voice processing failed.';
      actionTag.textContent = 'Error';
      return;
    }

    // Update User Transcript Bubble
    userText.textContent = data.transcribed_text || fallbackText || '(Unrecognized speech)';

    // Update AI Voice Response Bubble
    aiText.textContent = data.response_text;
    actionTag.textContent = data.action ? data.action.toUpperCase() : 'VOICE REPLY';

    // Play Voice Response Audio
    if (data.audio_base64) {
      loadAiVoiceAudio(data.audio_base64);
    }

    // Execute Client-side Actions triggered by voice
    if (data.action === 'screen' && data.ranked) {
      displayResults(data);
    } else if (data.action === 'load_preset' && data.action_data?.preset_id) {
      loadPreset(data.action_data.preset_id);
    } else if (data.action === 'update_job' && data.action_data?.job_description) {
      document.getElementById('jobDescription').value = data.action_data.job_description;
    }

  } catch (err) {
    console.error('Voice interaction error:', err);
    aiText.textContent = 'Network error communicating with voice server: ' + err.message;
    actionTag.textContent = 'Connection Error';
  }
}

// Simulate Voice Query (Quick voice prompts)
async function simulateVoiceQuery(queryText) {
  const convBox = document.getElementById('voiceConversationBox');
  const userText = document.getElementById('userTranscriptText');
  const aiText = document.getElementById('aiTranscriptText');
  const userPlayer = document.getElementById('userAudioPlayer');

  convBox.style.display = 'flex';
  userPlayer.style.display = 'none';
  userText.textContent = `"${queryText}"`;
  aiText.textContent = 'Processing request and formulating voice reply...';

  await sendVoiceInteraction(null, queryText);
}

// Load and optionally Auto-play the AI Voice Audio Response
function loadAiVoiceAudio(audioDataUri) {
  const player = document.getElementById('aiAudioPlayer');
  player.src = audioDataUri;

  const autoPlay = document.getElementById('autoPlayVoiceToggle').checked;
  if (autoPlay) {
    player.play().catch(e => {
      console.log('Auto-play was prevented by browser policy (user gesture required):', e);
    });
  }
}

function setupAudioPlayerEvents() {
  const player = document.getElementById('aiAudioPlayer');
  const waveAnim = document.getElementById('aiWaveAnim');
  const playIcon = document.getElementById('playPauseIcon');
  const timeLabel = document.getElementById('aiAudioTime');

  if (!player) return;

  const svgPlay = `
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>
  `;
  const svgPause = `
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
      <rect x="6" y="4" width="4" height="16"></rect>
      <rect x="14" y="4" width="4" height="16"></rect>
    </svg>
  `;

  player.addEventListener('play', () => {
    waveAnim.classList.add('playing');
    playIcon.innerHTML = svgPause;
  });

  player.addEventListener('pause', () => {
    waveAnim.classList.remove('playing');
    playIcon.innerHTML = svgPlay;
  });

  player.addEventListener('ended', () => {
    waveAnim.classList.remove('playing');
    playIcon.innerHTML = svgPlay;
  });

  player.addEventListener('timeupdate', () => {
    if (player.duration) {
      const cur = Math.floor(player.currentTime);
      const total = Math.floor(player.duration);
      timeLabel.textContent = `${cur}s / ${total}s`;
    }
  });
}

function togglePlayAiAudio() {
  const player = document.getElementById('aiAudioPlayer');
  if (!player.src) return;

  if (player.paused) {
    player.play();
  } else {
    player.pause();
  }
}

function replayAiAudio() {
  const player = document.getElementById('aiAudioPlayer');
  if (!player.src) return;
  player.currentTime = 0;
  player.play();
}

// ============================================================================
// Mini Dictation on Specific Text Fields
// ============================================================================
let activeDictationTarget = null;
let dictationRecognition = null;

function dictateField(targetId) {
  const textarea = document.getElementById(targetId);
  const btn = document.getElementById('btnDictateJob');
  handleFieldDictation(textarea, btn);
}

function dictateCandidateRow(buttonElement) {
  const row = buttonElement.closest('.candidate-row');
  const textarea = row.querySelector('.candidate-text-area');
  handleFieldDictation(textarea, buttonElement);
}

function handleFieldDictation(textareaElement, buttonElement) {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    alert('Voice recognition in field requires a modern browser supporting Web Speech API (Chrome/Edge/Safari), or use the main Voice Screener at the top.');
    return;
  }

  const setDictateBtnState = (btn, isListening) => {
    if (isListening) {
      btn.classList.add('dictating');
      btn.innerHTML = `
        <span class="red-pulse-dot" style="width:7px; height:7px; display:inline-block;"></span>
        <span>Listening...</span>
      `;
    } else {
      btn.classList.remove('dictating');
      btn.innerHTML = `
        <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          <line x1="12" y1="19" x2="12" y2="23"></line>
          <line x1="8" y1="23" x2="16" y2="23"></line>
        </svg>
        <span>Dictate</span>
      `;
    }
  };

  if (activeDictationTarget === textareaElement && dictationRecognition) {
    // Stop dictation
    dictationRecognition.stop();
    activeDictationTarget = null;
    setDictateBtnState(buttonElement, false);
    return;
  }

  try {
    dictationRecognition = new SpeechRec();
    const selectedLang = document.getElementById('voiceLangSelect').value;
    dictationRecognition.lang = selectedLang === 'ar' ? 'ar-EG' : (selectedLang === 'en' ? 'en-US' : 'en-US');
    dictationRecognition.continuous = false;
    dictationRecognition.interimResults = false;

    setDictateBtnState(buttonElement, true);
    activeDictationTarget = textareaElement;

    dictationRecognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript;
      const current = textareaElement.value.trim();
      textareaElement.value = current ? `${current} ${transcript}` : transcript;
    };

    dictationRecognition.onend = () => {
      setDictateBtnState(buttonElement, false);
      activeDictationTarget = null;
    };

    dictationRecognition.onerror = (e) => {
      console.warn('Dictation error:', e);
      setDictateBtnState(buttonElement, false);
      activeDictationTarget = null;
    };

    dictationRecognition.start();

  } catch (err) {
    console.error('Dictation setup failed:', err);
    setDictateBtnState(buttonElement, false);
  }
}

// Speak the winner candidate review using TTS
async function speakCurrentWinner() {
  if (!currentRankedResults || currentRankedResults.length === 0) {
    alert('Please screen resumes first to review the top candidate.');
    return;
  }

  const top = currentRankedResults[0];
  const skills = (top.matched_keywords && top.matched_keywords.length)
    ? top.matched_keywords.slice(0, 4).join(', ')
    : 'core job requirements';

  const selectedLang = document.getElementById('voiceLangSelect').value;
  const isAr = selectedLang === 'ar';

  const textToSpeak = isAr
    ? `أفضل مرشح هو ${top.name} بنسبة توافق ${top.score_percent}. من أهم مهاراته المطابقة: ${skills}.`
    : `The top ranked candidate is ${top.name} with an overall match score of ${top.score_percent}. Top matching skills include: ${skills}.`;

  try {
    const res = await fetch('/api/voice/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: textToSpeak,
        language: isAr ? 'ar' : 'en'
      })
    });
    const data = await res.json();
    if (data.audio_base64) {
      loadAiVoiceAudio(data.audio_base64);
      // Show in AI bubble
      const convBox = document.getElementById('voiceConversationBox');
      const aiText = document.getElementById('aiTranscriptText');
      const actionTag = document.getElementById('voiceActionTag');
      convBox.style.display = 'flex';
      aiText.textContent = textToSpeak;
      actionTag.textContent = 'TOP CANDIDATE REVIEW';
    }
  } catch (err) {
    alert('Failed to generate speech for top candidate: ' + err.message);
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

// ============================================================================
// Voice Tutorial Speaker & Guide Logic
// ============================================================================
let tutorialAudioData = null;
let tutorialSteps = [];
const tutorialClientCache = {};
let isTutorialLoading = false;

async function openVoiceTutorial(requestedLang) {
  const modal = document.getElementById('voiceTutorialBackdrop');
  if (!modal) return;
  modal.style.display = 'flex';

  const select = document.getElementById('tutorialLangSelect');
  const lang = requestedLang || (select ? select.value : 'en') || 'en';
  if (select) select.value = lang;

  // Use cached tutorial audio and steps if already fetched
  if (tutorialClientCache[lang]) {
    applyTutorialData(tutorialClientCache[lang]);
    return;
  }

  // Prevent duplicate concurrent requests
  if (isTutorialLoading) return;
  isTutorialLoading = true;

  const stepsContainer = document.getElementById('tutorialStepsContainer');
  if (stepsContainer) {
    stepsContainer.innerHTML = '<p style="color:var(--text-muted); font-size:0.85rem; grid-column:span 2; text-align:center;">Loading interactive spoken guide...</p>';
  }

  try {
    const res = await fetch(`/api/tutorial/voice?language=${lang}`);
    const data = await res.json();

    if (data.success) {
      tutorialClientCache[lang] = data;
      applyTutorialData(data);
    }
  } catch (err) {
    console.error('Failed to load voice tutorial:', err);
    if (stepsContainer) {
      stepsContainer.innerHTML = '<p style="color:var(--rose-text); font-size:0.85rem;">Failed to load voice tutorial audio.</p>';
    }
  } finally {
    isTutorialLoading = false;
  }
}

function applyTutorialData(data) {
  tutorialAudioData = data;
  tutorialSteps = data.steps || [];
  renderTutorialSteps(tutorialSteps);

  const player = document.getElementById('tutorialAudioPlayer');
  if (player && data.audio_base64) {
    // Pause other audio players to prevent sound conflict
    const aiPlayer = document.getElementById('aiAudioPlayer');
    if (aiPlayer && !aiPlayer.paused) aiPlayer.pause();

    player.loop = false;
    player.src = data.audio_base64;
    player.currentTime = 0;
    player.play().catch(e => console.log('Tutorial auto-play note:', e));
  }
}

function renderTutorialSteps(steps) {
  const container = document.getElementById('tutorialStepsContainer');
  if (!container) return;

  container.innerHTML = steps.map((s, idx) => `
    <div class="tutorial-step-card ${idx === 0 ? 'active-step' : ''}" id="tutorialStepCard_${idx}">
      <span class="step-card-num">${s.step}</span>
      <div class="step-card-content">
        <h5>${escapeHtml(s.title)}</h5>
        <p>${escapeHtml(s.description)}</p>
      </div>
    </div>
  `).join('');
}

function stopTutorialAudio() {
  const player = document.getElementById('tutorialAudioPlayer');
  if (!player) return;
  player.pause();
  player.currentTime = 0;

  const waveAnim = document.getElementById('tutorialWaveAnim');
  const playIcon = document.getElementById('tutorialPlayIcon');
  const playLabel = document.getElementById('tutorialPlayLabel');
  if (waveAnim) waveAnim.classList.remove('playing');
  if (playIcon) {
    playIcon.innerHTML = `
      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
        <polygon points="5 3 19 12 5 21 5 3"></polygon>
      </svg>
    `;
  }
  if (playLabel) playLabel.textContent = 'Play Voice Tutorial';

  document.querySelectorAll('.tutorial-step-card').forEach((card, idx) => {
    card.classList.toggle('active-step', idx === 0);
  });
}

function closeVoiceTutorial(e) {
  if (e && e.target && e.target !== document.getElementById('voiceTutorialBackdrop') && !e.target.closest('.btn-close-modal')) {
    return;
  }
  const modal = document.getElementById('voiceTutorialBackdrop');
  if (modal) modal.style.display = 'none';

  stopTutorialAudio();
}

function switchTutorialLanguage(lang) {
  openVoiceTutorial(lang);
}

function togglePlayTutorialAudio() {
  const player = document.getElementById('tutorialAudioPlayer');
  if (!player || !player.src) return;

  if (player.paused) {
    player.play();
  } else {
    player.pause();
  }
}

function replayTutorialAudio() {
  const player = document.getElementById('tutorialAudioPlayer');
  if (!player || !player.src) return;
  player.currentTime = 0;
  player.play();
}

function setupTutorialPlayerEvents() {
  const player = document.getElementById('tutorialAudioPlayer');
  const waveAnim = document.getElementById('tutorialWaveAnim');
  const playIcon = document.getElementById('tutorialPlayIcon');
  const playLabel = document.getElementById('tutorialPlayLabel');
  const timeLabel = document.getElementById('tutorialAudioTime');

  if (!player) return;
  player.loop = false; // Strictly prevent looping

  const svgPlay = `
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
    </svg>
  `;
  const svgPause = `
    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
      <rect x="6" y="4" width="4" height="16"></rect>
      <rect x="14" y="4" width="4" height="16"></rect>
    </svg>
  `;

  player.addEventListener('play', () => {
    if (waveAnim) waveAnim.classList.add('playing');
    if (playIcon) playIcon.innerHTML = svgPause;
    if (playLabel) playLabel.textContent = 'Pause Guide';
  });

  player.addEventListener('pause', () => {
    if (waveAnim) waveAnim.classList.remove('playing');
    if (playIcon) playIcon.innerHTML = svgPlay;
    if (playLabel) playLabel.textContent = 'Play Guide';
  });

  player.addEventListener('ended', () => {
    if (waveAnim) waveAnim.classList.remove('playing');
    if (playIcon) playIcon.innerHTML = svgPlay;
    if (playLabel) playLabel.textContent = 'Play Guide';
    player.currentTime = 0;
    // Clean stop without looping or re-triggering
    document.querySelectorAll('.tutorial-step-card').forEach((card, idx) => {
      card.classList.toggle('active-step', idx === 0);
    });
  });

  player.addEventListener('timeupdate', () => {
    if (player.duration) {
      const cur = Math.floor(player.currentTime);
      const total = Math.floor(player.duration);
      if (timeLabel) timeLabel.textContent = `${cur}s / ${total}s`;

      const progress = player.currentTime / player.duration;
      const stepIndex = Math.min(3, Math.floor(progress * 4));
      document.querySelectorAll('.tutorial-step-card').forEach((card, idx) => {
        card.classList.toggle('active-step', idx === stepIndex);
      });
    }
  });

  // Close tutorial modal on Escape key press
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const modal = document.getElementById('voiceTutorialBackdrop');
      if (modal && modal.style.display !== 'none') {
        closeVoiceTutorial();
      }
    }
  });
}

// ============================================================================
// Ollama AI Recruitment Assistant Chatbot with Interactive Voice Recording
// ============================================================================
let chatHistory = [];
let isChatRecording = false;
let chatAudioContext = null;
let chatMediaStream = null;
let chatScriptProcessor = null;
let chatRecordedBuffers = [];
let chatRecordingStartTime = null;
let chatRecordingTimerInterval = null;
let chatSpeechRecInstance = null;
let chatLiveSpeechTranscript = '';

async function toggleChatVoiceRecording() {
  if (!isChatRecording) {
    await startChatVoiceRecording();
  } else {
    await stopChatVoiceRecordingAndSend();
  }
}

async function startChatVoiceRecording() {
  // Stop other playing audio
  stopTutorialAudio();
  const aiPlayer = document.getElementById('aiAudioPlayer');
  if (aiPlayer && !aiPlayer.paused) aiPlayer.pause();

  try {
    chatMediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    chatAudioContext = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 16000 });
    const sourceNode = chatAudioContext.createMediaStreamSource(chatMediaStream);

    chatScriptProcessor = chatAudioContext.createScriptProcessor(4096, 1, 1);
    chatRecordedBuffers = [];

    chatScriptProcessor.onaudioprocess = (e) => {
      if (!isChatRecording) return;
      const inputData = e.inputBuffer.getChannelData(0);
      chatRecordedBuffers.push(new Float32Array(inputData));
    };

    sourceNode.connect(chatScriptProcessor);
    chatScriptProcessor.connect(chatAudioContext.destination);

    // Parallel Speech Recognition for real-time visual feedback
    chatLiveSpeechTranscript = '';
    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRec) {
      try {
        chatSpeechRecInstance = new SpeechRec();
        const selectedLang = document.getElementById('voiceLangSelect') ? document.getElementById('voiceLangSelect').value : 'auto';
        chatSpeechRecInstance.lang = selectedLang === 'ar' ? 'ar-EG' : 'en-US';
        chatSpeechRecInstance.continuous = true;
        chatSpeechRecInstance.interimResults = true;
        chatSpeechRecInstance.onresult = (evt) => {
          let text = '';
          for (let i = 0; i < evt.results.length; ++i) {
            text += evt.results[i][0].transcript;
          }
          chatLiveSpeechTranscript = text;
          if (text) {
            const statusEl = document.getElementById('chatRecStatusText');
            if (statusEl) statusEl.textContent = `Hearing: "${text.slice(-30)}"`;
          }
        };
        chatSpeechRecInstance.start();
      } catch (err) {
        console.warn('Chat SpeechRecognition init note:', err);
      }
    }

    // UI Updates
    isChatRecording = true;
    chatRecordingStartTime = Date.now();

    const banner = document.getElementById('chatRecordingBanner');
    if (banner) banner.style.display = 'flex';

    const micBtn = document.getElementById('btnChatMic');
    if (micBtn) {
      micBtn.classList.add('recording');
      micBtn.title = 'Stop Voice Recording & Send (إنهاء وإرسال التسجيل)';
    }

    const statusEl = document.getElementById('chatRecStatusText');
    if (statusEl) statusEl.textContent = 'Recording Voice Message... Speak clearly';

    // Start Recording Timer
    clearInterval(chatRecordingTimerInterval);
    chatRecordingTimerInterval = setInterval(() => {
      const elapsed = Math.floor((Date.now() - chatRecordingStartTime) / 1000);
      const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
      const secs = String(elapsed % 60).padStart(2, '0');
      const timerEl = document.getElementById('chatRecTimer');
      if (timerEl) timerEl.textContent = `${mins}:${secs}`;
    }, 500);

  } catch (err) {
    console.error('Chat microphone access failed:', err);
    alert(
      '⚠️ Microphone Access Error:\n' +
      (err.name === 'NotAllowedError'
        ? 'Microphone permission was denied. Please allow microphone access in your browser address bar.\nيرجى السماح بالوصول للميكروفون من إعدادات المتصفح.'
        : err.message)
    );
  }
}

async function stopChatVoiceRecordingAndSend() {
  if (!isChatRecording) return;
  isChatRecording = false;

  clearInterval(chatRecordingTimerInterval);

  if (chatSpeechRecInstance) {
    try { chatSpeechRecInstance.stop(); } catch (e) {}
  }

  if (chatScriptProcessor) chatScriptProcessor.disconnect();
  if (chatMediaStream) {
    chatMediaStream.getTracks().forEach(track => track.stop());
  }

  const micBtn = document.getElementById('btnChatMic');
  if (micBtn) {
    micBtn.classList.remove('recording');
    micBtn.title = 'Record Voice Message (تسجيل صوتي)';
  }

  const statusEl = document.getElementById('chatRecStatusText');
  if (statusEl) statusEl.textContent = 'Transcribing voice record...';

  // Merge Float32Array PCM samples
  let totalLength = 0;
  for (const b of chatRecordedBuffers) totalLength += b.length;
  const mergedSamples = new Float32Array(totalLength);
  let offset = 0;
  for (const b of chatRecordedBuffers) {
    mergedSamples.set(b, offset);
    offset += b.length;
  }

  const sampleRate = (chatAudioContext && chatAudioContext.sampleRate) ? chatAudioContext.sampleRate : 16000;
  if (chatAudioContext) {
    try { chatAudioContext.close(); } catch (e) {}
  }

  const banner = document.getElementById('chatRecordingBanner');
  if (banner) banner.style.display = 'none';

  // Ignore ultra short clicks (< 0.25s) unless live speech captured
  if (mergedSamples.length < sampleRate * 0.25) {
    if (chatLiveSpeechTranscript) {
      document.getElementById('chatInputText').value = chatLiveSpeechTranscript;
      submitChatMessage(true);
    }
    return;
  }

  // Encode to Standard 16-bit PCM WAV Blob
  const wavBlob = encodeWAV(mergedSamples, sampleRate);

  // Send to backend transcription endpoint
  const selectedLang = document.getElementById('voiceLangSelect') ? document.getElementById('voiceLangSelect').value : 'auto';
  const formData = new FormData();
  formData.append('audio', wavBlob, 'chat_voice.wav');
  formData.append('language', selectedLang);

  try {
    const res = await fetch('/api/voice/transcribe', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    let finalTranscribedText = (data && data.success && data.text) ? data.text.trim() : '';

    // Fallback to client speech recognition if backend was empty
    if (!finalTranscribedText && chatLiveSpeechTranscript) {
      finalTranscribedText = chatLiveSpeechTranscript.trim();
    }

    if (finalTranscribedText) {
      const input = document.getElementById('chatInputText');
      if (input) input.value = finalTranscribedText;
      // Auto-submit voice recorded message
      submitChatMessage(true);
    } else {
      alert('لم يتم التعرف على الصوت بوضوح، يرجى التحدث بوضوح وإعادة المحاولة.\nCould not detect clear speech in the voice recording. Please speak clearly into your microphone and try again.');
    }

  } catch (err) {
    console.error('Chat voice transcription error:', err);
    if (chatLiveSpeechTranscript) {
      const input = document.getElementById('chatInputText');
      if (input) input.value = chatLiveSpeechTranscript;
      submitChatMessage(true);
    } else {
      alert('Voice transcription error: ' + err.message);
    }
  }
}

function cancelChatVoiceRecording() {
  if (!isChatRecording) return;
  isChatRecording = false;

  clearInterval(chatRecordingTimerInterval);

  if (chatSpeechRecInstance) {
    try { chatSpeechRecInstance.stop(); } catch (e) {}
  }

  if (chatScriptProcessor) chatScriptProcessor.disconnect();
  if (chatMediaStream) {
    chatMediaStream.getTracks().forEach(track => track.stop());
  }

  if (chatAudioContext) {
    try { chatAudioContext.close(); } catch (e) {}
  }

  const banner = document.getElementById('chatRecordingBanner');
  if (banner) banner.style.display = 'none';

  const micBtn = document.getElementById('btnChatMic');
  if (micBtn) {
    micBtn.classList.remove('recording');
    micBtn.title = 'Record Voice Message (تسجيل صوتي)';
  }
}

async function fetchOllamaModels() {
  const select = document.getElementById('chatModelSelect');
  const dot = document.getElementById('ollamaStatusDot');
  if (!select) return;

  try {
    const res = await fetch('/api/ollama/models');
    const data = await res.json();

    if (data.status === 'online' && data.models && data.models.length > 0) {
      select.innerHTML = data.models.map(m => `
        <option value="${escapeHtml(m)}" ${m === data.default_model ? 'selected' : ''}>${escapeHtml(m)}</option>
      `).join('');
      if (dot) {
        dot.classList.remove('offline');
        dot.title = `Ollama Online (${data.models.length} models available)`;
      }
    } else {
      if (dot) {
        dot.classList.add('offline');
        dot.title = 'Ollama Standby / Fallback Enabled';
      }
    }
  } catch (e) {
    if (dot) dot.classList.add('offline');
  }
}

function toggleOllamaChat() {
  const panel = document.getElementById('chatPanel');
  const openIcon = document.getElementById('iconChatOpen');
  const closeIcon = document.getElementById('iconChatClose');
  if (!panel) return;

  const isHidden = panel.style.display === 'none' || !panel.style.display;
  panel.style.display = isHidden ? 'flex' : 'none';

  if (openIcon && closeIcon) {
    openIcon.style.display = isHidden ? 'none' : 'block';
    closeIcon.style.display = isHidden ? 'block' : 'none';
  }

  if (isHidden) {
    const textarea = document.getElementById('chatInputText');
    if (textarea) textarea.focus();
  }
}

function handleChatKeyDown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    submitChatMessage();
  }
}

function sendChatPrompt(promptText) {
  const input = document.getElementById('chatInputText');
  if (input) {
    input.value = promptText;
    submitChatMessage();
  }
}

async function submitChatMessage(isVoiceNote = false) {
  const input = document.getElementById('chatInputText');
  const body = document.getElementById('chatMessagesBody');
  const select = document.getElementById('chatModelSelect');
  if (!input || !body) return;

  const message = input.value.trim();
  if (!message) return;

  input.value = '';

  // Append user bubble with voice note badge if recorded via mic
  appendChatBubble('user', message, '', isVoiceNote);
  chatHistory.push({ role: 'user', content: message });

  // Add temporary loading typing indicator
  const typingId = 'typingIndicator_' + Date.now();
  const typingBubble = document.createElement('div');
  typingBubble.className = 'chat-message assistant-msg';
  typingBubble.id = typingId;
  typingBubble.innerHTML = `
    <div class="msg-bubble" style="color:var(--text-muted); font-style:italic;">
      <span class="status-pulse-dot" style="width:6px; height:6px; display:inline-block; margin-right:4px;"></span>
      AI Recruiter is thinking...
    </div>
  `;
  body.appendChild(typingBubble);
  body.scrollTop = body.scrollHeight;

  // Gather current screening context
  const jobDesc = document.getElementById('jobDescription') ? document.getElementById('jobDescription').value.trim() : '';
  const context = {
    job_description: jobDesc,
    ranked: currentRankedResults || []
  };

  const model = select ? select.value : 'mistral:latest';

  try {
    const res = await fetch('/api/ollama/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: message,
        history: chatHistory,
        model: model,
        context: context
      })
    });

    const data = await res.json();
    const typingNode = document.getElementById(typingId);
    if (typingNode) typingNode.remove();

    if (data.success && data.reply) {
      appendChatBubble('assistant', data.reply, data.model);
      chatHistory.push({ role: 'assistant', content: data.reply });
    } else {
      appendChatBubble('assistant', data.error || 'Failed to generate response. Please verify Ollama is active.');
    }

  } catch (err) {
    const typingNode = document.getElementById(typingId);
    if (typingNode) typingNode.remove();
    appendChatBubble('assistant', 'Network error connecting to AI Chat server: ' + err.message);
  }
}

function appendChatBubble(role, text, modelName = '', isVoiceNote = false) {
  const body = document.getElementById('chatMessagesBody');
  if (!body) return;

  const msgDiv = document.createElement('div');
  msgDiv.className = `chat-message ${role === 'user' ? 'user-msg' : 'assistant-msg'}`;

  const formatted = formatChatText(text);

  if (role === 'assistant') {
    const safeText = escapeHtml(text).replace(/'/g, "\\'");
    msgDiv.innerHTML = `
      <div class="msg-bubble">
        ${formatted}
        <div class="msg-footer">
          <button type="button" class="btn-speak-msg" onclick="speakMessageText(this, '${safeText}')" title="Read Aloud">
            <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"></polygon>
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07"></path>
            </svg>
          </button>
        </div>
      </div>
    `;
  } else {
    const voiceBadgeHtml = isVoiceNote ? `
      <div class="voice-note-badge">
        <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"></path>
          <path d="M19 10v2a7 7 0 0 1-14 0v-2"></path>
          <line x1="12" y1="19" x2="12" y2="23"></line>
        </svg>
        <span>Voice Recording</span>
      </div>
    ` : '';
    msgDiv.innerHTML = `<div class="msg-bubble">${voiceBadgeHtml}${formatted}</div>`;
  }

  body.appendChild(msgDiv);
  body.scrollTop = body.scrollHeight;
}

function formatChatText(text) {
  if (!text) return '';
  let str = escapeHtml(text);

  // Headers ###
  str = str.replace(/^### (.*$)/gim, '<h4>$1</h4>');
  str = str.replace(/^## (.*$)/gim, '<h3>$1</h3>');

  // Bold **text**
  str = str.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');

  // Bullet items
  str = str.replace(/^\s*[-•]\s+(.*$)/gim, '<li>$1</li>');
  str = str.replace(/(<li>.*<\/li>)/gms, '<ul>$1</ul>');

  // Paragraphs
  str = str.replace(/\n\n+/g, '</p><p>');
  str = `<p>${str}</p>`;
  str = str.replace(/<p><\/p>/g, '');

  return str;
}

// Speak Chat Response via TTS
async function speakMessageText(btn, text) {
  if (!text) return;

  const originalSvg = btn.innerHTML;
  btn.innerHTML = `
    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2">
      <circle cx="12" cy="12" r="10"></circle>
      <polyline points="12 6 12 12 16 14"></polyline>
    </svg>
  `;

  const isAr = /[\u0600-\u06FF]/.test(text);

  try {
    const res = await fetch('/api/voice/speak', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text.slice(0, 300),
        language: isAr ? 'ar' : 'en'
      })
    });
    const data = await res.json();
    btn.innerHTML = originalSvg;

    if (data.audio_base64) {
      loadAiVoiceAudio(data.audio_base64);
    }
  } catch (err) {
    btn.innerHTML = originalSvg;
    console.warn('TTS playback failed:', err);
  }
}
