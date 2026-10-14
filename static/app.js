/**
 * KCapTrack — Frontend Application Logic
 * Client-side state, YOLO Canvas visualizer, Mifflin-St Jeor engine, and REST API integration.
 */

const API_BASE = '/api/v1';

// ── Application State ──────────────────────────────────────────────────────────
const state = {
  token: localStorage.getItem('kcap_token') || null,
  user: JSON.parse(localStorage.getItem('kcap_user') || 'null'),
  currentImageBlob: null,
  currentImageBitmap: null,
  lastDetections: [],
  biometrics: {
    age: 26,
    gender: 'male',
    height_cm: 180,
    weight_kg: 75.0,
    activity_level: 'moderately_active',
    goal: 'cut',
    bmr: 1745,
    tdee: 2705,
    target_calories: 2164,
    target_protein_g: 189,
    target_fat_g: 72,
    target_carbs_g: 189,
  },
  dailySummary: {
    calories: { consumed: 0, target: 2164, percentage: 0 },
    protein: { consumed: 0, target: 189, percentage: 0 },
    fat: { consumed: 0, target: 72, percentage: 0 },
    carbs: { consumed: 0, target: 189, percentage: 0 },
    meal_count: 0,
  }
};

// ── Toast Notifications ──────────────────────────────────────────────────────
function showToast(message, type = 'info') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  
  const icon = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';
  toast.innerHTML = `<span style="font-weight:700;">${icon}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

// ── Authentication & Bootstrapping ───────────────────────────────────────────
async function ensureAuthenticated() {
  if (state.token && state.user) {
    updateUserUI();
    return;
  }

  // Auto-provision demo account for zero-friction evaluation
  try {
    const demoUsername = 'demo_athlete';
    const demoEmail = 'demo@kcaptrack.io';
    const demoPassword = 'DemoPassword123!';

    // Try login first
    let res = await fetch(`${API_BASE}/users/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: demoUsername, password: demoPassword }),
    });

    if (!res.ok) {
      // Register demo user
      await fetch(`${API_BASE}/users/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: demoUsername, email: demoEmail, password: demoPassword }),
      });
      res = await fetch(`${API_BASE}/users/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: demoUsername, password: demoPassword }),
      });
    }

    if (res.ok) {
      const data = await res.json();
      state.token = data.access_token;
      state.user = { username: demoUsername, email: demoEmail };
      localStorage.setItem('kcap_token', state.token);
      localStorage.setItem('kcap_user', JSON.stringify(state.user));
      updateUserUI();
    }
  } catch (err) {
    console.warn('Demo authentication bootstrap:', err);
  }
}

function updateUserUI() {
  const nameEl = document.getElementById('navUsername');
  const avatarEl = document.getElementById('userAvatar');
  if (state.user) {
    nameEl.textContent = state.user.username;
    avatarEl.textContent = state.user.username.charAt(0).toUpperCase();
  }
}

function authHeaders() {
  return state.token ? { 'Authorization': `Bearer ${state.token}` } : {};
}

// ── Tab Navigation ───────────────────────────────────────────────────────────
function initNavigation() {
  const tabs = document.querySelectorAll('.nav-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');

      const targetView = tab.getAttribute('data-tab');
      document.querySelectorAll('.view-section').forEach(view => {
        view.classList.remove('active');
      });

      const activeView = document.getElementById(`view${targetView.charAt(0).toUpperCase() + targetView.slice(1)}`);
      if (activeView) activeView.classList.add('active');

      if (targetView === 'dashboard') loadDashboardSummary();
      if (targetView === 'history') loadMealHistory();
    });
  });
}

// ── Mifflin-St Jeor Biometrics Engine (Client & Server) ──────────────────────
const ACTIVITY_FACTORS = {
  sedentary: 1.20,
  lightly_active: 1.375,
  moderately_active: 1.55,
  very_active: 1.725,
  extra_active: 1.90,
};

const GOAL_FACTORS = {
  cut: 0.80,
  maintain: 1.00,
  bulk: 1.15,
};

const MACRO_SPLITS = {
  cut: { p: 0.35, f: 0.30, c: 0.35 },
  maintain: { p: 0.30, f: 0.25, c: 0.45 },
  bulk: { p: 0.25, f: 0.25, c: 0.50 },
};

