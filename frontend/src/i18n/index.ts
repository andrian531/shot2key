export type UILang = 'id' | 'en'

export interface UIStrings {
  // Header & Navigation
  appSubtitle: string
  navLibrary: string
  navSettings: string
  navAriaLabel: string
  langSwitchAriaLabel: string
  depsIncomplete: string
  reaNotFound: string
  ffmpegNotFound: string
  agyNotFound: string
  codexNotFound: string

  // Library & Upload
  libraryTitle: string
  librarySubtitle: string
  dropVideoTitle: string
  dropVideoDesc: string
  chooseFile: string
  uploading: string
  recentProjects: string
  noProjects: string
  deleteProjectConfirm: string
  deleteProjectTitle: string
  deleteLabel: string
  localStorageNote: string
  sceneUnit: string
  shotUnit: string

  // Project View & Storyboard
  projectNotFound: string
  projectNotFoundDesc: string
  backToLibrary: string
  allProjects: string
  analyzerLabel: string
  imageEngineLabel: string
  notReady: string
  analyzeBtn: string
  analyzingBtn: string
  generateFirstAll: (count: number) => string
  generatingAll: string
  logsBtn: string
  exportZip: string
  audioReportTitle: string
  openReport: string
  logsTitle: (count: number) => string
  closeBtn: string
  loadingLogs: string
  noLogs: string
  inputImagesLabel: string
  promptSentLabel: string
  rawResponseLabel: string
  logFallbackFromLabel: string
  analyzingProgress: (done: number, total: number, engine: string) => string
  generatingProgress: (done: number, total: number, engine: string) => string
  decomposeFailed: (err: string) => string
  promptCountLabel: string
  keyframeCountLabel: string
  partialAnalyzeWarning: string
  failedKeyframesWarning: (count: number) => string
  subtitlesReady: string
  timelineTitle: (count: number) => string
  showingScene: (current: number, total: number) => string
  prevScene: string
  nextScene: string
  statusPromptOk: string
  statusQueued: string
  statusEmpty: string
  statusDeep: string
  statusFirstOk: string
  statusLastOk: string

  // Scene Card
  sceneTitle: (num: string) => string
  splitBadge: string
  splitBadgeTitle: string
  deepAnalyzeBtn: string
  deepAnalyzingBtn: string
  deepAnalyzeTitle: string
  deepAnalyzeDefaultMsg: string
  statusIdle: string
  statusQueue: string
  statusGenerating: string
  statusDone: string
  statusFailed: string
  firstBadgePrefix: string
  lastBadgePrefix: string
  clipTitle: (num: string) => string
  clipPlayingDesc: string
  clipIdleDesc: string
  downloadMp4: string
  closePlayer: string
  playClipHint: string
  refFirst: string
  refLast: string
  noLastRef: string
  cameraLabel: string
  lightingLabel: string
  timelineDetailTitle: (count: number) => string
  actionLabel: string
  expressionLabel: string
  backgroundLabel: string
  replaceCharLabel: string
  replaceSelectedCount: (selected: number, total: number) => string
  replaceDetectedCount: (total: number) => string
  supportingCharNote: string
  imagePromptsTitle: string
  imagePromptsDesc: string
  generateBothBtn: string
  generatingGeneric: string
  firstPromptLabel: string
  lastPromptLabel: string
  firstPromptPlaceholder: string
  lastPromptPlaceholder: string
  analyzingPlaceholder: string
  generateFirstBtn: string
  regenerateFirstBtn: string
  generatingFirstBtn: string
  generateLastBtn: string
  regenerateLastBtn: string
  generatingLastBtn: string
  resultFirstLabel: string
  resultLastLabel: string
  openFull: string
  firstGenFailed: string
  lastGenFailed: string
  videoPromptTitle: string
  videoPromptDesc: string
  generatePromptBtn: string
  generatingPromptProgress: string
  videoPromptPlaceholder: string
  videoPromptCharStaleWarning: string
  videoPromptDeepStaleWarning: string
  copyBtn: string
  copiedBtn: string

