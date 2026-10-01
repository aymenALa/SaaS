const state = { file: null, job: null, originalUrl: null, poll: null };
const $ = (id) => document.getElementById(id);
const panels = ['dropzone', 'preview-panel', 'processing-panel', 'result-panel'];
function show(id) { panels.forEach((panel) => $(panel).classList.toggle('hidden', panel !== id)); }
function toast(message) { const node = $('toast'); node.textContent = message; node.classList.add('show'); setTimeout(() => node.classList.remove('show'), 3200); }
function formatBytes(bytes) { return `${(bytes / 1024 / 1024).toFixed(2)} MB`; }
function selectFile(file) {
  if (!file) return;
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return toast('Please choose a JPEG, PNG, or WebP image.');
  if (file.size > 10 * 1024 * 1024) return toast('This image is larger than the 10 MB limit.');
  state.file = file; state.originalUrl = URL.createObjectURL(file);
  $('preview-image').src = state.originalUrl; $('file-name').textContent = file.name; $('file-size').textContent = formatBytes(file.size); show('preview-panel');
}
function reset() { if (state.poll) clearTimeout(state.poll); if (state.originalUrl) URL.revokeObjectURL(state.originalUrl); state.file = null; state.job = null; show('dropzone'); $('file-input').value = ''; }
async function processFile() {
  if (!state.file) return;
  show('processing-panel'); $('processing-title').textContent = 'Finding visible faces'; $('processing-copy').textContent = 'The lightweight CPU pipeline is working. This usually takes a moment.';
  const body = new FormData(); body.append('file', state.file);
  try { const response = await fetch('/api/v1/jobs', { method: 'POST', body }); if (!response.ok) throw new Error((await response.json()).detail || 'Upload failed'); state.job = await response.json(); pollJob(); }
  catch (error) { toast(error.message); show('preview-panel'); }
}
async function pollJob() {
  try {
    const response = await fetch(`/api/v1/jobs/${state.job.id}`); state.job = await response.json();
    if (state.job.status === 'completed') return renderResult();
    if (state.job.status === 'failed') { toast(state.job.error || 'Processing failed.'); return show('preview-panel'); }
    state.poll = setTimeout(pollJob, 400);
  } catch { toast('Could not read job status.'); show('preview-panel'); }
}
function renderResult() {
  $('result-image').src = `/api/v1/jobs/${state.job.id}/download?cache=${Date.now()}`;
  const m = state.job.metrics; $('result-limitation').textContent = m.limitation;
  $('metrics').innerHTML = `<div><span class="metric-label">Faces found</span><strong class="metric-value">${m.faces_detected}</strong></div><div><span class="metric-label">Faces protected</span><strong class="metric-value">${m.faces_protected}</strong></div><div><span class="metric-label">Quality · PSNR</span><strong class="metric-value">${m.psnr_db ? `${m.psnr_db} dB` : 'N/A'}</strong></div>`;
  show('result-panel');
}
function download() { window.location.href = `/api/v1/jobs/${state.job.id}/download`; }
$('file-input').addEventListener('change', (event) => selectFile(event.target.files[0]));
$('dropzone').addEventListener('dragover', (event) => { event.preventDefault(); $('dropzone').classList.add('dragging'); });
$('dropzone').addEventListener('dragleave', () => $('dropzone').classList.remove('dragging'));
$('dropzone').addEventListener('drop', (event) => { event.preventDefault(); $('dropzone').classList.remove('dragging'); selectFile(event.dataTransfer.files[0]); });
$('process-button').addEventListener('click', processFile); $('clear-button').addEventListener('click', reset); $('new-button').addEventListener('click', reset); $('download-button').addEventListener('click', download);