function calculateLiveBiometrics() {
  const age = parseInt(document.getElementById('bioAge').value, 10);
  const gender = document.getElementById('bioGender').value;
  const height = parseFloat(document.getElementById('bioHeight').value);
  const weight = parseFloat(document.getElementById('bioWeight').value);
  const activity = document.getElementById('bioActivity').value;
  const goal = document.querySelector('input[name="fitness_goal"]:checked')?.value || 'cut';

  // Label value updates
  document.getElementById('ageVal').textContent = `${age} yrs`;
  document.getElementById('heightVal').textContent = `${height} cm`;
  document.getElementById('weightVal').textContent = `${weight.toFixed(1)} kg`;

  // BMI = kg / (m^2)
  const heightM = height / 100.0;
  const bmi = weight / (heightM * heightM);
  document.getElementById('calcBmi').textContent = bmi.toFixed(1);

  let bmiCat = 'Normal Weight';
  if (bmi < 18.5) bmiCat = 'Underweight';
  else if (bmi >= 25 && bmi < 30) bmiCat = 'Overweight';
  else if (bmi >= 30) bmiCat = 'Obese';
  document.getElementById('calcBmiCat').textContent = bmiCat;

  // BMR (Mifflin-St Jeor)
  const base = (10 * weight) + (6.25 * height) - (5 * age);
  const bmr = Math.round(gender === 'male' ? base + 5 : base - 161);
  document.getElementById('calcBmr').textContent = bmr.toLocaleString();

  // TDEE
  const actMultiplier = ACTIVITY_FACTORS[activity] || 1.55;
  const tdee = Math.round(bmr * actMultiplier);
  document.getElementById('calcTdee').textContent = tdee.toLocaleString();

  // Target Calories & Macros
  const goalMultiplier = GOAL_FACTORS[goal] || 1.0;
  const targetCal = Math.round(tdee * goalMultiplier);
  document.getElementById('calcTargetCal').textContent = targetCal.toLocaleString();

  const split = MACRO_SPLITS[goal] || MACRO_SPLITS.cut;
  const targetPro = Math.round((targetCal * split.p) / 4.0);
  const targetFat = Math.round((targetCal * split.f) / 9.0);
  const targetCarb = Math.round((targetCal * split.c) / 4.0);

  document.getElementById('calcTargetPro').textContent = `${targetPro}g`;
  document.getElementById('calcTargetFat').textContent = `${targetFat}g`;
  document.getElementById('calcTargetCarb').textContent = `${targetCarb}g`;

  // Update Hero & Ratio bars
  document.getElementById('heroCalTarget').textContent = targetCal.toLocaleString();
  document.getElementById('heroGoalBadge').textContent = goal.toUpperCase();
  document.getElementById('barProPct').textContent = `${Math.round(split.p * 100)}%`;
  document.getElementById('barFatPct').textContent = `${Math.round(split.f * 100)}%`;
  document.getElementById('barCarbPct').textContent = `${Math.round(split.c * 100)}%`;
  document.getElementById('ratioBarPro').style.width = `${split.p * 100}%`;
  document.getElementById('ratioBarFat').style.width = `${split.f * 100}%`;
  document.getElementById('ratioBarCarb').style.width = `${split.c * 100}%`;

  return { age, gender, height_cm: height, weight_kg: weight, activity_level: activity, goal };
}

async function saveBiometricProfile() {
  const payload = calculateLiveBiometrics();
  try {
    const res = await fetch(`${API_BASE}/users/profile`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
      },
      body: JSON.stringify(payload),
    });

    if (res.ok) {
      showToast('Biometric profile & daily targets updated!', 'success');
      loadDashboardSummary();
    } else {
      const err = await res.json();
      showToast(err.detail || 'Could not save profile', 'error');
    }
  } catch (err) {
    showToast('Network error saving profile', 'error');
  }
}

// ── Dashboard Rings & Progress ───────────────────────────────────────────────
function updateRing(circleId, percent) {
  const circle = document.getElementById(circleId);
  if (!circle) return;
  const radius = 40;
  const circumference = 2 * Math.PI * radius; // ~251.2
  const clamped = Math.min(Math.max(percent, 0), 100);
  const offset = circumference - (clamped / 100) * circumference;
  circle.style.strokeDasharray = `${circumference}`;
  circle.style.strokeDashoffset = `${offset}`;
}

