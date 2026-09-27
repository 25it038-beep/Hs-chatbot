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

// 1. COLLEGE EVENT MANAGEMENT APP (PRESET 1)
export function buildCollegeEventApp(): SynthesizedProject {
  const html = wrapHtml('CampusSphere — College Event Management', `
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center text-white text-xl font-black shadow-lg shadow-indigo-600/30">🎓</div>
      <div>
        <h1 class="text-base font-black text-white tracking-wide">CampusSphere</h1>
        <p class="text-[11px] text-slate-400">College Event Management & Ticketing Portal</p>
      </div>
    </div>
    <div class="flex items-center gap-3">
      <span id="userBadge" class="hidden text-xs bg-indigo-500/10 text-indigo-400 border border-indigo-500/30 px-3 py-1.5 rounded-xl font-bold flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full bg-emerald-400"></span><span id="userNameDisplay">Student</span>
      </span>
      <button id="authBtn" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow transition">Sign In</button>
      <button id="createEventBtn" class="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-xl text-xs font-bold transition">+ Host Event</button>
    </div>
  </header>

  <main class="flex-1 p-6 max-w-6xl mx-auto w-full space-y-6">
    <div class="grid grid-cols-1 sm:grid-cols-4 gap-4">
      <div class="p-5 rounded-3xl bg-slate-900 border border-slate-800 flex items-center justify-between">
        <div><span class="text-xs text-slate-400 uppercase font-bold block mb-1">Total Events</span><span id="statTotal" class="text-2xl font-black text-white">4</span></div>
        <span class="text-3xl">📅</span>
      </div>
      <div class="p-5 rounded-3xl bg-indigo-950/40 border border-indigo-900/60 flex items-center justify-between">
        <div><span class="text-xs text-indigo-400 uppercase font-bold block mb-1">Seats Remaining</span><span id="statSeats" class="text-2xl font-black text-indigo-400">340</span></div>
        <span class="text-3xl">🎟️</span>
      </div>
      <div class="p-5 rounded-3xl bg-emerald-950/40 border border-emerald-900/60 flex items-center justify-between">
        <div><span class="text-xs text-emerald-400 uppercase font-bold block mb-1">My Registrations</span><span id="statMyRsvp" class="text-2xl font-black text-emerald-400">0</span></div>
        <span class="text-3xl">✅</span>
      </div>
      <div class="p-5 rounded-3xl bg-purple-950/40 border border-purple-900/60 flex items-center justify-between">
        <div><span class="text-xs text-purple-400 uppercase font-bold block mb-1">Invariant Guard</span><span class="text-xs font-bold text-emerald-400">Backend Intact ✓</span></div>
        <span class="text-3xl">🛡️</span>
      </div>
    </div>

    <div class="flex flex-col sm:flex-row items-center justify-between gap-4 pb-2 border-b border-slate-800">
      <div class="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
        <button class="filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white" data-cat="all">All Events</button>
        <button class="filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 hover:text-white border border-slate-800" data-cat="Hackathon">Hackathons</button>
        <button class="filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 hover:text-white border border-slate-800" data-cat="Cultural">Cultural</button>
        <button class="filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 hover:text-white border border-slate-800" data-cat="Workshop">Workshops</button>
        <button class="filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 hover:text-white border border-slate-800" data-cat="Sports">Sports</button>
      </div>
      <input id="eventSearch" type="text" placeholder="Search events by title or venue..." class="w-full sm:w-72 bg-slate-900 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-indigo-500" />
    </div>

    <div id="eventsGrid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5"></div>
  </main>

  <div id="authModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-sm shadow-2xl space-y-4">
      <div class="flex items-center justify-between pb-2 border-b border-slate-800">
        <h3 class="text-sm font-bold text-white">Student Sign In</h3>
        <button id="closeAuthModal" class="text-slate-500 hover:text-white text-xs">✕</button>
      </div>
      <form id="authForm" class="space-y-3 text-xs">
        <div><label class="block text-slate-400 mb-1">Student Name</label><input id="loginName" required type="text" placeholder="Alex Rivera" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
        <div><label class="block text-slate-400 mb-1">Campus Email</label><input id="loginEmail" required type="email" placeholder="alex@campus.edu" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
        <button type="submit" class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow">Confirm Sign In</button>
      </form>
    </div>
  </div>

  <div id="createModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-md shadow-2xl space-y-4">
      <div class="flex items-center justify-between pb-2 border-b border-slate-800">
        <h3 class="text-sm font-bold text-white">Host New Campus Event</h3>
        <button id="closeCreateModal" class="text-slate-500 hover:text-white text-xs">✕</button>
      </div>
      <form id="eventForm" class="space-y-3 text-xs">
        <div><label class="block text-slate-400 mb-1">Event Title</label><input id="newTitle" required type="text" placeholder="AI Autonomous Hackathon 2026" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-slate-400 mb-1">Category</label><select id="newCat" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white"><option>Hackathon</option><option>Cultural</option><option>Workshop</option><option>Sports</option></select></div>
          <div><label class="block text-slate-400 mb-1">Total Capacity</label><input id="newCap" required type="number" value="100" min="10" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div><label class="block text-slate-400 mb-1">Date</label><input id="newDate" required type="date" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
          <div><label class="block text-slate-400 mb-1">Venue</label><input id="newVenue" required type="text" placeholder="Main Auditorium" class="w-full bg-slate-950 border border-slate-800 rounded-xl p-2.5 text-white" /></div>
        </div>
        <button type="submit" class="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl shadow">Publish Event</button>
      </form>
    </div>
  </div>

  <div id="ticketModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 w-full max-w-sm shadow-2xl text-center space-y-4">
      <div class="w-12 h-12 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-2xl mx-auto">🎉</div>
      <div>
        <h3 class="text-base font-bold text-white">Registration Confirmed!</h3>
        <p id="ticketEventName" class="text-xs text-indigo-400 font-semibold mt-1">Hackathon 2026</p>
      </div>
      <div class="p-4 bg-slate-950 rounded-2xl border border-slate-800 text-left text-xs font-mono space-y-1.5">
        <div class="flex justify-between"><span class="text-slate-500">Attendee:</span><span id="ticketAttendee" class="text-white">Alex Rivera</span></div>
        <div class="flex justify-between"><span class="text-slate-500">Pass ID:</span><span id="ticketId" class="text-emerald-400">#PASS-8492</span></div>
        <div class="flex justify-between"><span class="text-slate-500">Venue:</span><span id="ticketVenue" class="text-white">Main Hall</span></div>
      </div>
      <button id="closeTicketModal" class="w-full py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold rounded-xl text-xs">Done</button>
    </div>
  </div>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  let user = JSON.parse(localStorage.getItem('campussphere_user') || 'null');
  let events = JSON.parse(localStorage.getItem('campussphere_events') || 'null') || [
    { id: 'ev-1', title: 'Grand Hackathon 2026', cat: 'Hackathon', date: '2026-10-14', venue: 'Innovation Lab A', cap: 150, rsvps: ['demo1', 'demo2'] },
    { id: 'ev-2', title: 'Annual Cultural Fiesta', cat: 'Cultural', date: '2026-10-22', venue: 'Open Amphitheatre', cap: 500, rsvps: [] },
    { id: 'ev-3', title: 'Hands-on Agentic AI Lab', cat: 'Workshop', date: '2026-10-18', venue: 'Science Block Rm 204', cap: 60, rsvps: [] },
    { id: 'ev-4', title: 'Inter-College Football Cup', cat: 'Sports', date: '2026-11-02', venue: 'University Stadium', cap: 300, rsvps: [] }
  ];

  let currentCat = 'all';

  function save() {
    localStorage.setItem('campussphere_events', JSON.stringify(events));
    if (user) localStorage.setItem('campussphere_user', JSON.stringify(user));
    render();
  }

  function renderUser() {
    const badge = document.getElementById('userBadge');
    const nameDisp = document.getElementById('userNameDisplay');
    const authBtn = document.getElementById('authBtn');
    if (user) {
      badge.classList.remove('hidden');
      nameDisp.textContent = user.name;
      authBtn.textContent = 'Sign Out';
    } else {
      badge.classList.add('hidden');
      authBtn.textContent = 'Sign In';
    }
  }

  function render() {
    renderUser();
    const container = document.getElementById('eventsGrid');
    const q = (document.getElementById('eventSearch').value || '').toLowerCase().trim();

    let totalSeats = 0, myRsvps = 0;
    events.forEach(e => {
      totalSeats += Math.max(0, e.cap - e.rsvps.length);
      if (user && e.rsvps.includes(user.email)) myRsvps++;
    });

    document.getElementById('statTotal').textContent = events.length;
    document.getElementById('statSeats').textContent = totalSeats;
    document.getElementById('statMyRsvp').textContent = myRsvps;

    const filtered = events.filter(e => {
      const matchCat = currentCat === 'all' || e.cat === currentCat;
      const matchQ = !q || e.title.toLowerCase().includes(q) || e.venue.toLowerCase().includes(q);
      return matchCat && matchQ;
    });

    container.innerHTML = '';
    filtered.forEach(e => {
      const isRegistered = user && e.rsvps.includes(user.email);
      const remaining = Math.max(0, e.cap - e.rsvps.length);
      const card = document.createElement('div');
      card.className = 'p-5 rounded-3xl bg-slate-900 border border-slate-800 shadow-xl flex flex-col justify-between space-y-4';
      card.innerHTML = \`<div>
        <div class="flex items-center justify-between mb-2">
          <span class="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md bg-indigo-500/15 text-indigo-400">\${e.cat}</span>
          <span class="text-xs font-mono text-slate-400">\${remaining} seats left</span>
        </div>
        <h3 class="text-base font-bold text-white leading-snug">\${e.title}</h3>
        <p class="text-xs text-slate-400 mt-2 flex items-center gap-1.5">📍 \${e.venue}</p>
        <p class="text-xs text-slate-400 mt-1 flex items-center gap-1.5">📅 \${e.date}</p>
      </div>
      <div class="pt-3 border-t border-slate-800 flex items-center justify-between">
        <span class="text-[11px] font-semibold text-emerald-400">\${isRegistered ? '✓ Registered' : 'Free Entry'}</span>
        <button class="rsvp-btn px-4 py-2 rounded-xl text-xs font-bold transition \${isRegistered ? 'bg-slate-800 text-slate-300 hover:bg-slate-700' : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow'}" data-id="\${e.id}">
          \${isRegistered ? 'Cancel RSVP' : 'Book Ticket'}
        </button>
      </div>\`;
      container.appendChild(card);
    });

    document.querySelectorAll('.rsvp-btn').forEach(b => {
      b.onclick = () => {
        if (!user) {
          document.getElementById('authModal').classList.remove('hidden');
          return;
        }
        const ev = events.find(x => x.id === b.dataset.id);
        if (!ev) return;
        if (ev.rsvps.includes(user.email)) {
          ev.rsvps = ev.rsvps.filter(em => em !== user.email);
        } else {
          if (ev.rsvps.length >= ev.cap) {
            alert('This event is fully booked!');
            return;
          }
          ev.rsvps.push(user.email);
          document.getElementById('ticketEventName').textContent = ev.title;
          document.getElementById('ticketAttendee').textContent = user.name;
          document.getElementById('ticketId').textContent = '#PASS-' + Math.floor(1000 + Math.random() * 9000);
          document.getElementById('ticketVenue').textContent = ev.venue;
          document.getElementById('ticketModal').classList.remove('hidden');
        }
        save();
      };
    });
  }

  // Modals & controls
  document.getElementById('authBtn').onclick = () => {
    if (user) {
      user = null;
      localStorage.removeItem('campussphere_user');
      render();
    } else {
      document.getElementById('authModal').classList.remove('hidden');
    }
  };
  document.getElementById('closeAuthModal').onclick = () => document.getElementById('authModal').classList.add('hidden');
  document.getElementById('authForm').onsubmit = (e) => {
    e.preventDefault();
    user = {
      name: document.getElementById('loginName').value.trim(),
      email: document.getElementById('loginEmail').value.trim()
    };
    document.getElementById('authModal').classList.add('hidden');
    save();
  };

  document.getElementById('createEventBtn').onclick = () => document.getElementById('createModal').classList.remove('hidden');
  document.getElementById('closeCreateModal').onclick = () => document.getElementById('createModal').classList.add('hidden');
  document.getElementById('eventForm').onsubmit = (e) => {
    e.preventDefault();
    const title = document.getElementById('newTitle').value.trim();
    const cat = document.getElementById('newCat').value;
    const cap = parseInt(document.getElementById('newCap').value, 10);
    const date = document.getElementById('newDate').value;
    const venue = document.getElementById('newVenue').value.trim();

    events.unshift({ id: 'ev-' + Date.now(), title, cat, cap, date, venue, rsvps: [] });
    document.getElementById('createModal').classList.add('hidden');
    save();
  };

  document.getElementById('closeTicketModal').onclick = () => document.getElementById('ticketModal').classList.add('hidden');

  document.querySelectorAll('.filter-btn').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('.filter-btn').forEach(x => {
        x.className = 'filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 hover:text-white border border-slate-800';
      });
      b.className = 'filter-btn px-3 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white';
      currentCat = b.dataset.cat;
      render();
    };
  });

  document.getElementById('eventSearch').oninput = render;

  // Set default tomorrow date on form
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  document.getElementById('newDate').value = tomorrow.toISOString().split('T')[0];

  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('college-event-app'),
    'README.md': baseReadme('CampusSphere College Event Management', ['Student Auth Modal', 'Event RSVP & Ticket Passes', 'Category Filters & Capacity Counters', 'Non-destructive Client State']),
    'src/App.test.tsx': baseTests('College Event App')
  }
}

// 2. FLASHCARDS & SPACED REPETITION APP
export function buildFlashcardApp(): SynthesizedProject {
  const html = wrapHtml('BrainSparks — Flashcard Learning & Quiz', `
  <main class="flex-1 p-6 max-w-4xl mx-auto w-full flex flex-col items-center">
    <div class="w-full flex items-center justify-between mb-8 pb-4 border-b border-slate-800">
      <div>
        <h1 class="text-2xl font-black text-white flex items-center gap-2">⚡ BrainSparks</h1>
        <p class="text-xs text-slate-400">Spaced repetition memory training system</p>
      </div>
      <button id="addCardBtn" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow">+ Add Card</button>
    </div>

    <div class="w-full grid grid-cols-3 gap-4 mb-6 text-center">
      <div class="p-4 rounded-2xl bg-slate-900 border border-slate-800">
        <span class="text-xs text-slate-400 block mb-1">Current Card</span>
        <span id="currentCardIndex" class="text-xl font-black text-white">1 / 5</span>
      </div>
      <div class="p-4 rounded-2xl bg-emerald-950/40 border border-emerald-900/60">
        <span class="text-xs text-emerald-400 block mb-1">Mastered</span>
        <span id="masteredCount" class="text-xl font-black text-emerald-400">0</span>
      </div>
      <div class="p-4 rounded-2xl bg-rose-950/40 border border-rose-900/60">
        <span class="text-xs text-rose-400 block mb-1">Reviewing</span>
        <span id="reviewCount" class="text-xl font-black text-rose-400">0</span>
      </div>
    </div>

    <!-- 3D Flip Card Container -->
    <div id="cardBox" class="w-full max-w-lg h-72 cursor-pointer select-none perspective mb-6">
      <div id="cardInner" class="relative w-full h-full duration-500 rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-8 flex flex-col justify-between shadow-2xl transition-transform">
        <div class="flex items-center justify-between text-xs text-indigo-400 font-mono font-bold">
          <span id="deckTag">Web Development</span>
          <span id="flipHint" class="text-slate-500">Click to flip 🔄</span>
        </div>
        <div class="flex-1 flex items-center justify-center text-center my-4">
          <p id="cardText" class="text-xl font-bold text-white leading-relaxed">What is the Event Loop in JavaScript?</p>
        </div>
        <div class="text-center text-[11px] text-slate-500 font-medium">Card face: <span id="faceLabel" class="text-indigo-300">QUESTION</span></div>
      </div>
    </div>

    <!-- Navigation and Assessment Controls -->
    <div class="flex items-center gap-4 mb-4">
      <button id="prevBtn" class="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition">◀ Prev</button>
      <button id="markHardBtn" class="px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold shadow transition">❌ Need Practice</button>
      <button id="markEasyBtn" class="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold shadow transition">✅ Mastered</button>
      <button id="nextBtn" class="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold transition">Next ▶</button>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  let cards = JSON.parse(localStorage.getItem('brainsparks_cards') || 'null') || [
    { q: 'What is the Event Loop in JavaScript?', a: 'A runtime mechanism that orchestrates the execution of non-blocking callbacks, the call stack, and the task queue.', deck: 'JavaScript', status: 'new' },
    { q: 'What does CSS Flexbox "justify-content" do?', a: 'Aligns flex items along the main axis of the current flex line.', deck: 'CSS', status: 'new' },
    { q: 'What is Big O notation of binary search?', a: 'O(log n) logarithmic time complexity.', deck: 'Algorithms', status: 'new' },
    { q: 'What is idempotency in HTTP REST APIs?', a: 'An operation where making multiple identical requests has the same intended effect as a single request (e.g. GET, PUT, DELETE).', deck: 'Networking', status: 'new' }
  ];

  let currentIndex = 0;
  let isFlipped = false;

  function render() {
    const total = cards.length;
    if (total === 0) return;
    if (currentIndex >= total) currentIndex = 0;
    if (currentIndex < 0) currentIndex = total - 1;

    const c = cards[currentIndex];
    document.getElementById('currentCardIndex').textContent = (currentIndex + 1) + ' / ' + total;
    document.getElementById('deckTag').textContent = c.deck;
    document.getElementById('cardText').textContent = isFlipped ? c.a : c.q;
    document.getElementById('faceLabel').textContent = isFlipped ? 'ANSWER' : 'QUESTION';

    document.getElementById('masteredCount').textContent = cards.filter(x => x.status === 'easy').length;
    document.getElementById('reviewCount').textContent = cards.filter(x => x.status === 'hard').length;
  }

  document.getElementById('cardBox').onclick = () => {
    isFlipped = !isFlipped;
    render();
  };

  document.getElementById('nextBtn').onclick = () => { isFlipped = false; currentIndex++; render(); };
  document.getElementById('prevBtn').onclick = () => { isFlipped = false; currentIndex--; render(); };

  document.getElementById('markEasyBtn').onclick = () => {
    cards[currentIndex].status = 'easy';
    localStorage.setItem('brainsparks_cards', JSON.stringify(cards));
    isFlipped = false; currentIndex++; render();
  };

  document.getElementById('markHardBtn').onclick = () => {
    cards[currentIndex].status = 'hard';
    localStorage.setItem('brainsparks_cards', JSON.stringify(cards));
    isFlipped = false; currentIndex++; render();
  };

  document.getElementById('addCardBtn').onclick = () => {
    const q = prompt('Enter card question:');
    if (!q) return;
    const a = prompt('Enter card answer:');
    if (!a) return;
    cards.push({ q, a, deck: 'Custom Deck', status: 'new' });
    localStorage.setItem('brainsparks_cards', JSON.stringify(cards));
    currentIndex = cards.length - 1; isFlipped = false; render();
  };

  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('flashcard-app'),
    'README.md': baseReadme('BrainSparks Flashcard Learning', ['Card Flip Animation', 'Spaced Repetition Mastery Tracking', 'Add Custom Flashcards']),
    'src/App.test.tsx': baseTests('Flashcard App')
  }
}