  // Settings
  settingsTitle: string
  settingsSubtitle: string
  loadingText: string
  loadSettingsFailed: (err: string) => string
  engineSectionTitle: string
  defaultAnalyzerLabel: string
  defaultModelLabel: string
  defaultCliConfigOption: string
  refreshModelsBtn: string
  loadingModelsBtn: string
  fallbackAnalyzerLabel: string
  fallbackDisabledOption: string
  fallbackModelLabel: string
  fallbackHint: string
  defaultImageEngineLabel: string
  maxDurationLabel: string
  maxDurationHint: string
  secondsUnit: (n: number) => string
  reaLangLabel: string
  useVlmLabel: string
  automationSectionTitle: string
  autoAnalyzeLabel: string
  defaultStyleLabel: string
  saveSettingsBtn: string
  savingBtn: string
  settingsSaved: string
}

const id: UIStrings = {
  appSubtitle: 'Studio pemecah adegan & keyframe',
  navLibrary: 'Pustaka',
  navSettings: 'Pengaturan',
  navAriaLabel: 'Navigasi utama',
  langSwitchAriaLabel: 'Pilih bahasa antarmuka',
  depsIncomplete: 'Dependensi belum lengkap',
  reaNotFound: 'rea-video tidak ditemukan di .venv',
  ffmpegNotFound: 'ffmpeg tidak ditemukan',
  agyNotFound: 'agy CLI tidak ditemukan',
  codexNotFound: 'codex CLI tidak ditemukan',

  libraryTitle: 'Pustaka Video',
  librarySubtitle: 'Unggah video referensi, lalu buka proyek untuk menyusun adegan, prompt, dan keyframe.',
  dropVideoTitle: 'Letakkan video referensi di sini',
  dropVideoDesc: '.mp4 / .mov / .mkv — rea-video akan memecahnya per shot, lalu Shot2Key membatasinya maksimal 10 detik per adegan.',
  chooseFile: 'Pilih file',
  uploading: 'Mengunggah...',
  recentProjects: 'Proyek terakhir',
  noProjects: 'Belum ada proyek.',
  deleteProjectConfirm: 'Hapus proyek ini beserta videonya?',
  deleteProjectTitle: 'Hapus proyek',
  deleteLabel: 'hapus',
  localStorageNote: 'Video disimpan lokal di backend/uploads/. Tidak ada unggahan ke cloud kecuali Anda memilih engine API.',
  sceneUnit: 'adegan',
  shotUnit: 'shot',

  projectNotFound: 'Proyek tidak ditemukan',
  projectNotFoundDesc: 'Proyek sudah dihapus atau belum pernah ada.',
  backToLibrary: '← Kembali ke Pustaka',
  allProjects: '← Semua proyek',
  analyzerLabel: 'Penganalisis',
  imageEngineLabel: 'Gambar',
  notReady: '(belum siap)',
  analyzeBtn: 'Analisis',
  analyzingBtn: 'Menganalisis...',
  generateFirstAll: (count) => `Buat Semua Awal (${count})`,
  generatingAll: 'Membuat...',
  logsBtn: 'Log',
  exportZip: 'Ekspor ZIP',
  audioReportTitle: 'Audio & Laporan',
  openReport: 'Buka report.html',
  logsTitle: (count) => `Log Prompt & Respons (${count})`,
  closeBtn: 'Tutup',
  loadingLogs: 'Memuat log...',
  noLogs: 'Belum ada log. Jalankan Analisis atau Buat Gambar untuk merekam prompt & respons.',
  inputImagesLabel: 'gambar masukan',
  promptSentLabel: 'prompt terkirim',
  rawResponseLabel: 'respons mentah',
  logFallbackFromLabel: 'Fallback dari error utama:',
  analyzingProgress: (done, total, engine) =>
    `Menganalisis & membuat prompt otomatis (${done}/${total} adegan) dengan ${engine}...`,
  generatingProgress: (done, total, engine) =>
    `Membuat gambar keyframe (${done}/${total}) dengan ${engine}...`,
  decomposeFailed: (err) => `Pemecahan video gagal: ${err}`,
  promptCountLabel: 'prompt',
  keyframeCountLabel: 'keyframe',
  partialAnalyzeWarning: 'sebagian adegan gagal dianalisis',
  failedKeyframesWarning: (count) => `${count} keyframe gagal`,
  subtitlesReady: 'subtitle .srt tersedia',
  timelineTitle: (count) => `Linimasa Adegan (${count})`,
  showingScene: (current, total) => `Menampilkan Adegan ${String(current).padStart(2, '0')} dari ${total}`,
  prevScene: '← Sebelumnya',
  nextScene: 'Berikutnya →',
  statusPromptOk: 'prompt ✓',
  statusQueued: 'antre...',
  statusEmpty: 'kosong',
  statusDeep: 'mendalam...',
  statusFirstOk: 'awal ✓',
  statusLastOk: 'akhir ✓',

  sceneTitle: (num) => `Adegan ${num}`,
  splitBadge: 'pecahan',
  splitBadgeTitle: 'Potongan dari shot yang lebih panjang',
  deepAnalyzeBtn: 'Analisis Mendalam (0.5 dtk)',
  deepAnalyzingBtn: 'Menganalisis (0.5 dtk)...',
  deepAnalyzeTitle: 'Ekstrak frame tiap 0,5 detik untuk analisis ekspresi, gestur & prompt lebih detail',
  deepAnalyzeDefaultMsg: 'Analisis mendalam berjalan (ekstrak frame 0,5 dtk & analisis detail)...',
  statusIdle: 'belum dibuat',
  statusQueue: 'dalam antrean',
  statusGenerating: 'sedang dibuat...',
  statusDone: 'selesai',
  statusFailed: 'gagal',
  firstBadgePrefix: 'Awal',
  lastBadgePrefix: 'Akhir',
  clipTitle: (num) => `Video Referensi Adegan ${num}`,
  clipPlayingDesc: 'Klip sedang diputar (ulang otomatis). Jika baru pertama dibuka, ffmpeg memotong segmen ini secara otomatis.',
  clipIdleDesc: 'Klik tombol Putar pada pemutar untuk memotong dan memutar klip asli adegan ini tanpa memuat video penuh.',
  downloadMp4: 'Unduh MP4',
  closePlayer: 'Tutup pemutar',
  playClipHint: 'Klik untuk memotong & memutar klip asli adegan ini',
  refFirst: 'Referensi Awal',
  refLast: 'Referensi Akhir',
  noLastRef: 'tidak ada frame akhir',
  cameraLabel: 'Kamera:',
  lightingLabel: 'Cahaya:',
  timelineDetailTitle: (count) => `Rincian Linimasa per 0,5 dtk (${count} bagian)`,
  actionLabel: 'Aksi:',
  expressionLabel: 'Ekspresi:',
  backgroundLabel: 'Latar:',
  replaceCharLabel: 'Ganti Karakter (pilih karakter mana yang masuk prompt sebagai tag [Char_N])',
  replaceSelectedCount: (selected, total) => `${selected}/${total} dipilih`,
  replaceDetectedCount: (total) => `${total} terdeteksi`,
  supportingCharNote: '(karakter sampingan — pakai deskripsi asli)',
  imagePromptsTitle: 'Prompt Gambar (Keyframe Awal & Akhir)',
  imagePromptsDesc: 'Salin prompt Frame Awal & Akhir ini ke Google Flow, Midjourney, Nano Banana, atau ChatGPT.',
  generateBothBtn: 'Buat Keduanya (Awal + Akhir)',
  generatingGeneric: 'Membuat...',
  firstPromptLabel: '1. Prompt Keyframe Awal',
  lastPromptLabel: '2. Prompt Keyframe Akhir',
  firstPromptPlaceholder: 'Prompt untuk gambar Frame Awal...',
  lastPromptPlaceholder: 'Prompt untuk gambar Frame Akhir...',
  analyzingPlaceholder: 'Sedang menganalisis...',
  generateFirstBtn: 'Buat Frame Awal',
  regenerateFirstBtn: 'Buat Ulang Awal',
  generatingFirstBtn: 'Membuat Awal...',
  generateLastBtn: 'Buat Frame Akhir',
  regenerateLastBtn: 'Buat Ulang Akhir',
  generatingLastBtn: 'Membuat Akhir...',
  resultFirstLabel: 'Hasil Keyframe Awal',
  resultLastLabel: 'Hasil Keyframe Akhir',
  openFull: 'Buka penuh',
  firstGenFailed: 'Pembuatan Keyframe Awal gagal',
  lastGenFailed: 'Pembuatan Keyframe Akhir gagal',
  videoPromptTitle: 'Prompt Gerakan Video (Untuk Generator Video AI)',
  videoPromptDesc: 'Salin prompt ini ke Google Flow (Omni 1.2 / Veo 3.1 Lite), Seedance, MiniMax, atau Kling bersama Frame Awal/Akhir.',
  generatePromptBtn: 'Buat Prompt',
  generatingPromptProgress: 'Menyusun Prompt Gerakan Video sesuai aturan model terpilih...',
  videoPromptPlaceholder: 'Kosong secara bawaan — pilih model target lalu klik Buat Prompt.',
  videoPromptCharStaleWarning:
    'Prompt video ini dibuat saat Replace Karakter tidak aktif atau dengan pilihan karakter berbeda. Klik Buat Prompt untuk menyusun ulang dengan tag [Char_N] sesuai pilihan saat ini.',
  videoPromptDeepStaleWarning:
    'Data Analisis Mendalam (0,5 dtk) tersedia atau diperbarui setelah prompt ini dibuat. Klik Buat Prompt untuk memasukkan detail timeline terbaru.',
  copyBtn: 'Salin',
  copiedBtn: 'Tersalin',

  settingsTitle: 'Pengaturan',
  settingsSubtitle: 'Engine CLI bawaan, durasi maksimal adegan, dan otomatisasi. Disimpan lokal di',
  loadingText: 'Memuat...',
  loadSettingsFailed: (err) => `Gagal memuat pengaturan: ${err}`,
  engineSectionTitle: 'Engine Bawaan',
  defaultAnalyzerLabel: 'Penganalisis bawaan',
  defaultModelLabel: 'Model CLI bawaan',
  defaultCliConfigOption: 'default (bawaan CLI)',
  refreshModelsBtn: 'Muat ulang daftar model',
  loadingModelsBtn: 'Memuat model...',
  fallbackAnalyzerLabel: 'Penganalisis cadangan (Fallback)',
  fallbackDisabledOption: 'Tidak ada (nonaktif)',
  fallbackModelLabel: 'Model cadangan',
  fallbackHint:
    'Jika engine utama gagal atau terkena limit kuota, Shot2Key otomatis mengulang adegan dengan engine dan model cadangan.',
  defaultImageEngineLabel: 'Engine gambar bawaan',
  maxDurationLabel: 'Maks. durasi adegan (detik)',
  maxDurationHint: 'Shot tidak pernah digabung; shot yang lebih panjang akan dipecah.',
  secondsUnit: (n) => `${n} detik`,
  reaLangLabel: 'Bahasa laporan rea-video',
  useVlmLabel: 'Pakai VLM (butuh API key Gemini di env)',
  automationSectionTitle: 'Otomatisasi & Gaya',
  autoAnalyzeLabel: 'Analisis otomatis & buat prompt gambar setelah video selesai dipecah',
  defaultStyleLabel: 'Prompt Gaya Bawaan (otomatis ditambahkan saat buat gambar)',
  saveSettingsBtn: 'Simpan Pengaturan',
  savingBtn: 'Menyimpan...',
  settingsSaved: 'Pengaturan tersimpan.',
}