async function loadDashboardSummary() {
  try {
    const res = await fetch(`${API_BASE}/dashboard/summary`, {
      headers: authHeaders(),
    });
    if (!res.ok) return;

    const data = await res.json();
    state.dailySummary = data;

    // Calories
    const cal = data.calories || {};
    document.getElementById('dashCalConsumed').textContent = Math.round(cal.consumed || 0);
    document.getElementById('dashCalTarget').textContent = Math.round(cal.target || 2000);
    document.getElementById('dashCalRem').textContent = `${Math.max(0, Math.round(cal.remaining || 0))} left`;
    document.getElementById('ringCalPercent').textContent = `${Math.round(cal.percentage || 0)}%`;
    document.getElementById('heroCalRemaining').textContent = Math.max(0, Math.round(cal.remaining || 0)).toLocaleString();
    updateRing('ringCalories', cal.percentage || 0);

    // Protein
    const pro = data.protein || {};
    document.getElementById('dashProConsumed').textContent = Math.round(pro.consumed || 0);
    document.getElementById('dashProTarget').textContent = Math.round(pro.target || 175);
    document.getElementById('dashProRem').textContent = `${Math.max(0, Math.round(pro.remaining || 0))}g left`;
    document.getElementById('ringProPercent').textContent = `${Math.round(pro.percentage || 0)}%`;
    updateRing('ringProtein', pro.percentage || 0);

    // Fat
    const fat = data.fat || {};
    document.getElementById('dashFatConsumed').textContent = Math.round(fat.consumed || 0);
    document.getElementById('dashFatTarget').textContent = Math.round(fat.target || 67);
    document.getElementById('dashFatRem').textContent = `${Math.max(0, Math.round(fat.remaining || 0))}g left`;
    document.getElementById('ringFatPercent').textContent = `${Math.round(fat.percentage || 0)}%`;
    updateRing('ringFat', fat.percentage || 0);

    // Carbs
    const carb = data.carbs || {};
    document.getElementById('dashCarbConsumed').textContent = Math.round(carb.consumed || 0);
    document.getElementById('dashCarbTarget').textContent = Math.round(carb.target || 175);
    document.getElementById('dashCarbRem').textContent = `${Math.max(0, Math.round(carb.remaining || 0))}g left`;
    document.getElementById('ringCarbPercent').textContent = `${Math.round(carb.percentage || 0)}%`;
    updateRing('ringCarbs', carb.percentage || 0);

    // Meal Count Badge
    document.getElementById('dashMealCount').textContent = `${data.meal_count || 0} Meals Logged`;
  } catch (err) {
    console.warn('Dashboard summary error:', err);
  }
}

// ── Input Modes & Scanner Studio ─────────────────────────────────────────────
let cameraStream = null;
let knownFoodsList = [];

function initInputModes() {
  const tabs = document.querySelectorAll('.mode-tab');
  const panels = {
    upload: document.getElementById('uploadMode'),
    camera: document.getElementById('cameraMode'),
    manual: document.getElementById('manualMode'),
  };

  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const mode = tab.dataset.mode;
      Object.keys(panels).forEach(k => {
        if (panels[k]) panels[k].style.display = (k === mode) ? 'block' : 'none';
      });

      // Stop camera feed if switching away
      if (mode !== 'camera' && cameraStream) {
        stopCamera();
      }
    });
  });
}

function stopCamera() {
  if (cameraStream) {
    cameraStream.getTracks().forEach(t => t.stop());
    cameraStream = null;
  }
  const video = document.getElementById('cameraFeed');
  const placeholder = document.getElementById('cameraPlaceholder');
  const snapBtn = document.getElementById('snapPhotoBtn');
  const stopBtn = document.getElementById('stopCameraBtn');
  if (video) video.style.display = 'none';
  if (placeholder) placeholder.style.display = 'block';
  if (snapBtn) snapBtn.style.display = 'none';
  if (stopBtn) stopBtn.style.display = 'none';
}

function initCamera() {
  const startBtn = document.getElementById('startCameraBtn');
  const snapBtn = document.getElementById('snapPhotoBtn');
  const retakeBtn = document.getElementById('retakePhotoBtn');
  const stopBtn = document.getElementById('stopCameraBtn');
  const video = document.getElementById('cameraFeed');
  const canvas = document.getElementById('cameraCanvas');
  const placeholder = document.getElementById('cameraPlaceholder');

  if (!startBtn) return;

  startBtn.addEventListener('click', async () => {
    try {
      cameraStream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: { ideal: 'environment' }, width: { ideal: 1280 } }
      });
      video.srcObject = cameraStream;
      video.style.display = 'block';
      placeholder.style.display = 'none';
      snapBtn.style.display = 'inline-flex';
      stopBtn.style.display = 'inline-flex';
      retakeBtn.style.display = 'none';
      showToast('Camera active! Point at your food dish and click Snap Photo.', 'info');
    } catch (err) {
      console.warn('Camera access denied/unavailable:', err);
      showToast('Could not access camera (' + (err.name || 'check permissions') + ')', 'error');
    }
  });

  snapBtn.addEventListener('click', () => {
    if (!video.videoWidth) {
      showToast('Camera stream is initializing, please wait a second', 'info');
      return;
    }
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

    canvas.toBlob((blob) => {
      const file = new File([blob], 'camera_meal.jpg', { type: 'image/jpeg' });
      stopCamera();
      handleImageSelected(file);
      showToast('Photo captured! Click "Analyze Food" to scan.', 'success');
    }, 'image/jpeg', 0.92);
  });

  stopBtn.addEventListener('click', stopCamera);
}