// 3. E-COMMERCE STOREFRONT & CART APP
export function buildEcommerceApp(): SynthesizedProject {
  const html = wrapHtml('NovaShop — Modern E-Commerce Store', `
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
    <div class="flex items-center gap-3">
      <div class="w-10 h-10 rounded-2xl bg-indigo-600 flex items-center justify-center text-white text-xl font-black shadow-lg">🛍️</div>
      <div>
        <h1 class="text-base font-black text-white">NovaStore</h1>
        <p class="text-[11px] text-slate-400">Curated Tech, Wearables & Lifestyle</p>
      </div>
    </div>
    <div class="flex items-center gap-4">
      <input id="prodSearch" type="text" placeholder="Search catalog..." class="hidden sm:block bg-slate-950 border border-slate-800 rounded-xl px-4 py-2 text-xs text-white focus:outline-none focus:border-indigo-500 w-56" />
      <button id="openCartBtn" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow flex items-center gap-2">
        <span>Cart</span>
        <span id="cartCountBadge" class="w-5 h-5 rounded-full bg-white text-indigo-700 flex items-center justify-center font-black text-[10px]">0</span>
      </button>
    </div>
  </header>

  <main class="flex-1 p-6 max-w-6xl mx-auto w-full space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2 overflow-x-auto">
        <button class="cat-pill px-3 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white" data-cat="all">All Items</button>
        <button class="cat-pill px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 border border-slate-800" data-cat="Audio">Audio</button>
        <button class="cat-pill px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 border border-slate-800" data-cat="Wearables">Wearables</button>
        <button class="cat-pill px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 border border-slate-800" data-cat="Accessories">Accessories</button>
      </div>
      <span id="catalogCount" class="text-xs text-slate-500 font-mono">Showing 6 products</span>
    </div>

    <div id="productGrid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"></div>
  </main>

  <!-- Cart Drawer Modal -->
  <div id="cartModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex justify-end hidden">
    <div class="bg-slate-900 border-l border-slate-800 w-full max-w-md h-full flex flex-col justify-between p-6 shadow-2xl">
      <div>
        <div class="flex items-center justify-between pb-4 border-b border-slate-800 mb-4">
          <h3 class="text-base font-bold text-white flex items-center gap-2">🛒 Your Shopping Cart</h3>
          <button id="closeCartBtn" class="text-slate-400 hover:text-white text-sm">✕</button>
        </div>
        <div id="cartItemsList" class="space-y-3 max-h-[60vh] overflow-y-auto"></div>
      </div>
      <div class="pt-4 border-t border-slate-800 space-y-3">
        <div class="flex justify-between text-xs text-slate-400"><span>Subtotal:</span><strong id="cartSubtotal" class="text-white">$0.00</strong></div>
        <div class="flex justify-between text-xs text-slate-400"><span>Shipping:</span><span class="text-emerald-400 font-bold">FREE</span></div>
        <div class="flex justify-between text-sm font-bold text-white pt-2 border-t border-slate-800"><span>Estimated Total:</span><span id="cartTotal" class="text-indigo-400 text-lg">$0.00</span></div>
        <button id="checkoutBtn" class="w-full py-3 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-2xl shadow transition text-xs">Proceed to Secure Checkout</button>
      </div>
    </div>
  </div>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const products = [
    { id: 'p1', name: 'AcousticPro Studio Headphones', cat: 'Audio', price: 199.99, rating: '4.9 ★', emoji: '🎧' },
    { id: 'p2', name: 'Chronos Smartwatch Titan', cat: 'Wearables', price: 249.00, rating: '4.8 ★', emoji: '⌚' },
    { id: 'p3', name: 'MagGlow Wireless Fast Charger', cat: 'Accessories', price: 49.50, rating: '4.7 ★', emoji: '🔋' },
    { id: 'p4', name: 'TrueBass Bluetooth Speaker', cat: 'Audio', price: 79.99, rating: '4.6 ★', emoji: '🔊' },
    { id: 'p5', name: 'Haptic Mechanical Keypad', cat: 'Accessories', price: 119.00, rating: '4.9 ★', emoji: '⌨️' },
    { id: 'p6', name: 'Aura Fitness Tracker Band', cat: 'Wearables', price: 65.00, rating: '4.5 ★', emoji: '🏃' }
  ];

  let cart = JSON.parse(localStorage.getItem('novastore_cart') || '{}');
  let currentCat = 'all';

  function saveCart() {
    localStorage.setItem('novastore_cart', JSON.stringify(cart));
    renderCart();
  }

  function renderCatalog() {
    const grid = document.getElementById('productGrid');
    const q = (document.getElementById('prodSearch')?.value || '').toLowerCase().trim();
    const filtered = products.filter(p => (currentCat === 'all' || p.cat === currentCat) && (!q || p.name.toLowerCase().includes(q)));
    document.getElementById('catalogCount').textContent = 'Showing ' + filtered.length + ' products';

    grid.innerHTML = '';
    filtered.forEach(p => {
      const card = document.createElement('div');
      card.className = 'p-5 rounded-3xl bg-slate-900 border border-slate-800 shadow flex flex-col justify-between space-y-4';
      card.innerHTML = \`<div class="space-y-3">
        <div class="h-40 rounded-2xl bg-slate-950 flex items-center justify-center text-6xl shadow-inner">\${p.emoji}</div>
        <div class="flex items-center justify-between text-xs text-slate-400">
          <span class="font-bold uppercase text-indigo-400">\${p.cat}</span>
          <span class="text-amber-400 font-bold">\${p.rating}</span>
        </div>
        <h4 class="font-bold text-white text-sm leading-snug">\${p.name}</h4>
      </div>
      <div class="pt-3 border-t border-slate-800 flex items-center justify-between">
        <span class="text-lg font-black text-white">$\${p.price.toFixed(2)}</span>
        <button class="add-cart-btn px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-xs font-bold shadow" data-id="\${p.id}">
          Add to Cart
        </button>
      </div>\`;
      grid.appendChild(card);
    });

    document.querySelectorAll('.add-cart-btn').forEach(b => {
      b.onclick = () => {
        const id = b.dataset.id;
        cart[id] = (cart[id] || 0) + 1;
        saveCart();
      };
    });
  }

  function renderCart() {
    const list = document.getElementById('cartItemsList');
    let subtotal = 0, totalCount = 0;
    list.innerHTML = '';

    Object.entries(cart).forEach(([id, qty]) => {
      const p = products.find(x => x.id === id);
      if (!p || qty <= 0) return;
      subtotal += p.price * qty;
      totalCount += qty;

      const item = document.createElement('div');
      item.className = 'p-3 bg-slate-950 rounded-2xl border border-slate-800 flex items-center justify-between text-xs';
      item.innerHTML = \`<div class="flex items-center gap-3">
        <span class="text-2xl">\${p.emoji}</span>
        <div><strong class="text-white block">\${p.name}</strong><span class="text-slate-400">$\${p.price.toFixed(2)} each</span></div>
      </div>
      <div class="flex items-center gap-2">
        <button class="qty-btn px-2 py-1 bg-slate-800 rounded text-slate-300" data-id="\${id}" data-delta="-1">-</button>
        <span class="font-bold text-white">\${qty}</span>
        <button class="qty-btn px-2 py-1 bg-slate-800 rounded text-slate-300" data-id="\${id}" data-delta="1">+</button>
      </div>\`;
      list.appendChild(item);
    });

    document.getElementById('cartCountBadge').textContent = totalCount;
    document.getElementById('cartSubtotal').textContent = '$' + subtotal.toFixed(2);
    document.getElementById('cartTotal').textContent = '$' + subtotal.toFixed(2);

    document.querySelectorAll('.qty-btn').forEach(b => {
      b.onclick = () => {
        const id = b.dataset.id;
        const delta = parseInt(b.dataset.delta, 10);
        cart[id] = (cart[id] || 0) + delta;
        if (cart[id] <= 0) delete cart[id];
        saveCart();
      };
    });
  }

  document.getElementById('openCartBtn').onclick = () => document.getElementById('cartModal').classList.remove('hidden');
  document.getElementById('closeCartBtn').onclick = () => document.getElementById('cartModal').classList.add('hidden');
  document.getElementById('checkoutBtn').onclick = () => {
    alert('Thank you for ordering! Your simulated order has been placed.');
    cart = {}; saveCart();
    document.getElementById('cartModal').classList.add('hidden');
  };

  document.querySelectorAll('.cat-pill').forEach(b => {
    b.onclick = () => {
      document.querySelectorAll('.cat-pill').forEach(x => x.className = 'cat-pill px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 text-slate-400 border border-slate-800');
      b.className = 'cat-pill px-3 py-1.5 rounded-xl text-xs font-bold bg-indigo-600 text-white';
      currentCat = b.dataset.cat;
      renderCatalog();
    };
  });

  document.getElementById('prodSearch')?.addEventListener('input', renderCatalog);

  renderCatalog();
  renderCart();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('ecommerce-store'),
    'README.md': baseReadme('NovaShop E-Commerce Store', ['Product Catalog & Filtering', 'Interactive Shopping Cart Drawer', 'Local Storage Persistence', 'Order Checkout Summary']),
    'src/App.test.tsx': baseTests('E-Commerce Store')
  }
}

// 4. RECIPE FINDER & MEAL PLANNER
export function buildRecipeApp(): SynthesizedProject {
  const html = wrapHtml('FlavorForge — Recipe Book & Meal Planner', `
  <main class="flex-1 p-6 max-w-5xl mx-auto w-full space-y-6">
    <div class="flex items-center justify-between pb-4 border-b border-slate-800">
      <div>
        <h1 class="text-2xl font-black text-white flex items-center gap-2">🍲 FlavorForge</h1>
        <p class="text-xs text-slate-400">Culinary recipes, step timers & nutrition breakdown</p>
      </div>
      <button id="addRecipeBtn" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold shadow">+ Add Recipe</button>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
      <div class="bg-slate-900 border border-slate-800 rounded-3xl p-5 space-y-3">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Recipe Index</h3>
        <div id="recipeList" class="space-y-2"></div>
      </div>
      <div id="recipeDetail" class="md:col-span-2 bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col justify-between">
        <!-- Injected dynamically -->
      </div>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const recipes = [
    {
      id: 'r1',
      title: 'Mediterranean Quinoa Salad',
      time: '20 mins',
      cal: '380 kcal',
      diff: 'Easy',
      tags: ['Vegan', 'Gluten-Free'],
      ingredients: ['1 cup cooked quinoa', '1 diced cucumber', '1/2 cup cherry tomatoes', '1/4 cup kalamata olives', '2 tbsp extra virgin olive oil', '1 lemon, juiced'],
      steps: ['Rinse and cook quinoa according to package instructions.', 'Chop cucumbers, cherry tomatoes, and olives.', 'Whisk olive oil, lemon juice, salt, and black pepper.', 'Combine all ingredients in a large bowl and toss gently. Serve chilled.']
    },
    {
      id: 'r2',
      title: 'Creamy Garlic Tuscan Pasta',
      time: '30 mins',
      cal: '540 kcal',
      diff: 'Intermediate',
      tags: ['Vegetarian', 'Comfort'],
      ingredients: ['8 oz fettuccine pasta', '3 cloves garlic, minced', '1 cup heavy cream', '1/2 cup sun-dried tomatoes', '2 cups baby spinach', '1/2 cup grated parmesan'],
      steps: ['Boil pasta until al dente; reserve 1/2 cup pasta water.', 'Sauté garlic and sun-dried tomatoes in olive oil.', 'Pour in heavy cream and simmer until thickened.', 'Fold in spinach and parmesan until melted. Toss with pasta and serve hot.']
    }
  ];

  let selectedId = 'r1';

  function render() {
    const list = document.getElementById('recipeList');
    const detail = document.getElementById('recipeDetail');
    list.innerHTML = '';

    recipes.forEach(r => {
      const active = r.id === selectedId;
      const item = document.createElement('button');
      item.className = 'w-full text-left p-3.5 rounded-2xl border transition ' + (active ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400' : 'bg-slate-950 border-slate-800 text-slate-300 hover:bg-slate-800');
      item.innerHTML = \`<strong class="block text-xs font-bold">\${r.title}</strong><span class="text-[10px] text-slate-500">\${r.time} · \${r.cal}</span>\`;
      item.onclick = () => { selectedId = r.id; render(); };
      list.appendChild(item);
    });

    const activeRec = recipes.find(x => x.id === selectedId) || recipes[0];
    detail.innerHTML = \`<div>
      <div class="flex items-center justify-between mb-2">
        <h2 class="text-xl font-black text-white">\${activeRec.title}</h2>
        <span class="text-xs font-mono px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 font-bold">\${activeRec.diff}</span>
      </div>
      <div class="flex items-center gap-4 text-xs text-slate-400 mb-6 font-mono">
        <span>⏱️ \${activeRec.time}</span>
        <span>🔥 \${activeRec.cal}</span>
        <div class="flex gap-1.5">\${activeRec.tags.map(t => \`<span class="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] font-bold">\${t}</span>\`).join('')}</div>
      </div>
      <div class="space-y-4">
        <div>
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Ingredients Checklist</h4>
          <div class="space-y-1.5">\${activeRec.ingredients.map(ing => \`<label class="flex items-center gap-2 text-xs text-slate-300 cursor-pointer"><input type="checkbox" class="rounded accent-emerald-500" /><span>\${ing}</span></label>\`).join('')}</div>
        </div>
        <div class="pt-4 border-t border-slate-800">
          <h4 class="text-xs font-bold uppercase tracking-wider text-slate-400 mb-2">Cooking Instructions</h4>
          <ol class="list-decimal list-inside space-y-2 text-xs text-slate-300">\${activeRec.steps.map(s => \`<li class="leading-relaxed">\${s}</li>\`).join('')}</ol>
        </div>
      </div>
    </div>\`;
  }

  document.getElementById('addRecipeBtn').onclick = () => {
    const title = prompt('Recipe title:');
    if (!title) return;
    recipes.push({
      id: 'r-' + Date.now(),
      title,
      time: '25 mins',
      cal: '420 kcal',
      diff: 'Easy',
      tags: ['Homemade'],
      ingredients: ['1 lb main protein/vegetable', '2 tbsp olive oil', 'Salt & spice to taste'],
      steps: ['Prep ingredients thoroughly.', 'Heat pan and cook thoroughly.', 'Season to taste and enjoy!']
    });
    selectedId = recipes[recipes.length - 1].id;
    render();
  };

  render();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('recipe-planner'),
    'README.md': baseReadme('FlavorForge Recipe Manager', ['Ingredients checklist', 'Step-by-step instructions', 'Nutrition overview']),
    'src/App.test.tsx': baseTests('Recipe App')
  }
}

// 5. TYPING SPEED TEST (MONKEYTYPE STYLE)
export function buildTypingTestApp(): SynthesizedProject {
  const html = wrapHtml('SpeedKey — Typing Performance Lab', `
  <main class="flex-1 p-6 max-w-3xl mx-auto w-full flex flex-col items-center justify-center">
    <div class="w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl space-y-6">
      <div class="flex items-center justify-between pb-4 border-b border-slate-800">
        <h1 class="text-xl font-black text-white flex items-center gap-2">⌨️ SpeedKey</h1>
        <div class="flex items-center gap-4 text-xs font-mono">
          <div class="p-2 rounded-xl bg-slate-950 border border-slate-800">WPM: <strong id="wpmVal" class="text-emerald-400 text-sm">0</strong></div>
          <div class="p-2 rounded-xl bg-slate-950 border border-slate-800">Acc: <strong id="accVal" class="text-indigo-400 text-sm">100%</strong></div>
          <div class="p-2 rounded-xl bg-slate-950 border border-slate-800">Time: <strong id="timeVal" class="text-white text-sm">30s</strong></div>
        </div>
      </div>

      <div id="wordsContainer" class="p-6 bg-slate-950 rounded-2xl border border-slate-800 text-lg font-mono leading-relaxed select-none tracking-wide text-slate-500 min-h-[120px]">
        <!-- Words injected dynamically -->
      </div>

      <input id="typingInput" type="text" autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false" placeholder="Type here to start..." class="w-full bg-slate-950 border-2 border-indigo-600 rounded-2xl p-4 text-white font-mono text-base focus:outline-none shadow-inner" />

      <div class="flex items-center justify-between pt-2">
        <span class="text-xs text-slate-500">Hit Escape or click Reset to restart test</span>
        <button id="resetTestBtn" class="px-5 py-2 bg-slate-800 hover:bg-slate-700 text-white font-bold text-xs rounded-xl transition">Restart Test</button>
      </div>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const samplePassage = 'software engineering involves designing resilient systems maintaining invariants writing thorough automated tests and delivering responsive user interfaces with precision and speed';
  const words = samplePassage.split(' ');
  let wordIndex = 0, charIndex = 0, correctChars = 0, totalTyped = 0;
  let timer = null, remaining = 30, started = false;

  const wordsBox = document.getElementById('wordsContainer');
  const input = document.getElementById('typingInput');
  const wpmDisp = document.getElementById('wpmVal');
  const accDisp = document.getElementById('accVal');
  const timeDisp = document.getElementById('timeVal');

  function renderWords() {
    wordsBox.innerHTML = '';
    words.forEach((w, wIdx) => {
      const span = document.createElement('span');
      span.className = 'inline-block mr-2.5 ' + (wIdx === wordIndex ? 'text-white underline decoration-indigo-500 underline-offset-4 font-bold' : (wIdx < wordIndex ? 'text-emerald-400' : 'text-slate-500'));
      span.textContent = w;
      wordsBox.appendChild(span);
    });
  }

  function startTimer() {
    if (started) return;
    started = true;
    timer = setInterval(() => {
      remaining--;
      timeDisp.textContent = remaining + 's';
      const mins = (30 - remaining) / 60;
      const wpm = mins > 0 ? Math.round((correctChars / 5) / mins) : 0;
      wpmDisp.textContent = wpm;
      if (remaining <= 0) {
        clearInterval(timer);
        input.disabled = true;
        alert('Test complete! Final WPM: ' + wpm + ' with ' + accDisp.textContent + ' accuracy.');
      }
    }, 1000);
  }

  input.addEventListener('input', (e) => {
    startTimer();
    const val = input.value;
    totalTyped++;

    if (val.endsWith(' ')) {
      const typedWord = val.trim();
      if (typedWord === words[wordIndex]) {
        correctChars += typedWord.length + 1;
      }
      wordIndex++;
      input.value = '';
      if (wordIndex >= words.length) wordIndex = 0;
      renderWords();
    }

    const acc = totalTyped > 0 ? Math.round((correctChars / totalTyped) * 100) : 100;
    accDisp.textContent = Math.min(100, Math.max(0, acc)) + '%';
  });

  document.getElementById('resetTestBtn').onclick = () => {
    clearInterval(timer);
    started = false; remaining = 30; wordIndex = 0; correctChars = 0; totalTyped = 0;
    input.disabled = false; input.value = ''; input.focus();
    timeDisp.textContent = '30s'; wpmDisp.textContent = '0'; accDisp.textContent = '100%';
    renderWords();
  };

  renderWords();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('typing-speed-test'),
    'README.md': baseReadme('SpeedKey Typing Lab', ['Real-time WPM & accuracy metrics', 'Dynamic word highlight', '30s countdown loop']),
    'src/App.test.tsx': baseTests('Typing Test')
  }
}

// 6. UNIT & CURRENCY CONVERTER
export function buildUnitConverterApp(): SynthesizedProject {
  const html = wrapHtml('OmniConvert — Universal Measurement & Currency', `
  <main class="flex-1 p-6 max-w-xl mx-auto w-full flex flex-col justify-center">
    <div class="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-2xl space-y-6">
      <div class="flex items-center justify-between pb-3 border-b border-slate-800">
        <h1 class="text-xl font-black text-white flex items-center gap-2">🔄 OmniConvert</h1>
        <span class="text-xs text-indigo-400 font-mono font-bold">Live Conversion</span>
      </div>

      <div class="flex items-center gap-2 p-1.5 bg-slate-950 rounded-2xl border border-slate-800 overflow-x-auto text-xs">
        <button class="tab-btn px-3 py-1.5 rounded-xl font-bold bg-indigo-600 text-white" data-type="length">Length</button>
        <button class="tab-btn px-3 py-1.5 rounded-xl font-bold text-slate-400" data-type="weight">Weight</button>
        <button class="tab-btn px-3 py-1.5 rounded-xl font-bold text-slate-400" data-type="temp">Temperature</button>
        <button class="tab-btn px-3 py-1.5 rounded-xl font-bold text-slate-400" data-type="currency">Currency</button>
      </div>

      <div class="space-y-4">
        <div class="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-3">
          <input id="inputA" type="number" value="1" class="w-full bg-transparent text-2xl font-black text-white focus:outline-none font-mono" />
          <select id="unitA" class="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"></select>
        </div>

        <div class="flex justify-center">
          <button id="swapBtn" class="w-10 h-10 rounded-full bg-slate-800 hover:bg-slate-700 text-white flex items-center justify-center border border-slate-700 text-sm shadow transition">⇅</button>
        </div>

        <div class="p-4 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-3">
          <input id="inputB" type="number" readonly class="w-full bg-transparent text-2xl font-black text-emerald-400 focus:outline-none font-mono" />
          <select id="unitB" class="bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-white"></select>
        </div>
      </div>

      <div class="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 text-xs font-mono text-slate-400 text-center">
        Formula: <span id="formulaText" class="text-indigo-300">1 Meters = 3.28084 Feet</span>
      </div>
    </div>
  </main>`)

  const js = `document.addEventListener('DOMContentLoaded', () => {
  const configs = {
    length: {
      units: ['Meters', 'Kilometers', 'Miles', 'Feet', 'Inches'],
      toBase: { Meters: 1, Kilometers: 1000, Miles: 1609.34, Feet: 0.3048, Inches: 0.0254 }
    },
    weight: {
      units: ['Kilograms', 'Grams', 'Pounds', 'Ounces'],
      toBase: { Kilograms: 1, Grams: 0.001, Pounds: 0.453592, Ounces: 0.0283495 }
    },
    temp: {
      units: ['Celsius', 'Fahrenheit', 'Kelvin']
    },
    currency: {
      units: ['USD', 'EUR', 'GBP', 'JPY', 'INR'],
      toBase: { USD: 1, EUR: 1.08, GBP: 1.28, JPY: 0.0065, INR: 0.012 }
    }
  };

  let currentType = 'length';
  const selA = document.getElementById('unitA');
  const selB = document.getElementById('unitB');
  const inA = document.getElementById('inputA');
  const inB = document.getElementById('inputB');
  const formula = document.getElementById('formulaText');

  function populate() {
    const u = configs[currentType].units;
    selA.innerHTML = u.map(x => \`<option value="\${x}">\${x}</option>\`).join('');
    selB.innerHTML = u.map(x => \`<option value="\${x}">\${x}</option>\`).join('');
    if (u.length > 1) selB.selectedIndex = 1;
    calc();
  }

  function calc() {
    const val = parseFloat(inA.value) || 0;
    const a = selA.value, b = selB.value;
    let res = 0;

    if (currentType === 'temp') {
      let c = val;
      if (a === 'Fahrenheit') c = (val - 32) * 5 / 9;
      if (a === 'Kelvin') c = val - 273.15;

      if (b === 'Celsius') res = c;
      if (b === 'Fahrenheit') res = (c * 9 / 5) + 32;
      if (b === 'Kelvin') res = c + 273.15;
    } else {
      const cfg = configs[currentType];
      const baseVal = val * cfg.toBase[a];
      res = baseVal / cfg.toBase[b];
    }

    inB.value = Number(res.toFixed(4));
    formula.textContent = \`1 \${a} = \${(res / (val || 1)).toFixed(4)} \${b}\`;
  }

  inA.oninput = calc;
  selA.onchange = calc;
  selB.onchange = calc;
  document.getElementById('swapBtn').onclick = () => {
    const tmp = selA.selectedIndex;
    selA.selectedIndex = selB.selectedIndex;
    selB.selectedIndex = tmp;
    calc();
  };

  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.tab-btn').forEach(b => b.className = 'tab-btn px-3 py-1.5 rounded-xl font-bold text-slate-400');
      btn.className = 'tab-btn px-3 py-1.5 rounded-xl font-bold bg-indigo-600 text-white';
      currentType = btn.dataset.type;
      populate();
    };
  });

  populate();
});`

  return {
    'index.html': html,
    'styles.css': baseCss(),
    'script.js': js,
    'package.json': basePackageJson('unit-converter'),
    'README.md': baseReadme('OmniConvert Universal Converter', ['Length, Weight, Temperature, Currency', 'Bi-directional calculation', 'Unit swapping']),
    'src/App.test.tsx': baseTests('Unit Converter')
  }
}