const en: UIStrings = {
  appSubtitle: 'Cutroom & keyframe studio',
  navLibrary: 'Library',
  navSettings: 'Settings',
  navAriaLabel: 'Main navigation',
  langSwitchAriaLabel: 'Select interface language',
  depsIncomplete: 'Missing dependencies',
  reaNotFound: 'rea-video not found in .venv',
  ffmpegNotFound: 'ffmpeg not found',
  agyNotFound: 'agy CLI not found',
  codexNotFound: 'codex CLI not found',

  libraryTitle: 'Video Library',
  librarySubtitle: 'Upload a reference video, then open the project to manage scenes, prompts, and keyframes.',
  dropVideoTitle: 'Drop a reference video',
  dropVideoDesc: '.mp4 / .mov / .mkv — rea-video splits it by shot, and Shot2Key caps each scene at 10 seconds.',
  chooseFile: 'Choose file',
  uploading: 'Uploading...',
  recentProjects: 'Recent projects',
  noProjects: 'No projects yet.',
  deleteProjectConfirm: 'Delete this project and its video?',
  deleteProjectTitle: 'Delete project',
  deleteLabel: 'delete',
  localStorageNote: 'Videos stay local in backend/uploads/. Nothing goes to the cloud unless you pick an API engine.',
  sceneUnit: 'scenes',
  shotUnit: 'shots',

  projectNotFound: 'Project not found',
  projectNotFoundDesc: 'This project was deleted or does not exist.',
  backToLibrary: '← Back to Library',
  allProjects: '← All projects',
  analyzerLabel: 'Analyzer',
  imageEngineLabel: 'Image',
  notReady: '(not ready)',
  analyzeBtn: 'Analyze',
  analyzingBtn: 'Analyzing...',
  generateFirstAll: (count) => `Generate First All (${count})`,
  generatingAll: 'Generating...',
  logsBtn: 'Logs',
  exportZip: 'Export ZIP',
  audioReportTitle: 'Audio & Report',
  openReport: 'Open report.html',
  logsTitle: (count) => `Prompt & Response Logs (${count})`,
  closeBtn: 'Close',
  loadingLogs: 'Loading logs...',
  noLogs: 'No logs yet. Run Analyze or Generate to record prompts & responses.',
  inputImagesLabel: 'input images',
  promptSentLabel: 'prompt sent',
  rawResponseLabel: 'raw response',
  logFallbackFromLabel: 'Fallback from primary error:',
  analyzingProgress: (done, total, engine) =>
    `Analyzing & crafting prompts (${done}/${total} scenes) with ${engine}...`,
  generatingProgress: (done, total, engine) =>
    `Generating keyframes (${done}/${total}) with ${engine}...`,
  decomposeFailed: (err) => `Decompose failed: ${err}`,
  promptCountLabel: 'prompts',
  keyframeCountLabel: 'keyframes',
  partialAnalyzeWarning: 'some scenes failed to analyze',
  failedKeyframesWarning: (count) => `${count} keyframes failed`,
  subtitlesReady: '.srt subtitles ready',
  timelineTitle: (count) => `Scene Timeline (${count})`,
  showingScene: (current, total) => `Showing Scene ${String(current).padStart(2, '0')} of ${total}`,
  prevScene: '← Previous',
  nextScene: 'Next →',
  statusPromptOk: 'prompt ✓',
  statusQueued: 'queued...',
  statusEmpty: 'empty',
  statusDeep: 'deep...',
  statusFirstOk: 'first ✓',
  statusLastOk: 'last ✓',

  sceneTitle: (num) => `Scene ${num}`,
  splitBadge: 'split',
  splitBadgeTitle: 'Split from a longer shot',
  deepAnalyzeBtn: 'Deep Analyze (0.5s)',
  deepAnalyzingBtn: 'Deep Analyzing (0.5s)...',
  deepAnalyzeTitle: 'Sample frames every 0.5s for detailed expression, gesture & prompt analysis',
  deepAnalyzeDefaultMsg: 'Deep Analyze running (sampling frames every 0.5s)...',
  statusIdle: 'not generated',
  statusQueue: 'queued',
  statusGenerating: 'generating...',
  statusDone: 'done',
  statusFailed: 'failed',
  firstBadgePrefix: 'First',
  lastBadgePrefix: 'Last',
  clipTitle: (num) => `Scene ${num} Reference Video`,
  clipPlayingDesc: 'Playing scene clip (looped). On first play, ffmpeg cuts this segment on demand.',
  clipIdleDesc: 'Click Play on the player to cut and preview this scene clip without loading the full video.',
  downloadMp4: 'Download MP4',
  closePlayer: 'Close player',
  playClipHint: 'Click to cut & play this scene clip',
  refFirst: 'Reference First',
  refLast: 'Reference Last',
  noLastRef: 'no last frame',
  cameraLabel: 'Camera:',
  lightingLabel: 'Lighting:',
  timelineDetailTitle: (count) => `0.5s Timeline Breakdown (${count} beats)`,
  actionLabel: 'Action:',
  expressionLabel: 'Expression:',
  backgroundLabel: 'Background:',
  replaceCharLabel: 'Replace Characters (pick which characters keep [Char_N] tags in prompts)',
  replaceSelectedCount: (selected, total) => `${selected}/${total} selected`,
  replaceDetectedCount: (total) => `${total} detected`,
  supportingCharNote: '(supporting character — using natural description)',
  imagePromptsTitle: 'Image Prompts (First & Last Keyframe)',
  imagePromptsDesc: 'Copy these First & Last frame prompts to Google Flow, Midjourney, Nano Banana, or ChatGPT.',
  generateBothBtn: 'Generate Both (First + Last)',
  generatingGeneric: 'Generating...',
  firstPromptLabel: '1. First Keyframe Prompt',
  lastPromptLabel: '2. Last Keyframe Prompt',
  firstPromptPlaceholder: 'Prompt for First Frame image...',
  lastPromptPlaceholder: 'Prompt for Last Frame image...',
  analyzingPlaceholder: 'Analyzing...',
  generateFirstBtn: 'Generate First',
  regenerateFirstBtn: 'Regenerate First',
  generatingFirstBtn: 'Generating First...',
  generateLastBtn: 'Generate Last',
  regenerateLastBtn: 'Regenerate Last',
  generatingLastBtn: 'Generating Last...',
  resultFirstLabel: 'Generated First Keyframe',
  resultLastLabel: 'Generated Last Keyframe',
  openFull: 'Open full',
  firstGenFailed: 'First Keyframe generation failed',
  lastGenFailed: 'Last Keyframe generation failed',
  videoPromptTitle: 'Video Motion Prompt (For AI Video Generators)',
  videoPromptDesc: 'Copy this prompt to Google Flow (Omni 1.2 / Veo 3.1 Lite), Seedance, MiniMax, or Kling with your First/Last Frame.',
  generatePromptBtn: 'Generate Prompt',
  generatingPromptProgress: 'Crafting Video Motion Prompt for the selected model...',
  videoPromptPlaceholder: 'Empty by default — pick a target model and click Generate Prompt.',
  videoPromptCharStaleWarning:
    'This video prompt was generated with Replace Characters disabled or a different character selection. Click Generate Prompt to regenerate with current [Char_N] tags.',
  videoPromptDeepStaleWarning:
    'Deep Analyze (0.5s) data was added or updated after this prompt was generated. Click Generate Prompt to include the latest timeline details.',
  copyBtn: 'Copy',
  copiedBtn: 'Copied',

  settingsTitle: 'Settings',
  settingsSubtitle: 'Default CLI engines, max scene duration, and automation. Stored locally in',
  loadingText: 'Loading...',
  loadSettingsFailed: (err) => `Failed to load settings: ${err}`,
  engineSectionTitle: 'Default Engines',
  defaultAnalyzerLabel: 'Default analyzer',
  defaultModelLabel: 'Default CLI model',
  defaultCliConfigOption: 'default (CLI config)',
  refreshModelsBtn: 'Refresh models',
  loadingModelsBtn: 'Loading models...',
  fallbackAnalyzerLabel: 'Fallback analyzer (on failure)',
  fallbackDisabledOption: 'None (disabled)',
  fallbackModelLabel: 'Fallback model',
  fallbackHint:
    'If the primary analyzer fails or hits quota limits, Shot2Key automatically retries that scene with the fallback engine and model.',
  defaultImageEngineLabel: 'Default image engine',
  maxDurationLabel: 'Max scene duration (seconds)',
  maxDurationHint: 'Shots are never merged; longer shots are split evenly.',
  secondsUnit: (n) => `${n}s`,
  reaLangLabel: 'rea-video report language',
  useVlmLabel: 'Use VLM (requires Gemini API key in env)',
  automationSectionTitle: 'Automation & Style',
  autoAnalyzeLabel: 'Auto-analyze & write image prompts after video decomposition',
  defaultStyleLabel: 'Default Style Prompt (appended automatically during image generation)',
  saveSettingsBtn: 'Save Settings',
  savingBtn: 'Saving...',
  settingsSaved: 'Settings saved.',
}

export const TRANSLATIONS: Record<UILang, UIStrings> = { id, en }
export const DEFAULT_LANG: UILang = 'en'

export function readStoredLang(): UILang {
  try {
    const val = window.localStorage.getItem('shot2key_lang')
    if (val === 'id' || val === 'en') return val
    return DEFAULT_LANG
  } catch {
    return DEFAULT_LANG
  }
}

export function saveStoredLang(lang: UILang): void {
  try {
    window.localStorage.setItem('shot2key_lang', lang)
  } catch {
    /* ignore storage failures */
  }
}