async function loadFoodSuggestions() {
  try {
    const res = await fetch(`${API_BASE}/meals/foods`);
    if (res.ok) {
      knownFoodsList = await res.json();
      const datalist = document.getElementById('foodSuggestions');
      if (datalist) {
        datalist.innerHTML = knownFoodsList.map(f => 
          `<option value="${f.name}">${f.calories_per_100g} kcal/100g • ${f.protein_per_100g}g P • ${f.carbs_per_100g}g C</option>`
        ).join('');
      }
    }
  } catch (err) {
    console.warn('Could not load food list for autocomplete:', err);
  }
}

function updateManualPreview() {
  const foodName = (document.getElementById('manualFoodName')?.value || '').trim().toLowerCase();
  const grams = parseFloat(document.getElementById('manualPortion')?.value || '150') || 150;

  const match = knownFoodsList.find(f => 
    f.name.toLowerCase() === foodName || 
    (f.yolo_class_name && f.yolo_class_name.toLowerCase() === foodName)
  );

  if (match) {
    const factor = grams / 100.0;
    document.getElementById('previewCal').textContent = Math.round(match.calories_per_100g * factor);
    document.getElementById('previewPro').textContent = Math.round(match.protein_per_100g * factor) + 'g';
    document.getElementById('previewFat').textContent = Math.round(match.fat_per_100g * factor) + 'g';
    document.getElementById('previewCarb').textContent = Math.round(match.carbs_per_100g * factor) + 'g';
  } else {
    document.getElementById('previewCal').textContent = '—';
    document.getElementById('previewPro').textContent = '—';
    document.getElementById('previewFat').textContent = '—';
    document.getElementById('previewCarb').textContent = '—';
  }
}

function initManualEntry() {
  const nameInput = document.getElementById('manualFoodName');
  const portionInput = document.getElementById('manualPortion');
  const logBtn = document.getElementById('logManualBtn');

  if (!nameInput || !logBtn) return;

  nameInput.addEventListener('input', updateManualPreview);
  nameInput.addEventListener('change', updateManualPreview);
  portionInput.addEventListener('input', updateManualPreview);

  logBtn.addEventListener('click', async () => {
    const foodName = nameInput.value.trim();
    const portionG = parseFloat(portionInput.value || '150');
    const mealType = document.getElementById('scanMealType').value;

    if (!foodName) {
      showToast('Please type a food name (e.g. Dosa, Pizza, Chicken Breast)', 'error');
      nameInput.focus();
      return;
    }

    logBtn.disabled = true;
    logBtn.textContent = 'Logging...';

    try {
      const res = await fetch(`${API_BASE}/meals/log-manual`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders(),
        },
        body: JSON.stringify({
          food_name: foodName,
          portion_g: portionG,
          meal_type: mealType,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        showToast(err.detail || 'Failed to log manual entry', 'error');
        return;
      }

      const log = await res.json();
      showToast(`Logged ${log.detected_class} (${Math.round(log.calories)} kcal) to ${mealType.toUpperCase()}!`, 'success');
      nameInput.value = '';
      updateManualPreview();
      loadDashboardSummary();
      loadMealHistory();
    } catch (err) {
      showToast('Network error logging manual food', 'error');
    } finally {
      logBtn.disabled = false;
      logBtn.textContent = '+ Log This Food';
    }
  });
}

function initGeminiKeyModal() {
  const modal = document.getElementById('apiKeyModal');
  const openBtn = document.getElementById('apiKeyModalBtn');
  const closeBtn = document.getElementById('closeApiKeyModalBtn');
  const saveBtn = document.getElementById('saveApiKeyBtn');
  const clearBtn = document.getElementById('clearApiKeyBtn');
  const input = document.getElementById('geminiApiKeyInput');
  const dot = document.getElementById('geminiKeyStatusDot');
  const text = document.getElementById('geminiKeyBtnText');

  if (!modal || !openBtn) return;

  function updateKeyBadge() {
    const key = localStorage.getItem('kcap_gemini_key');
    if (key && key.trim()) {
      if (dot) {
        dot.style.background = '#10b981';
        dot.style.boxShadow = '0 0 8px rgba(16, 185, 129, 0.8)';
      }
      if (text) text.textContent = '✨ Gemini Active';
      openBtn.style.borderColor = 'rgba(16, 185, 129, 0.5)';
      openBtn.style.background = 'rgba(16, 185, 129, 0.08)';
    } else {
      if (dot) {
        dot.style.background = '#a855f7';
        dot.style.boxShadow = '0 0 6px rgba(168, 85, 247, 0.6)';
      }
      if (text) text.textContent = '⚡ Enable AI Vision (Free)';
      openBtn.style.borderColor = 'rgba(168, 85, 247, 0.6)';
      openBtn.style.background = 'rgba(168, 85, 247, 0.12)';
    }
  }

  updateKeyBadge();

  openBtn.addEventListener('click', () => {
    input.value = localStorage.getItem('kcap_gemini_key') || '';
    modal.classList.add('active');
  });

  closeBtn?.addEventListener('click', () => modal.classList.remove('active'));
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('active');
  });

  saveBtn?.addEventListener('click', () => {
    const val = input.value.trim();
    if (val) {
      localStorage.setItem('kcap_gemini_key', val);
      showToast('Gemini API key saved! Accurate food detection enabled.', 'success');
    } else {
      localStorage.removeItem('kcap_gemini_key');
      showToast('Gemini key removed. Reverting to offline YOLO model.', 'info');
    }
    updateKeyBadge();
    modal.classList.remove('active');
  });

  clearBtn?.addEventListener('click', () => {
    localStorage.removeItem('kcap_gemini_key');
    input.value = '';
    updateKeyBadge();
    showToast('Gemini key cleared.', 'info');
    modal.classList.remove('active');
  });
}

