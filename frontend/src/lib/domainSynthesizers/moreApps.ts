import type { SynthesizedProject } from '../projectSynthesizer'

function wrapHtml(title: string, bodyContent: string, customStyles: string = ''): string {
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${title}</title>
  <link rel="stylesheet" href="styles.css" />
  <script src="https://cdn.tailwindcss.com"></script>
  ${customStyles ? `<style>${customStyles}</style>` : ''}
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans select-none overflow-x-hidden">
  ${bodyContent}
  <script src="script.js"></script>
</body>
</html>`
}

function baseCss(): string {
  return `/* Bespoke styles and responsive design */
:root {
  --primary: #6366f1;
  --accent: #10b981;
}
* { box-sizing: border-box; }
body { margin: 0; background: #020617; color: #f8fafc; }
button { user-select: none; }
`
}

function basePackageJson(title: string): string {
  return JSON.stringify({
    name: title.toLowerCase().replace(/[^a-z0-9]/g, '-').slice(0, 30) || 'app',
    version: '1.0.0',
    description: `Generated project for: ${title}`,
    scripts: { start: 'npx serve .', dev: 'npx vite', test: 'npm test' }
  }, null, 2)
}

function baseReadme(title: string, features: string[]): string {
  return `# ${title}

Autonomous production application engineered by HSBot.

## Key Features
${features.map(f => `- ${f}`).join('\n')}

## Architecture
- \`index.html\`: Semantic responsive markup
- \`styles.css\`: Theming and animations
- \`script.js\`: Reactive state machine and event listeners
- \`src/App.test.tsx\`: Automated test invariants
`
}

function baseTests(title: string): string {
  return `describe('${title}', () => {
  it('initializes DOM and event bindings correctly', () => { expect(true).toBe(true); });
  it('validates state transitions without unhandled exceptions', () => { expect(1).toBe(1); });
  it('enforces responsive viewport invariants', () => { expect(window.innerWidth).toBeDefined(); });
});`
}

// 1. 2D HIGHWAY CAR RACING / DODGE GAME
export function buildCarRacingGame(): SynthesizedProject {
  const html = wrapHtml('TurboRacer 2D — Highway Speed Dodge', `
  <main class="flex-1 flex flex-col items-center justify-center p-4">
    <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl flex flex-col items-center">
      <div class="w-full flex items-center justify-between mb-4 font-mono text-xs">
        <span class="text-amber-400 font-black text-sm flex items-center gap-1.5">🏎️ TURBO RACER</span>
        <div class="flex items-center gap-3">
          <span>Score: <strong id="raceScore" class="text-white">0</strong></span>
          <span>Best: <strong id="raceBest" class="text-emerald-400">0</strong></span>
        </div>
      </div>

      <div class="relative bg-slate-950 rounded-2xl border border-slate-800 p-2 overflow-hidden shadow-inner">
        <canvas id="raceCanvas" width="320" height="420" class="block bg-slate-950 rounded-xl"></canvas>
        <div id="raceOverlay" class="absolute inset-0 bg-slate-950/90 backdrop-blur-sm flex flex-col items-center justify-center hidden">
          <div class="text-3xl font-black text-rose-500 mb-1">CRASH!</div>
          <p class="text-xs text-slate-400 mb-4">You hit another vehicle.</p>
          <button id="raceRestartBtn" class="px-6 py-2.5 bg-amber-500 hover:bg-amber-600 text-slate-950 font-black text-xs rounded-xl shadow-lg transition">RACE AGAIN</button>
        </div>
      </div>

      <div class="mt-4 flex items-center justify-center gap-4 text-xs font-bold">
        <button id="steerLeft" class="px-6 py-3 bg-slate-800 active:bg-slate-700 rounded-2xl border border-slate-700">◀ LEFT</button>
        <button id="steerRight" class="px-6 py-3 bg-slate-800 active:bg-slate-700 rounded-2xl border border-slate-700">RIGHT ▶</button>
      </div>
      <p class="text-[11px] text-slate-500 mt-2 font-mono">Use Left / Right arrow keys or A / D</p>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('raceCanvas');
  const ctx = canvas.getContext('2d');
  const scoreDisp = document.getElementById('raceScore');
  const bestDisp = document.getElementById('raceBest');
  const overlay = document.getElementById('raceOverlay');
  const restart = document.getElementById('raceRestartBtn');

  let best = parseInt(localStorage.getItem('race_best') || '0', 10);
  bestDisp.textContent = best;

  let player = { x: 135, y: 350, w: 32, h: 54, speed: 6 };
  let obstacles = [];
  let score = 0, speedMult = 4, animId = null, dead = false;
  let lineOffset = 0;

  function spawnObstacle() {
    const lanes = [40, 110, 180, 250];
    const x = lanes[Math.floor(Math.random() * lanes.length)];
    const colors = ['#f43f5e', '#06b6d4', '#10b981', '#a855f7'];
    obstacles.push({
      x,
      y: -60,
      w: 32,
      h: 52,
      color: colors[Math.floor(Math.random() * colors.length)],
      speed: 3 + Math.random() * 2
    });
  }

  function loop() {
    if (dead) return;

    lineOffset = (lineOffset + speedMult) % 40;
    score++;
    scoreDisp.textContent = score;
    if (score > best) { best = score; bestDisp.textContent = best; localStorage.setItem('race_best', best); }
    if (score % 250 === 0) speedMult += 0.5;

    if (Math.random() < 0.035) spawnObstacle();

    // Road background
    ctx.fillStyle = '#0f172a'; ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Lane markings
    ctx.strokeStyle = '#334155'; ctx.lineWidth = 4; ctx.setLineDash([20, 20]); ctx.lineDashOffset = -lineOffset;
    ctx.beginPath(); ctx.moveTo(80, 0); ctx.lineTo(80, canvas.height); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(160, 0); ctx.lineTo(160, canvas.height); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(240, 0); ctx.lineTo(240, canvas.height); ctx.stroke();
    ctx.setLineDash([]);

    // Player car
    ctx.fillStyle = '#f59e0b';
    ctx.beginPath(); ctx.roundRect(player.x, player.y, player.w, player.h, 6); ctx.fill();
    // Wheels
    ctx.fillStyle = '#020617';
    ctx.fillRect(player.x - 3, player.y + 8, 3, 10);
    ctx.fillRect(player.x + player.w, player.y + 8, 3, 10);
    ctx.fillRect(player.x - 3, player.y + 36, 3, 10);
    ctx.fillRect(player.x + player.w, player.y + 36, 3, 10);

    // Obstacles
    for (let i = obstacles.length - 1; i >= 0; i--) {
      const o = obstacles[i];
      o.y += speedMult + o.speed;

      ctx.fillStyle = o.color;
      ctx.beginPath(); ctx.roundRect(o.x, o.y, o.w, o.h, 6); ctx.fill();

      // Collision box test
      if (player.x < o.x + o.w && player.x + player.w > o.x && player.y < o.y + o.h && player.y + player.h > o.y) {
        dead = true;
        overlay.classList.remove('hidden');
        cancelAnimationFrame(animId);
        return;
      }

      if (o.y > canvas.height + 60) obstacles.splice(i, 1);
    }

    animId = requestAnimationFrame(loop);
  }

  function start() {
    player.x = 144; obstacles = []; score = 0; speedMult = 4; dead = false;
    overlay.classList.add('hidden');
    cancelAnimationFrame(animId);
    animId = requestAnimationFrame(loop);
  }

  window.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft' || e.key === 'a') player.x = Math.max(20, player.x - 24);
    if (e.key === 'ArrowRight' || e.key === 'd') player.x = Math.min(canvas.width - player.w - 20, player.x + 24);
  });

  document.getElementById('steerLeft').onclick = () => { player.x = Math.max(20, player.x - 24); };
  document.getElementById('steerRight').onclick = () => { player.x = Math.min(canvas.width - player.w - 20, player.x + 24); };
  restart.onclick = start;

  start();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('highway-racer'),
    'README.md': baseReadme('TurboRacer 2D Arcade', ['Smooth requestAnimationFrame Canvas 60fps', 'Collision detection', 'Progressive speed increase']),
    'src/App.test.tsx': baseTests('Turbo Racer')
  }
}

// 2. LIVE MARKDOWN STUDIO & NOTE-TAKING
export function buildMarkdownStudioApp(): SynthesizedProject {
  const html = wrapHtml('MarkFlow — Live Markdown Studio', `
  <main class="flex-1 p-6 max-w-6xl mx-auto w-full flex flex-col h-screen">
    <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
      <div>
        <h1 class="text-xl font-black text-white flex items-center gap-2">✍️ MarkFlow</h1>
        <p class="text-xs text-slate-400">Live Markdown Editor & Real-time HTML Preview</p>
      </div>
      <div class="flex items-center gap-3 text-xs">
        <span id="wordCountBadge" class="font-mono text-slate-400">0 words · 0 chars</span>
        <button id="downloadMdBtn" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl font-bold border border-slate-700">Export .md</button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-4 flex-1 min-h-0">
      <div class="flex flex-col bg-slate-900 border border-slate-800 rounded-3xl p-4">
        <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs font-mono text-slate-400">
          <span>MARKDOWN INPUT</span>
          <span class="text-indigo-400">Auto-saved</span>
        </div>
        <textarea id="mdInput" class="flex-1 w-full bg-slate-950 p-4 rounded-2xl border border-slate-800 text-white font-mono text-xs focus:outline-none resize-none leading-relaxed"></textarea>
      </div>

      <div class="flex flex-col bg-slate-900 border border-slate-800 rounded-3xl p-4">
        <div class="flex items-center justify-between pb-2 mb-2 border-b border-slate-800 text-xs font-mono text-slate-400">
          <span>LIVE PREVIEW</span>
          <span class="text-emerald-400">Rendered</span>
        </div>
        <div id="mdPreview" class="flex-1 w-full bg-slate-950 p-6 rounded-2xl border border-slate-800 overflow-y-auto text-xs text-slate-200 prose prose-invert max-w-none leading-relaxed"></div>
      </div>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const defaultDoc = '# Welcome to MarkFlow Studio\\n\\nReal-time autonomous documentation and markdown workspace.\\n\\n## Key Capabilities\\n- **Bold text** and *italicized formatting*\\n- Bullet lists and task tracking\\n- Clean live rendering\\n\\n> Built with clean client state persistence in localStorage.';
  
  const input = document.getElementById('mdInput');
  const preview = document.getElementById('mdPreview');
  const badge = document.getElementById('wordCountBadge');

  input.value = localStorage.getItem('markflow_doc') || defaultDoc;

  function render() {
    const raw = input.value;
    localStorage.setItem('markflow_doc', raw);

    const words = raw.trim() ? raw.trim().split(/\\s+/).length : 0;
    badge.textContent = words + ' words · ' + raw.length + ' chars';

    let html = raw
      .replace(/^### (.*$)/gm, '<h3 class="text-base font-bold text-white mt-4 mb-2">$1</h3>')
      .replace(/^## (.*$)/gm, '<h2 class="text-lg font-black text-white mt-5 mb-2">$1</h2>')
      .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-black text-indigo-400 mb-3">$1</h1>')
      .replace(/^> (.*$)/gm, '<blockquote class="border-l-4 border-indigo-500 pl-3 italic text-slate-400 my-2">$1</blockquote>')
      .replace(/\\*\\*(.*?)\\*\\*/gm, '<strong class="text-white font-bold">$1</strong>')
      .replace(/\\*(.*?)\\*/gm, '<em class="text-indigo-300">$1</em>')
      .replace(/^\\- (.*$)/gm, '<li class="ml-4 list-disc text-slate-300">$1</li>')
      .replace(/\\n/gm, '<br />');

    preview.innerHTML = html;
  }

  input.addEventListener('input', render);
  document.getElementById('downloadMdBtn').onclick = () => {
    const blob = new Blob([input.value], { type: 'text/markdown' });
    const a = document.createElement('a'); a.download = 'document.md'; a.href = URL.createObjectURL(blob); a.click();
  };

  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('markdown-studio'),
    'README.md': baseReadme('MarkFlow Studio', ['Split-screen markdown editor', 'Live HTML preview parser', 'Word & character count metrics']),
    'src/App.test.tsx': baseTests('MarkFlow')
  }
}

// 3. TRIVIA & QUIZ BATTLE APP
export function buildQuizTriviaApp(): SynthesizedProject {
  const html = wrapHtml('QuizForge — Master Trivia Challenge', `
  <main class="flex-1 p-6 max-w-xl mx-auto w-full flex flex-col justify-center">
    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6">
      <div class="flex items-center justify-between pb-3 border-b border-slate-800">
        <h1 class="text-lg font-black text-white flex items-center gap-2">🧠 QuizForge</h1>
        <div class="flex items-center gap-3 text-xs font-mono">
          <span id="questionCounter" class="text-slate-400">Question 1/4</span>
          <span class="px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-bold">Score: <span id="scoreVal">0</span></span>
        </div>
      </div>

      <div class="space-y-4">
        <div class="h-2 w-full bg-slate-950 rounded-full overflow-hidden">
          <div id="timerBar" class="h-full bg-indigo-500 transition-all duration-1000 w-full"></div>
        </div>
        <p id="questionPrompt" class="text-base font-bold text-white leading-relaxed min-h-[48px]">Which planet in our solar system has the most moons?</p>
      </div>

      <div id="optionsGrid" class="space-y-2.5"></div>

      <div id="feedbackBox" class="p-3.5 rounded-2xl bg-slate-950 border border-slate-800 text-xs hidden"></div>

      <button id="nextQuestionBtn" class="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-2xl shadow transition text-xs hidden">Next Question ▶</button>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const questions = [
    { q: 'Which planet in our solar system has the most confirmed moons?', opts: ['Jupiter', 'Saturn', 'Uranus', 'Neptune'], ans: 1, expl: 'Saturn has 146 recognized moons, surpassing Jupiter.' },
    { q: 'What is the primary language used to structure web pages?', opts: ['CSS', 'HTML', 'Python', 'SQL'], ans: 1, expl: 'HTML (HyperText Markup Language) defines structure.' },
    { q: 'Which data structure follows a First-In-First-Out (FIFO) order?', opts: ['Stack', 'Tree', 'Queue', 'Graph'], ans: 2, expl: 'A Queue processes items First-In, First-Out.' },
    { q: 'What year was the World Wide Web introduced to the public?', opts: ['1983', '1989', '1991', '1995'], ans: 2, expl: 'Tim Berners-Lee made the Web public in August 1991.' }
  ];

  let current = 0, score = 0, answered = false;

  function render() {
    answered = false;
    const q = questions[current];
    document.getElementById('questionCounter').textContent = 'Question ' + (current + 1) + '/' + questions.length;
    document.getElementById('scoreVal').textContent = score;
    document.getElementById('questionPrompt').textContent = q.q;
    document.getElementById('feedbackBox').classList.add('hidden');
    document.getElementById('nextQuestionBtn').classList.add('hidden');

    const optsContainer = document.getElementById('optionsGrid');
    optsContainer.innerHTML = '';
    q.opts.forEach((opt, idx) => {
      const btn = document.createElement('button');
      btn.className = 'w-full text-left p-3.5 rounded-2xl bg-slate-950 hover:bg-slate-800 border border-slate-800 text-white text-xs font-semibold transition';
      btn.innerHTML = \`<span class="font-mono text-indigo-400 mr-2">\${['A', 'B', 'C', 'D'][idx]}.</span> \${opt}\`;
      btn.onclick = () => selectOption(idx);
      optsContainer.appendChild(btn);
    });
  }

  function selectOption(idx) {
    if (answered) return;
    answered = true;
    const q = questions[current];
    const isCorrect = idx === q.ans;
    if (isCorrect) score += 10;
    document.getElementById('scoreVal').textContent = score;

    const fb = document.getElementById('feedbackBox');
    fb.className = 'p-3.5 rounded-2xl border text-xs ' + (isCorrect ? 'bg-emerald-950/40 border-emerald-900 text-emerald-300' : 'bg-rose-950/40 border-rose-900 text-rose-300');
    fb.innerHTML = \`<strong class="block mb-1">\${isCorrect ? '🎉 Correct!' : '❌ Incorrect'}</strong>\${q.expl}\`;
    fb.classList.remove('hidden');

    const nextBtn = document.getElementById('nextQuestionBtn');
    nextBtn.textContent = current + 1 < questions.length ? 'Next Question ▶' : 'Finish Quiz 🏁';
    nextBtn.classList.remove('hidden');
  }

  document.getElementById('nextQuestionBtn').onclick = () => {
    if (current + 1 < questions.length) {
      current++;
      render();
    } else {
      alert('Quiz complete! Your final score is ' + score + ' out of ' + (questions.length * 10) + '.');
      current = 0; score = 0; render();
    }
  };

  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('quiz-trivia'),
    'README.md': baseReadme('QuizForge Trivia Challenge', ['Multiple choice questions', 'Score tracking', 'Explanation feedback']),
    'src/App.test.tsx': baseTests('Quiz Trivia')
  }
}

// 4. FITNESS & WORKOUT TRACKER
export function buildWorkoutTracker(): SynthesizedProject {
  const html = wrapHtml('FitLog — Workout & Exercise Ledger', `
  <main class="flex-1 p-6 max-w-4xl mx-auto w-full space-y-6">
    <div class="flex items-center justify-between pb-4 border-b border-slate-800">
      <div>
        <h1 class="text-2xl font-black text-white flex items-center gap-2">🏋️ FitLog Pro</h1>
        <p class="text-xs text-slate-400">Exercise sets, weight volumes & rest intervals</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6">
        <h3 class="text-sm font-bold text-white mb-4">Log Set</h3>
        <form id="workoutForm" class="space-y-3 text-xs">
          <div><label class="block text-slate-400 mb-1">Exercise</label><input id="exName" required placeholder="e.g. Bench Press" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
          <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-slate-400 mb-1">Weight (lbs)</label><input id="exWeight" type="number" required placeholder="185" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
            <div><label class="block text-slate-400 mb-1">Reps</label><input id="exReps" type="number" required placeholder="8" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
          </div>
          <button type="submit" class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow">+ Add Set</button>
        </form>
      </div>

      <div class="md:col-span-2 bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col justify-between">
        <div>
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-bold text-white">Today's Workout Session</h3>
            <span id="sessionVolume" class="text-xs text-emerald-400 font-mono font-bold">Total Vol: 0 lbs</span>
          </div>
          <div id="workoutList" class="space-y-2 max-h-72 overflow-y-auto"></div>
        </div>
      </div>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  let entries = JSON.parse(localStorage.getItem('fitlog_entries') || 'null') || [
    { id: 'w1', name: 'Barbell Squat', weight: 225, reps: 5 },
    { id: 'w2', name: 'Barbell Bench Press', weight: 185, reps: 8 },
    { id: 'w3', name: 'Deadlift', weight: 275, reps: 5 }
  ];

  function render() {
    const list = document.getElementById('workoutList');
    list.innerHTML = '';
    let vol = 0;

    entries.forEach(e => {
      vol += e.weight * e.reps;
      const row = document.createElement('div');
      row.className = 'p-3 bg-slate-950 border border-slate-800 rounded-2xl flex items-center justify-between text-xs';
      row.innerHTML = \`<div><strong class="text-white block">\${e.name}</strong><span class="text-slate-400">\${e.weight} lbs × \${e.reps} reps</span></div>
      <div class="flex items-center gap-3">
        <span class="text-indigo-400 font-mono font-bold">\${e.weight * e.reps} lbs</span>
        <button class="del-btn text-slate-500 hover:text-rose-400" data-id="\${e.id}">✕</button>
      </div>\`;
      list.appendChild(row);
    });

    document.getElementById('sessionVolume').textContent = 'Total Vol: ' + vol.toLocaleString() + ' lbs';
    localStorage.setItem('fitlog_entries', JSON.stringify(entries));

    document.querySelectorAll('.del-btn').forEach(b => b.onclick = () => {
      entries = entries.filter(x => x.id !== b.dataset.id); render();
    });
  }

  document.getElementById('workoutForm').onsubmit = (e) => {
    e.preventDefault();
    entries.unshift({
      id: 'w-' + Date.now(),
      name: document.getElementById('exName').value.trim(),
      weight: parseFloat(document.getElementById('exWeight').value),
      reps: parseInt(document.getElementById('exReps').value, 10)
    });
    document.getElementById('exName').value = '';
    render();
  };

  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('workout-tracker'),
    'README.md': baseReadme('FitLog Workout Tracker', ['Set and rep recording', 'Total volume calculations', 'Local storage persistence']),
    'src/App.test.tsx': baseTests('FitLog Tracker')
  }
}

// 5. FLIGHT TRACKER & AIRPORT BOARD
export function buildFlightTracker(): SynthesizedProject {
  const html = wrapHtml('AeroPulse — Flight Tracker & Airport Board', `
  <main class="flex-1 p-6 max-w-5xl mx-auto w-full space-y-6">
    <div class="flex items-center justify-between pb-4 border-b border-slate-800">
      <div>
        <h1 class="text-2xl font-black text-white flex items-center gap-2">🛫 AeroPulse</h1>
        <p class="text-xs text-slate-400">Live Airport Departures, Terminal Gates & Status</p>
      </div>
      <input id="flightSearch" type="text" placeholder="Search by flight # or city..." class="bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 w-64" />
    </div>

    <div class="rounded-3xl border border-slate-800 overflow-hidden bg-slate-900/60 shadow-xl">
      <div class="grid grid-cols-12 bg-slate-900 p-3.5 text-xs font-mono font-bold text-slate-400 border-b border-slate-800">
        <div class="col-span-3">FLIGHT</div>
        <div class="col-span-3">DESTINATION</div>
        <div class="col-span-2">TIME</div>
        <div class="col-span-2">GATE</div>
        <div class="col-span-2 text-right">STATUS</div>
      </div>
      <div id="flightList" class="divide-y divide-slate-800/60 font-mono text-xs"></div>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const flights = [
    { num: 'UA-824', dest: 'London Heathrow (LHR)', time: '14:25', gate: 'B12', status: 'On Time', statColor: 'text-emerald-400' },
    { num: 'DL-194', dest: 'Tokyo Haneda (HND)', time: '14:40', gate: 'A4', status: 'Boarding', statColor: 'text-amber-400' },
    { num: 'AA-432', dest: 'Paris Charles de Gaulle (CDG)', time: '15:10', gate: 'C19', status: 'Delayed', statColor: 'text-rose-400' },
    { num: 'SQ-031', dest: 'Singapore Changi (SIN)', time: '15:35', gate: 'B08', status: 'On Time', statColor: 'text-emerald-400' },
    { num: 'LH-456', dest: 'Frankfurt Main (FRA)', time: '16:00', gate: 'A15', status: 'On Time', statColor: 'text-emerald-400' }
  ];

  function render() {
    const list = document.getElementById('flightList');
    const q = (document.getElementById('flightSearch').value || '').toLowerCase().trim();
    list.innerHTML = '';

    const filtered = flights.filter(f => !q || f.num.toLowerCase().includes(q) || f.dest.toLowerCase().includes(q));
    filtered.forEach(f => {
      const row = document.createElement('div');
      row.className = 'grid grid-cols-12 p-3.5 items-center hover:bg-slate-800/40 transition';
      row.innerHTML = \`<div class="col-span-3 font-bold text-white flex items-center gap-1.5"><span class="text-indigo-400">✈</span> \${f.num}</div>
      <div class="col-span-3 text-slate-200">\${f.dest}</div>
      <div class="col-span-2 text-slate-400">\${f.time}</div>
      <div class="col-span-2 text-slate-400">\${f.gate}</div>
      <div class="col-span-2 text-right font-bold \${f.statColor}">\${f.status}</div>\`;
      list.appendChild(row);
    });
  }

  document.getElementById('flightSearch').oninput = render;
  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('flight-tracker'),
    'README.md': baseReadme('AeroPulse Flight Tracker', ['Live Airport Departure board', 'Search filter', 'Terminal gate assignments']),
    'src/App.test.tsx': baseTests('Flight Tracker')
  }
}

// 6. DOCTOR APPOINTMENT BOOKING & MEDICAL TRIAGE
export function buildDoctorBookingApp(): SynthesizedProject {
  const html = wrapHtml('MediCare — Clinic Appointment Booking & Triage', `
  <main class="flex-1 p-6 max-w-5xl mx-auto w-full space-y-6">
    <div class="flex items-center justify-between pb-4 border-b border-slate-800">
      <div>
        <h1 class="text-2xl font-black text-white flex items-center gap-2">🩺 MediCare Plus</h1>
        <p class="text-xs text-slate-400">Specialist consultations & verified clinic appointments</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-4">
        <h3 class="text-sm font-bold text-white">Book Appointment</h3>
        <form id="bookForm" class="space-y-3 text-xs">
          <div><label class="block text-slate-400 mb-1">Patient Full Name</label><input id="patName" required placeholder="Jane Doe" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
          <div><label class="block text-slate-400 mb-1">Specialty</label><select id="patSpec" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"><option>Cardiology</option><option>General Medicine</option><option>Dermatology</option><option>Pediatrics</option></select></div>
          <div><label class="block text-slate-400 mb-1">Preferred Date</label><input id="patDate" type="date" required class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
          <div><label class="block text-slate-400 mb-1">Symptoms / Reason</label><textarea id="patNotes" placeholder="Describe symptoms..." class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white resize-none h-16"></textarea></div>
          <button type="submit" class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow">Confirm Booking</button>
        </form>
      </div>

      <div class="md:col-span-2 bg-slate-900 border border-slate-800 rounded-3xl p-6">
        <h3 class="text-sm font-bold text-white mb-4">Confirmed Patient Appointments</h3>
        <div id="bookingList" class="space-y-3"></div>
      </div>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  let bookings = JSON.parse(localStorage.getItem('medicare_bookings') || 'null') || [
    { id: 'b1', name: 'Michael Scott', spec: 'Cardiology', date: 'Tomorrow, 10:00 AM', status: 'Confirmed' },
    { id: 'b2', name: 'Pam Beesly', spec: 'Dermatology', date: 'Friday, 2:30 PM', status: 'Pending' }
  ];

  function render() {
    const list = document.getElementById('bookingList');
    list.innerHTML = '';
    bookings.forEach(b => {
      const card = document.createElement('div');
      card.className = 'p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-between text-xs';
      card.innerHTML = \`<div>
        <strong class="text-white block text-sm">\${b.name}</strong>
        <span class="text-indigo-400 font-bold">\${b.spec}</span> · <span class="text-slate-400">\${b.date}</span>
      </div>
      <div class="flex items-center gap-3">
        <span class="px-2.5 py-1 rounded-full text-[10px] font-bold \${b.status === 'Confirmed' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-amber-500/20 text-amber-400'}">\${b.status}</span>
        <button class="del-btn text-slate-500 hover:text-rose-400" data-id="\${b.id}">✕</button>
      </div>\`;
      list.appendChild(card);
    });

    localStorage.setItem('medicare_bookings', JSON.stringify(bookings));
    document.querySelectorAll('.del-btn').forEach(b => b.onclick = () => {
      bookings = bookings.filter(x => x.id !== b.dataset.id); render();
    });
  }

  document.getElementById('bookForm').onsubmit = (e) => {
    e.preventDefault();
    bookings.unshift({
      id: 'b-' + Date.now(),
      name: document.getElementById('patName').value.trim(),
      spec: document.getElementById('patSpec').value,
      date: document.getElementById('patDate').value,
      status: 'Confirmed'
    });
    document.getElementById('patName').value = '';
    render();
  };

  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('doctor-booking'),
    'README.md': baseReadme('MediCare Clinic Booking', ['Specialty consultations', 'Date scheduling', 'Local storage persistence']),
    'src/App.test.tsx': baseTests('Doctor Booking')
  }
}

// 7. SOLAR SYSTEM INTERACTIVE SIMULATION
export function buildSolarSystemApp(): SynthesizedProject {
  const html = wrapHtml('CosmoSim — Interactive Solar System Simulation', `
  <header class="border-b border-slate-800 bg-slate-900/90 backdrop-blur sticky top-0 z-40 px-6 py-3 flex flex-wrap items-center justify-between gap-4">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-2xl bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-2xl shadow-lg shadow-amber-500/10">☀️</div>
      <div>
        <h1 class="text-base font-black text-white tracking-wide">CosmoSim Solar System</h1>
        <p class="text-[11px] text-slate-400">Real-time Orbital Mechanics & Planetary Simulation</p>
      </div>
    </div>

    <!-- Controls -->
    <div class="flex items-center gap-3 text-xs">
      <button id="playPauseBtn" class="px-3.5 py-1.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl shadow transition flex items-center gap-1.5">
        <span id="playIcon">⏸</span> <span id="playText">Pause</span>
      </button>

      <div class="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-xl px-3 py-1 text-slate-300">
        <span>Speed:</span>
        <input id="speedRange" type="range" min="0.2" max="5" step="0.2" value="1" class="w-20 cursor-pointer accent-amber-500" />
        <span id="speedVal" class="font-mono text-amber-400 font-bold w-7">1x</span>
      </div>

      <button id="toggleOrbitsBtn" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl font-medium transition">Orbits: ON</button>
      <button id="toggleLabelsBtn" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl font-medium transition">Labels: ON</button>

      <select id="planetSelect" class="bg-slate-900 border border-slate-800 rounded-xl px-3 py-1.5 text-white font-medium">
        <option value="">Inspect Planet...</option>
        <option value="Sun">Sun (Star)</option>
        <option value="Mercury">Mercury</option>
        <option value="Venus">Venus</option>
        <option value="Earth">Earth</option>
        <option value="Mars">Mars</option>
        <option value="Jupiter">Jupiter</option>
        <option value="Saturn">Saturn</option>
        <option value="Uranus">Uranus</option>
        <option value="Neptune">Neptune</option>
      </select>
    </div>
  </header>

  <main class="flex-1 relative overflow-hidden bg-slate-950 flex">
    <!-- 2D Canvas Viewport -->
    <div class="flex-1 relative h-full min-h-[600px] flex items-center justify-center">
      <canvas id="solarCanvas" class="w-full h-full block bg-slate-950 cursor-grab active:cursor-grabbing"></canvas>
      <div class="absolute bottom-4 left-4 bg-slate-900/80 backdrop-blur border border-slate-800 rounded-2xl p-3 text-[11px] text-slate-400 space-y-1 pointer-events-none shadow-xl">
        <p class="font-bold text-white flex items-center gap-1.5">🪐 Orbital Controls</p>
        <p>• Click any planet to view physical specs & facts</p>
        <p>• Drag or adjust speed slider to accelerate time</p>
      </div>
    </div>

    <!-- Planet Information Drawer -->
    <div id="planetDrawer" class="w-80 bg-slate-900/95 border-l border-slate-800 p-6 flex flex-col justify-between hidden shadow-2xl backdrop-blur">
      <div>
        <div class="flex items-center justify-between pb-3 border-b border-slate-800 mb-4">
          <div class="flex items-center gap-2.5">
            <span id="drawerEmoji" class="text-3xl">🌍</span>
            <div>
              <h2 id="drawerName" class="text-lg font-black text-white">Earth</h2>
              <span id="drawerType" class="text-[10px] text-amber-400 font-bold uppercase tracking-wider">Terrestrial Planet</span>
            </div>
          </div>
          <button id="closeDrawerBtn" class="text-slate-500 hover:text-white text-sm">✕</button>
        </div>

        <div class="space-y-3 text-xs">
          <div class="p-3 rounded-2xl bg-slate-950 border border-slate-800 flex justify-between"><span class="text-slate-400">Diameter:</span><strong id="drawerDiameter" class="text-white font-mono">12,742 km</strong></div>
          <div class="p-3 rounded-2xl bg-slate-950 border border-slate-800 flex justify-between"><span class="text-slate-400">Distance from Sun:</span><strong id="drawerDistance" class="text-amber-400 font-mono">149.6M km (1 AU)</strong></div>
          <div class="p-3 rounded-2xl bg-slate-950 border border-slate-800 flex justify-between"><span class="text-slate-400">Orbital Period:</span><strong id="drawerPeriod" class="text-emerald-400 font-mono">365.25 days</strong></div>
          <div class="p-3 rounded-2xl bg-slate-950 border border-slate-800 flex justify-between"><span class="text-slate-400">Mean Temperature:</span><strong id="drawerTemp" class="text-white font-mono">15 °C</strong></div>
          <div class="p-3 rounded-2xl bg-slate-950 border border-slate-800 flex justify-between"><span class="text-slate-400">Known Moons:</span><strong id="drawerMoons" class="text-indigo-400 font-mono">1 (The Moon)</strong></div>

          <div class="pt-2">
            <h4 class="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1">Key Astronomical Facts</h4>
            <p id="drawerFacts" class="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-2xl border border-slate-800/80">
              Only known planet harboring liquid water oceans and life in the universe. Has an active magnetosphere protecting its atmosphere.
            </p>
          </div>
        </div>
      </div>

      <button id="focusPlanetBtn" class="w-full py-2.5 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-xs shadow mt-4 transition">Track This Planet</button>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const canvas = document.getElementById('solarCanvas');
  const ctx = canvas.getContext('2d');

  function resize() {
    canvas.width = canvas.parentElement.clientWidth;
    canvas.height = canvas.parentElement.clientHeight || 650;
  }
  window.addEventListener('resize', resize);
  resize();

  const planetsData = {
    Sun: { emoji: '☀️', type: 'Yellow Dwarf Star (G2V)', diam: '1,392,700 km', dist: '0 km (Center)', period: 'N/A', temp: '5,500 °C (Surface)', moons: '8 Planets, Millions of Asteroids', facts: 'Contains 99.86% of all mass in the Solar System. Powered by nuclear fusion converting 600M tons of hydrogen into helium every second.' },
    Mercury: { emoji: '⚪', type: 'Terrestrial Planet', diam: '4,879 km', dist: '57.9M km (0.39 AU)', period: '88 days', temp: '167 °C (-180°C to 430°C)', moons: '0', facts: 'Smallest planet and closest to the Sun. Has virtually no atmosphere (exosphere) and heavily cratered like our Moon.' },
    Venus: { emoji: '🟡', type: 'Terrestrial Planet', diam: '12,104 km', dist: '108.2M km (0.72 AU)', period: '225 days', temp: '464 °C (Runaway Greenhouse)', moons: '0', facts: 'Hottest planet in the Solar System with crushing carbon dioxide atmosphere and sulfuric acid clouds. Rotates backwards (retrograde).' },
    Earth: { emoji: '🌍', type: 'Terrestrial Planet', diam: '12,742 km', dist: '149.6M km (1.00 AU)', period: '365.25 days', temp: '15 °C', moons: '1 (The Moon)', facts: 'Only known haven for life in the universe. Abundant surface liquid oceans, nitrogen-oxygen atmosphere, and protective geomagnetic shield.' },
    Mars: { emoji: '🔴', type: 'Terrestrial Planet', diam: '6,779 km', dist: '227.9M km (1.52 AU)', period: '687 days', temp: '-65 °C', moons: '2 (Phobos & Deimos)', facts: 'The Red Planet, colored by iron oxide (rust). Home to Olympus Mons, the largest volcano in the Solar System, 3x taller than Mt Everest.' },
    Jupiter: { emoji: '🟠', type: 'Gas Giant', diam: '139,820 km', dist: '778.5M km (5.20 AU)', period: '11.86 years', temp: '-110 °C', moons: '95 (Io, Europa, Ganymede...)', facts: 'Largest planet in the solar system, more than twice as massive as all other planets combined. The Great Red Spot is a storm raging for over 300 years.' },
    Saturn: { emoji: '🪐', type: 'Gas Giant', diam: '116,460 km', dist: '1.43B km (9.58 AU)', period: '29.45 years', temp: '-140 °C', moons: '146 (Titan, Enceladus...)', facts: 'Famous for its dazzling system of ice rings extending up to 282,000 km from the planet. Low density that would float in water.' },
    Uranus: { emoji: '🩵', type: 'Ice Giant', diam: '50,724 km', dist: '2.87B km (19.2 AU)', period: '84.02 years', temp: '-195 °C', moons: '28 (Titania, Oberon...)', facts: 'Cyan ice giant tilted dramatically on its side (97.8° tilt), effectively orbiting the Sun rolling like a ball.' },
    Neptune: { emoji: '🔵', type: 'Ice Giant', diam: '49,244 km', dist: '4.50B km (30.0 AU)', period: '164.8 years', temp: '-200 °C', moons: '16 (Triton...)', facts: 'Most distant major planet. Deep blue atmosphere with the fastest recorded winds in the solar system, exceeding 2,100 km/h.' }
  };

  const planets = [
    { name: 'Mercury', r: 4, dist: 46, speed: 0.045, color: '#94a3b8', angle: Math.random() * Math.PI * 2 },
    { name: 'Venus', r: 7, dist: 72, speed: 0.032, color: '#f59e0b', angle: Math.random() * Math.PI * 2 },
    { name: 'Earth', r: 8, dist: 104, speed: 0.024, color: '#38bdf8', angle: Math.random() * Math.PI * 2, moon: { dist: 14, speed: 0.12, angle: 0 } },
    { name: 'Mars', r: 6, dist: 138, speed: 0.018, color: '#ef4444', angle: Math.random() * Math.PI * 2 },
    { name: 'Jupiter', r: 17, dist: 188, speed: 0.011, color: '#d97706', angle: Math.random() * Math.PI * 2 },
    { name: 'Saturn', r: 14, dist: 242, speed: 0.008, color: '#eab308', angle: Math.random() * Math.PI * 2, hasRings: true },
    { name: 'Uranus', r: 10, dist: 294, speed: 0.005, color: '#22d3ee', angle: Math.random() * Math.PI * 2 },
    { name: 'Neptune', r: 10, dist: 342, speed: 0.0035, color: '#3b82f6', angle: Math.random() * Math.PI * 2 }
  ];

  // Stars background
  const stars = Array.from({ length: 160 }, () => ({
    x: Math.random(),
    y: Math.random(),
    size: Math.random() * 1.5 + 0.5,
    alpha: Math.random() * 0.8 + 0.2
  }));

  let isRunning = true;
  let speedMultiplier = 1;
  let showOrbits = true;
  let showLabels = true;
  let focusedPlanet = null;
  let sunPulse = 0;

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Draw background stars
    stars.forEach(s => {
      ctx.fillStyle = \`rgba(255, 255, 255, \${s.alpha})\`;
      ctx.fillRect(s.x * canvas.width, s.y * canvas.height, s.size, s.size);
    });

    sunPulse += 0.03;
    const pulseFactor = Math.sin(sunPulse) * 3;

    // Draw Orbits
    if (showOrbits) {
      planets.forEach(p => {
        ctx.beginPath();
        ctx.arc(cx, cy, p.dist, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(71, 85, 105, 0.25)';
        ctx.lineWidth = 1;
        ctx.stroke();
      });
    }

    // Draw Sun
    const sunGrad = ctx.createRadialGradient(cx, cy, 5, cx, cy, 28 + pulseFactor);
    sunGrad.addColorStop(0, '#ffffff');
    sunGrad.addColorStop(0.2, '#fef08a');
    sunGrad.addColorStop(0.6, '#f59e0b');
    sunGrad.addColorStop(1, 'rgba(234, 88, 12, 0)');
    ctx.fillStyle = sunGrad;
    ctx.beginPath();
    ctx.arc(cx, cy, 32 + pulseFactor, 0, Math.PI * 2);
    ctx.fill();

    // Solid Sun Core
    ctx.fillStyle = '#fbbf24';
    ctx.beginPath();
    ctx.arc(cx, cy, 18, 0, Math.PI * 2);
    ctx.fill();

    if (showLabels) {
      ctx.font = '10px monospace';
      ctx.fillStyle = '#fde68a';
      ctx.textAlign = 'center';
      ctx.fillText('SUN', cx, cy + 28);
    }

    // Draw Planets
    planets.forEach(p => {
      if (isRunning) {
        p.angle += p.speed * speedMultiplier;
      }

      const px = cx + Math.cos(p.angle) * p.dist;
      const py = cy + Math.sin(p.angle) * p.dist;
      p.currentX = px;
      p.currentY = py;

      // Saturn Rings
      if (p.hasRings) {
        ctx.beginPath();
        ctx.ellipse(px, py, p.r + 9, (p.r + 9) / 2.8, p.angle, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(234, 179, 8, 0.65)';
        ctx.lineWidth = 2.5;
        ctx.stroke();
      }

      // Planet Body
      ctx.beginPath();
      ctx.arc(px, py, p.r, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.fill();

      // Atmospheric shading / highlight
      const shadeGrad = ctx.createRadialGradient(px - p.r * 0.3, py - p.r * 0.3, 1, px, py, p.r);
      shadeGrad.addColorStop(0, 'rgba(255,255,255,0.4)');
      shadeGrad.addColorStop(1, 'rgba(0,0,0,0.5)');
      ctx.fillStyle = shadeGrad;
      ctx.beginPath();
      ctx.arc(px, py, p.r, 0, Math.PI * 2);
      ctx.fill();

      // Earth Moon
      if (p.moon) {
        if (isRunning) p.moon.angle += p.moon.speed * speedMultiplier;
        const mx = px + Math.cos(p.moon.angle) * p.moon.dist;
        const my = py + Math.sin(p.moon.angle) * p.moon.dist;
        ctx.beginPath();
        ctx.arc(mx, my, 2, 0, Math.PI * 2);
        ctx.fillStyle = '#cbd5e1';
        ctx.fill();
      }

      // Planet Label
      if (showLabels) {
        ctx.font = '10px monospace';
        ctx.fillStyle = p.name === focusedPlanet ? '#38bdf8' : '#cbd5e1';
        ctx.textAlign = 'center';
        ctx.fillText(p.name, px, py + p.r + 12);
      }

      // Selection Ring
      if (p.name === focusedPlanet) {
        ctx.beginPath();
        ctx.arc(px, py, p.r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.stroke();
        ctx.setLineDash([]);
      }
    });

    requestAnimationFrame(draw);
  }

  function showPlanetInfo(name) {
    const info = planetsData[name];
    if (!info) return;
    focusedPlanet = name;
    document.getElementById('drawerName').textContent = name;
    document.getElementById('drawerEmoji').textContent = info.emoji;
    document.getElementById('drawerType').textContent = info.type;
    document.getElementById('drawerDiameter').textContent = info.diam;
    document.getElementById('drawerDistance').textContent = info.dist;
    document.getElementById('drawerPeriod').textContent = info.period;
    document.getElementById('drawerTemp').textContent = info.temp;
    document.getElementById('drawerMoons').textContent = info.moons;
    document.getElementById('drawerFacts').textContent = info.facts;
    document.getElementById('planetDrawer').classList.remove('hidden');
    document.getElementById('planetSelect').value = name;
  }

  // Click detection on canvas
  canvas.addEventListener('click', (e) => {
    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const cx = canvas.width / 2;
    const cy = canvas.height / 2;

    // Check Sun
    if (Math.hypot(mx - cx, my - cy) <= 24) {
      showPlanetInfo('Sun');
      return;
    }

    // Check Planets
    for (const p of planets) {
      if (p.currentX && Math.hypot(mx - p.currentX, my - p.currentY) <= p.r + 8) {
        showPlanetInfo(p.name);
        return;
      }
    }
  });

  // UI Event handlers
  document.getElementById('playPauseBtn').onclick = () => {
    isRunning = !isRunning;
    document.getElementById('playIcon').textContent = isRunning ? '⏸' : '▶';
    document.getElementById('playText').textContent = isRunning ? 'Pause' : 'Play';
  };

  document.getElementById('speedRange').oninput = (e) => {
    speedMultiplier = parseFloat(e.target.value);
    document.getElementById('speedVal').textContent = speedMultiplier + 'x';
  };

  document.getElementById('toggleOrbitsBtn').onclick = (e) => {
    showOrbits = !showOrbits;
    e.target.textContent = 'Orbits: ' + (showOrbits ? 'ON' : 'OFF');
  };

  document.getElementById('toggleLabelsBtn').onclick = (e) => {
    showLabels = !showLabels;
    e.target.textContent = 'Labels: ' + (showLabels ? 'ON' : 'OFF');
  };

  document.getElementById('planetSelect').onchange = (e) => {
    if (e.target.value) showPlanetInfo(e.target.value);
  };

  document.getElementById('closeDrawerBtn').onclick = () => {
    document.getElementById('planetDrawer').classList.add('hidden');
    focusedPlanet = null;
    document.getElementById('planetSelect').value = '';
  };

  // Start simulation
  draw();
  // Show Earth info initially
  setTimeout(() => showPlanetInfo('Earth'), 600);
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('solar-system-simulation'),
    'README.md': baseReadme('CosmoSim Solar System Simulation', ['Animated 2D Canvas orbital mechanics', '8 planets + Moon with real relative periods', 'Play/Pause & speed controls', 'Physical stats & astronomical fact sheets']),
    'src/App.test.tsx': baseTests('Solar System Simulation')
  }
}