// ── YOLO Scanner & Canvas Rendering ──────────────────────────────────────────
function initScanner() {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('mealFileInput');
  const browseBtn = document.getElementById('browseBtn');
  const resetBtn = document.getElementById('resetScanBtn');
  const inferBtn = document.getElementById('runInferenceBtn');

  browseBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    fileInput.click();
  });

  dropzone.addEventListener('click', () => fileInput.click());

  dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
  });

  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));

  dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      handleImageSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length) {
      handleImageSelected(fileInput.files[0]);
    }
  });

  resetBtn.addEventListener('click', resetScanStage);
  inferBtn.addEventListener('click', runYoloScan);

  // Sample pill handlers
  document.querySelectorAll('.sample-pill').forEach(pill => {
    pill.addEventListener('click', (e) => {
      e.stopPropagation();
      loadSyntheticSampleFood(pill.getAttribute('data-sample'));
    });
  });

  initInputModes();
  initCamera();
  initManualEntry();
  initGeminiKeyModal();
  loadFoodSuggestions();
}

function handleImageSelected(file) {
  state.currentImageBlob = file;
  const reader = new FileReader();
  reader.onload = (e) => {
    const img = new Image();
    img.onload = () => {
      state.currentImageBitmap = img;
      renderImageToCanvas(img);
      document.querySelectorAll('.input-mode-panel').forEach(p => p.style.display = 'none');
      document.getElementById('inputModeTabs').style.display = 'none';
      document.getElementById('scanStage').style.display = 'block';
      document.getElementById('scanImageMeta').textContent = `${file.name || 'image'} (${img.naturalWidth}×${img.naturalHeight}px)`;
    };
    img.src = e.target.result;
  };
  reader.readAsDataURL(file);
}

function renderImageToCanvas(img, detections = []) {
  const canvas = document.getElementById('scanCanvas');
  const ctx = canvas.getContext('2d');

  canvas.width = img.naturalWidth || img.width;
  canvas.height = img.naturalHeight || img.height;

  // Draw photo
  ctx.drawImage(img, 0, 0);

  // Draw YOLO / Gemini bounding boxes
  detections.forEach(det => {
    if (!det.bbox || det.bbox.length < 4) return;
    const [x1, y1, x2, y2] = det.bbox;
    const w = x2 - x1;
    const h = y2 - y1;

    // Glowing BBox border
    ctx.lineWidth = Math.max(3, Math.round(canvas.width / 250));
    ctx.strokeStyle = '#10b981';
    ctx.shadowColor = 'rgba(16, 185, 129, 0.8)';
    ctx.shadowBlur = 12;
    ctx.strokeRect(x1, y1, w, h);
    ctx.shadowBlur = 0;

    // Soft fill overlay
    ctx.fillStyle = 'rgba(16, 185, 129, 0.12)';
    ctx.fillRect(x1, y1, w, h);

    // Label Badge
    const label = `${det.detected_class.toUpperCase()} ${Math.round(det.confidence * 100)}% • ${Math.round(det.portion_g)}g`;
    const fontSize = Math.max(14, Math.round(canvas.width / 45));
    ctx.font = `bold ${fontSize}px Inter, sans-serif`;
    const textMetrics = ctx.measureText(label);
    const badgeW = textMetrics.width + 16;
    const badgeH = fontSize + 10;

    ctx.fillStyle = 'rgba(18, 26, 43, 0.9)';
    ctx.fillRect(x1, Math.max(0, y1 - badgeH - 4), badgeW, badgeH);

    ctx.fillStyle = '#10b981';
    ctx.fillRect(x1, Math.max(0, y1 - badgeH - 4), 4, badgeH);

    ctx.fillStyle = '#ffffff';
    ctx.fillText(label, x1 + 10, Math.max(badgeH - 4, y1 - 8));
  });
}

function resetScanStage() {
  state.currentImageBlob = null;
  state.currentImageBitmap = null;
  state.lastDetections = [];
  document.getElementById('inputModeTabs').style.display = 'flex';
  const activeTab = document.querySelector('.mode-tab.active')?.dataset.mode || 'upload';
  document.querySelectorAll('.input-mode-panel').forEach(p => p.style.display = 'none');
  const activePanel = document.getElementById(activeTab + 'Mode');
  if (activePanel) activePanel.style.display = 'block';

  document.getElementById('scanStage').style.display = 'none';
  document.getElementById('mealTotalsBanner').style.display = 'none';
  document.getElementById('detectionSubtitle').textContent = 'Upload or snap a photo to see detected items';
  document.getElementById('detectionCountBadge').textContent = '0 Items';
  document.getElementById('detectionsList').innerHTML = `
    <div style="text-align:center; padding:50px 20px; color:var(--text-dim); font-size:14px;">
      No scan results yet. Drop an image, snap with camera, or select a demo dish.
    </div>
  `;
}

// ── Synthetic Demo Food Generator ───────────────────────────────────────────
function loadSyntheticSampleFood(foodType) {
  const canvas = document.createElement('canvas');
  canvas.width = 640;
  canvas.height = 480;
  const ctx = canvas.getContext('2d');

  // Dining table background
  const grad = ctx.createRadialGradient(320, 240, 50, 320, 240, 350);
  grad.addColorStop(0, '#2d3748');
  grad.addColorStop(1, '#1a202c');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 640, 480);

  // White Plate
  ctx.beginPath();
  ctx.arc(320, 240, 190, 0, Math.PI * 2);
  ctx.fillStyle = '#edf2f7';
  ctx.shadowColor = 'rgba(0, 0, 0, 0.4)';
  ctx.shadowBlur = 25;
  ctx.fill();
  ctx.shadowBlur = 0;

  // Inner Plate Rim
  ctx.beginPath();
  ctx.arc(320, 240, 160, 0, Math.PI * 2);
  ctx.strokeStyle = '#cbd5e0';
  ctx.lineWidth = 3;
  ctx.stroke();

  // Food Item representation
  ctx.font = '120px sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const emojiMap = {
    apple: '🍎',
    banana: '🍌',
    pizza: '🍕',
    broccoli: '🥦',
    sandwich: '🥪',
  };

  ctx.fillText(emojiMap[foodType] || '🍲', 320, 240);

  canvas.toBlob((blob) => {
    const file = new File([blob], `${foodType}_demo.jpg`, { type: 'image/jpeg' });
    handleImageSelected(file);
    showToast(`Loaded sample ${foodType}! Click "Analyze Food" to scan`, 'info');
  }, 'image/jpeg');
}

// ── Run Meal Scan (Gemini Vision or YOLO Fallback) ───────────────────────────
async function runYoloScan() {
  if (!state.currentImageBlob) {
    showToast('Please select or capture a photo first', 'error');
    return;
  }

  const inferBtn = document.getElementById('runInferenceBtn');
  const spinner = document.getElementById('inferSpinner');
  inferBtn.disabled = true;
  spinner.style.display = 'inline';

  const mealType = document.getElementById('scanMealType').value;
  const formData = new FormData();
  formData.append('image', state.currentImageBlob, 'meal.jpg');
  formData.append('file', state.currentImageBlob, 'meal.jpg');
  formData.append('meal_type', mealType);

  const geminiKey = (localStorage.getItem('kcap_gemini_key') || '').trim();
  if (geminiKey) {
    formData.append('gemini_key', geminiKey);
  }

  try {
    const res = await fetch(`${API_BASE}/meals/scan`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      showToast(err.detail || 'Inference error', 'error');
      // If 422 (no food detected) and no Gemini key is active, suggest Gemini key
      if (res.status === 422 && !geminiKey) {
        setTimeout(() => {
          document.getElementById('apiKeyModal')?.classList.add('active');
        }, 1200);
      }
      return;
    }

    const data = await res.json();
    state.lastDetections = data.detections || [];

    // Redraw canvas with neon bounding boxes if available
    if (state.currentImageBitmap) {
      renderImageToCanvas(state.currentImageBitmap, state.lastDetections);
    }

    renderDetectionResults(data);
    const count = data.detected_count || state.lastDetections.length;
    showToast(`Detected ${count} food item(s) & logged to database!`, 'success');
    loadDashboardSummary();
    loadMealHistory();
  } catch (err) {
    showToast('Failed to reach backend inference service', 'error');
  } finally {
    inferBtn.disabled = false;
    spinner.style.display = 'none';
  }
}

function renderDetectionResults(scanData) {
  const listEl = document.getElementById('detectionsList');
  const totalsBanner = document.getElementById('mealTotalsBanner');
  const countBadge = document.getElementById('detectionCountBadge');
  const subTitle = document.getElementById('detectionSubtitle');

  countBadge.textContent = `${scanData.detected_count} Item(s)`;
  subTitle.textContent = `Scanned at ${new Date().toLocaleTimeString()}`;

  // Totals banner
  totalsBanner.style.display = 'block';
  document.getElementById('scanTotalCal').textContent = Math.round(scanData.total_calories || 0);
  document.getElementById('scanTotalPro').textContent = `${Math.round(scanData.total_protein_g || 0)}g`;
  document.getElementById('scanTotalFat').textContent = `${Math.round(scanData.total_fat_g || 0)}g`;
  document.getElementById('scanTotalCarb').textContent = `${Math.round(scanData.total_carbs_g || 0)}g`;

  const hasGemini = Boolean((localStorage.getItem('kcap_gemini_key') || '').trim());
  const tipBanner = !hasGemini ? `
    <div style="background:rgba(168, 85, 247, 0.08); border:1px solid rgba(168, 85, 247, 0.28); border-radius:10px; padding:12px 16px; margin-bottom:14px; font-size:12px; line-height:1.5;">
      <div style="font-weight:700; color:var(--text-main); margin-bottom:4px; display:flex; align-items:center; gap:6px;">
        <span>✨</span> Scanning Indian or Regional Dishes (Dosa, Sambar, Chutney)?
      </div>
      <div style="color:var(--text-muted); margin-bottom:8px;">
        The offline YOLO model only knows 10 basic western objects (which is why it guesses Sandwich/Banana). Connect your free Gemini key to recognize <b>Dosa, Idli, Sambar, and Chutney</b> accurately!
      </div>
      <button type="button" class="btn btn-primary" style="padding:4px 12px; font-size:11px;" onclick="document.getElementById('apiKeyModal').classList.add('active')">
        ⚡ Activate Free Gemini AI Vision ↗
      </button>
    </div>
  ` : '';

  if (!scanData.detections || scanData.detections.length === 0) {
    listEl.innerHTML = tipBanner + `
      <div style="text-align:center; padding:40px 20px; color:var(--text-muted); font-size:14px;">
        🔍 No food items recognized with current confidence threshold. Try another angle or enable AI Vision!
      </div>
    `;
    return;
  }

  listEl.innerHTML = tipBanner + scanData.detections.map(det => `
    <div class="detection-item">
      <div class="detection-info">
        <div class="detection-title">
          <span>${det.detected_class}</span>
          <span class="confidence-tag">${Math.round(det.confidence * 100)}% Match</span>
        </div>
        <div class="detection-meta">
          Estimated Portion: <b>${Math.round(det.portion_g)}g</b> ${det.portion_meta ? `• <span style="color:var(--primary-light); font-weight:600;">${det.portion_meta}</span>` : '(Area Heuristic)'}
        </div>
      </div>
      <div class="detection-macros">
        <div class="macro-chip">
          <span class="macro-chip-val" style="color:var(--color-calories);">${Math.round(det.calories)}</span>
          <span class="macro-chip-label">kcal</span>
        </div>
        <div class="macro-chip">
          <span class="macro-chip-val" style="color:var(--color-protein);">${Math.round(det.protein_g)}g</span>
          <span class="macro-chip-label">Pro</span>
        </div>
        <div class="macro-chip">
          <span class="macro-chip-val" style="color:var(--color-fat);">${Math.round(det.fat_g)}g</span>
          <span class="macro-chip-label">Fat</span>
        </div>
        <div class="macro-chip">
          <span class="macro-chip-val" style="color:var(--color-carbs);">${Math.round(det.carbs_g)}g</span>
          <span class="macro-chip-label">Carb</span>
        </div>
      </div>
    </div>
  `).join('');
}

// ── Historical Meal Logs ─────────────────────────────────────────────────────
async function loadMealHistory() {
  const dateInput = document.getElementById('historyDateInput');
  const targetDate = dateInput.value || new Date().toISOString().split('T')[0];
  dateInput.value = targetDate;

  const historyList = document.getElementById('historyList');
  historyList.innerHTML = `<div class="meal-history-empty">Loading logs for ${targetDate}...</div>`;

  try {
    const res = await fetch(`${API_BASE}/meals/logs?log_date=${targetDate}`, {
      headers: authHeaders(),
    });
    if (!res.ok) {
      historyList.innerHTML = `<div class="meal-history-empty">Could not load meal logs.</div>`;
      return;
    }

    const logs = await res.json();
    if (!logs || logs.length === 0) {
      historyList.innerHTML = `<div class="meal-history-empty">No meal logs recorded for ${targetDate}.</div>`;
      return;
    }

    historyList.innerHTML = logs.map(log => `
      <div class="meal-row">
        <div>
          <div style="font-weight:700; font-size:15px; display:flex; align-items:center; gap:8px;">
            <span>🍽️</span> ${log.food_name}
            <span class="brand-badge" style="font-size:10px;">${(log.meal_type || 'meal').toUpperCase()}</span>
          </div>
          <div style="font-size:12px; color:var(--text-muted); margin-top:2px;">
            Portion: <b>${Math.round(log.portion_g)}g</b> • Confidence: <b>${Math.round((log.confidence || 1) * 100)}%</b>
          </div>
        </div>
        <div style="display:flex; gap:16px; text-align:right;">
          <div>
            <div style="font-weight:800; font-size:15px; color:var(--color-calories);">${Math.round(log.calories)}</div>
            <div style="font-size:10px; color:var(--text-dim);">KCAL</div>
          </div>
          <div>
            <div style="font-weight:800; font-size:15px; color:var(--color-protein);">${Math.round(log.protein_g)}g</div>
            <div style="font-size:10px; color:var(--text-dim);">PRO</div>
          </div>
          <div>
            <div style="font-weight:800; font-size:15px; color:var(--color-fat);">${Math.round(log.fat_g)}g</div>
            <div style="font-size:10px; color:var(--text-dim);">FAT</div>
          </div>
          <div>
            <div style="font-weight:800; font-size:15px; color:var(--color-carbs);">${Math.round(log.carbs_g)}g</div>
            <div style="font-size:10px; color:var(--text-dim);">CARB</div>
          </div>
        </div>
      </div>
    `).join('');
  } catch (err) {
    historyList.innerHTML = `<div class="meal-history-empty">Network error loading logs.</div>`;
  }
}

// ── Check Server Health Ping ─────────────────────────────────────────────────
async function checkServerHealth() {
  const dot = document.getElementById('statusDot');
  const text = document.getElementById('statusText');
  try {
    const res = await fetch('/health');
    if (res.ok) {
      dot.className = 'status-dot online';
      text.textContent = 'Connected';
    } else {
      dot.className = 'status-dot';
      text.textContent = 'Server Busy';
    }
  } catch {
    dot.className = 'status-dot';
    text.textContent = 'Disconnected';
  }
}

// ── Initialization on DOM Ready ──────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  initNavigation();
  initScanner();

  // Biometric form listeners
  ['bioAge', 'bioHeight', 'bioWeight', 'bioGender', 'bioActivity'].forEach(id => {
    document.getElementById(id).addEventListener('input', calculateLiveBiometrics);
  });
  document.querySelectorAll('input[name="fitness_goal"]').forEach(r => {
    r.addEventListener('change', calculateLiveBiometrics);
  });
  document.getElementById('saveBiometricsBtn').addEventListener('click', saveBiometricProfile);

  // Date picker listener
  const dateInput = document.getElementById('historyDateInput');
  dateInput.value = new Date().toISOString().split('T')[0];
  dateInput.addEventListener('change', loadMealHistory);

  // Initial calculations & authentication
  calculateLiveBiometrics();
  await ensureAuthenticated();
  checkServerHealth();
  loadDashboardSummary();
  setInterval(checkServerHealth, 30000);
});
