/**
 * Quantum PR Review Dashboard
 * Auto-runs review when repo + PR selected.
 * Approve & Merge via GitHub API.
 */

let selectedRepo = null;
let selectedPR = null;


let githubToken = null; // No longer needed for HttpOnly cookies

async function apiFetch(url, options = {}) {
    options.credentials = 'same-origin'; // Automatically send HttpOnly cookies
    return fetch(url, options);
}

document.addEventListener('DOMContentLoaded', () => {
    // HttpOnly Auth is handled by the server automatically setting/reading cookies.
    // The previously exposed `/api/github/callback?token=...` logic has been removed.

    setupTabs();
    setupRepoChange();
    setupPRChange();
    setupRun();
    setupActions();
    initGitHub();
    loadReport();
});

// ── GitHub Init ──────────────────────────────────────────────────────────────

async function initGitHub() {
    const chip = document.getElementById('gh-chip');
    const warn = document.getElementById('gh-warn');
    const autofixBar = document.getElementById('autofix-bar');

    try {
        const resp = await apiFetch('/api/github/status');
        const st = await resp.json();

        if (st.connected) {
            document.getElementById('gh-avatar').src = st.user.avatar_url;
            document.getElementById('gh-username').textContent = st.user.login;
            chip.style.display = 'flex';
            warn.style.display = 'none';
            await loadRepos();
        } else {
            chip.style.display = 'none';
            warn.style.display = 'flex';
            showManualFallback();
        }
    } catch (e) {
        warn.style.display = 'flex';
        showManualFallback();
    }

    autofixBar.style.display = '';
}

// ── Load Repos ───────────────────────────────────────────────────────────────

async function loadRepos() {
    const sel = document.getElementById('repo-select');
    try {
        const resp = await apiFetch('/api/github/repos');
        const data = await resp.json();
        const repos = data.repos || [];

        sel.innerHTML = '<option value="">Choose a repository</option>';
        repos.forEach(r => {
            const opt = document.createElement('option');
            opt.value = r.full_name;
            opt.textContent = r.full_name + (r.private ? ' (private)' : '');
            sel.appendChild(opt);
        });
        sel.disabled = false;
    } catch (e) {
        sel.innerHTML = '<option value="">Failed to load</option>';
    }
}

// ── Repo Change → Load PRs ──────────────────────────────────────────────────

function setupRepoChange() {
    document.getElementById('repo-select').addEventListener('change', async (e) => {
        const repo = e.target.value;
        const prSel = document.getElementById('pr-select');
        document.getElementById('btn-review').disabled = true;

        if (!repo) {
            prSel.innerHTML = '<option value="">Select a repository first</option>';
            prSel.disabled = true;
            selectedRepo = null;
            return;
        }

        selectedRepo = repo;
        prSel.innerHTML = '<option value="">Loading PRs...</option>';
        prSel.disabled = true;

        try {
            const resp = await apiFetch(`/api/github/prs?repo=${encodeURIComponent(repo)}`);
            const data = await resp.json();
            const prs = data.prs || [];

            if (!prs.length) {
                prSel.innerHTML = '<option value="">No open PRs</option>';
                return;
            }

            prSel.innerHTML = '<option value="">Choose a pull request</option>';
            prs.forEach(pr => {
                const opt = document.createElement('option');
                opt.value = pr.number;
                opt.textContent = `#${pr.number} — ${pr.title}`;
                prSel.appendChild(opt);
            });
            prSel.disabled = false;
        } catch (e) {
            prSel.innerHTML = '<option value="">Error loading PRs</option>';
        }
    });
}

// ── PR Change → AUTO-RUN REVIEW ─────────────────────────────────────────────

function setupPRChange() {
    document.getElementById('pr-select').addEventListener('change', (e) => {
        selectedPR = e.target.value ? parseInt(e.target.value, 10) : null;
        document.getElementById('btn-review').disabled = !selectedPR;

        // Auto-run the review when a PR is selected
        if (selectedRepo && selectedPR) {
            runReview();
        }
    });
}

// ── Manual Fallback ──────────────────────────────────────────────────────────

function showManualFallback() {
    const section = document.querySelector('.input-section .container');
    const grid = section.querySelector('.input-grid');

    grid.innerHTML = `
        <div class="field">
            <label class="field-label">Repository</label>
            <input type="text" class="select" id="manual-repo" value="Qiskit/qiskit" placeholder="owner/repo" style="padding-left:14px;">
        </div>
        <div class="field">
            <label class="field-label">PR Number</label>
            <input type="number" class="select" id="manual-pr" placeholder="e.g. 13456" style="padding-left:14px;">
        </div>
        <div class="field field-btn">
            <button class="btn-primary" id="btn-review" onclick="return false;">Run review</button>
        </div>
    `;

    const btn = document.getElementById('btn-review');
    const prInput = document.getElementById('manual-pr');

    prInput.addEventListener('input', () => {
        selectedRepo = document.getElementById('manual-repo').value.trim();
        selectedPR = prInput.value ? parseInt(prInput.value, 10) : null;
        btn.disabled = !selectedRepo || !selectedPR;
    });

    btn.addEventListener('click', runReview);
}

// ── Run Review ───────────────────────────────────────────────────────────────

function setupRun() {
    document.getElementById('btn-review').addEventListener('click', runReview);
}

async function runReview() {
    if (!selectedRepo || !selectedPR) return;

    const btn = document.getElementById('btn-review');
    const textEl = document.getElementById('btn-text');
    const loadEl = document.getElementById('btn-loading');
    const banner = document.getElementById('status-banner');
    const statusText = document.getElementById('status-text');

    // Show loading states
    if (textEl) textEl.style.display = 'none';
    if (loadEl) loadEl.style.display = 'inline-flex';
    btn.disabled = true;
    banner.style.display = '';
    statusText.textContent = `Running 5 specialist agents on ${selectedRepo}#${selectedPR}...`;

    // Hide previous results
    document.getElementById('results').style.display = 'none';
    document.getElementById('action-bar').style.display = 'none';

    try {
        const resp = await apiFetch('/api/review', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo: selectedRepo, pr_number: selectedPR }),
        });
        const data = await resp.json();
        if (data.error) {
            alert('Review failed: ' + data.error);
        } else {
            renderReport(data);
            document.getElementById('results').scrollIntoView({ behavior: 'smooth' });
        }
    } catch (e) {
        alert('Error: ' + e.message);
    } finally {
        btn.disabled = false;
        if (textEl) textEl.style.display = '';
        if (loadEl) loadEl.style.display = 'none';
        banner.style.display = 'none';
    }
}

// ── Tabs ─────────────────────────────────────────────────────────────────────

function setupTabs() {
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById('p-' + tab.dataset.tab).classList.add('active');
        });
    });
}

// ── Load Saved Report ────────────────────────────────────────────────────────

async function loadReport() {
    try {
        const resp = await apiFetch('/api/report');
        const data = await resp.json();
        if (!data.error && data.quality_score !== undefined) renderReport(data);
    } catch (e) { /* none saved */ }
}

// ── Render Report ────────────────────────────────────────────────────────────

function renderReport(r) {
    document.getElementById('results').style.display = '';

    // Metrics
    const score = r.quality_score || 0;
    const scoreEl = document.getElementById('m-score');
    scoreEl.textContent = score;
    scoreEl.className = 'metric-value ' + (score >= 80 ? 'v-green' : score >= 50 ? 'v-yellow' : 'v-red');

    const risk = r.risk_level || '—';
    const riskEl = document.getElementById('m-risk');
    riskEl.textContent = risk;
    riskEl.className = 'metric-value ' + (risk === 'Low' ? 'v-green' : risk === 'Medium' ? 'v-yellow' : 'v-red');

    const rec = r.overall_recommendation || '—';
    const recEl = document.getElementById('m-rec');
    recEl.textContent = rec;
    recEl.className = 'metric-value ' + (rec === 'Approve' ? 'v-green' : rec.includes('Major') ? 'v-red' : 'v-yellow');

    document.getElementById('m-total').textContent = (r.review_stats || {}).total_findings || 0;

    // Summary
    document.getElementById('summary-text').textContent = r.summary || '';
    const meta = r.meta || {};
    document.getElementById('summary-meta').innerHTML = [
        meta.pr_author ? `<span>${esc(meta.pr_author)}</span>` : '',
        `<span>${meta.files_changed_count || 0} files</span>`,
        `<span class="sm-plus">+${meta.additions || 0}</span>`,
        `<span class="sm-minus">-${meta.deletions || 0}</span>`,
        `<span>${(meta.review_duration_seconds || 0).toFixed(1)}s</span>`,
        meta.pr_url ? `<a href="${esc(meta.pr_url)}" target="_blank" style="color:var(--blue);text-decoration:none;">View PR →</a>` : '',
    ].join('');

    // Show approve/merge actions
    if (meta.repo && meta.pr_number) {
        selectedRepo = selectedRepo || meta.repo;
        selectedPR = selectedPR || meta.pr_number;
        document.getElementById('action-bar').style.display = 'flex';
        document.getElementById('action-status').textContent = '';
        document.getElementById('action-status').className = 'action-status';
    }

    // Panels
    const dims = [
        { key: 'syntax', items: r.syntax_issues || [], badge: 'b-syntax', panel: 'p-syntax' },
        { key: 'design', items: r.design_improvements || [], badge: 'b-design', panel: 'p-design' },
        { key: 'quantum', items: r.quantum_validation || [], badge: 'b-quantum', panel: 'p-quantum' },
        { key: 'perf', items: r.performance_optimizations || [], badge: 'b-perf', panel: 'p-perf' },
        { key: 'security', items: r.security_concerns || [], badge: 'b-security', panel: 'p-security' },
    ];

    dims.forEach(d => {
        document.getElementById(d.badge).textContent = d.items.length;
        const panel = document.getElementById(d.panel);

        if (!d.items.length) {
            panel.innerHTML = '<div class="empty-panel">No issues found.</div>';
            return;
        }

        panel.innerHTML = d.items.map((f, idx) => {
            const sev = (f.severity || 'info').toLowerCase();
            const file = f.file || '';
            const line = f.line ? `:${f.line}` : '';
            const fid = `finding-${d.key}-${idx}`;

            // Sample-style icons and headers
            const isAction = ['high', 'critical'].includes(sev);
            const statusLabel = isAction ? '<span class="action-label">Action required</span>' : '<span class="rec-label">Remediation recommended</span>';
            const bugIcon = d.key === 'syntax' || d.key === 'quantum' ? '🐞 Bug' : d.key === 'security' ? '⛯ Security' : '📘 Rule';

            let title = '', body = '', code = '';

            switch (d.key) {
                case 'syntax':
                    title = `${idx + 1}. ${esc(f.issue || 'Syntax issue')} ${bugIcon}`;
                    body = esc(f.category || 'General');
                    if (f.fix) code = `<div class="finding-code">${esc(f.fix)}</div>`;
                    break;
                case 'design':
                    title = `${idx + 1}. ${esc(f.issue || 'Architectural improvement')} ${bugIcon}`;
                    body = `${esc(f.category || '')} — ${esc(f.suggestion || '')}`;
                    if (f.refactor_example) code = `<div class="finding-code">${esc(f.refactor_example)}</div>`;
                    break;
                case 'quantum':
                    title = `${idx + 1}. ${esc(f.problem || 'Quantum logic error')} ${bugIcon}`;
                    body = `<strong>Reasoning:</strong> ${esc(f.mathematical_reasoning || '')}`;
                    if (f.corrected_code) code = `<div class="finding-code">${esc(f.corrected_code)}</div>`;
                    break;
                case 'perf':
                    title = `${idx + 1}. ${esc(f.issue || 'Performance bottleneck')} ${bugIcon}`;
                    body = `${esc(f.improvement || '')}<br><em>Impact: ${esc(f.estimated_impact || '')}</em>`;
                    break;
                case 'security':
                    title = `${idx + 1}. ${esc(f.risk || 'Security concern')} ${bugIcon}`;
                    body = esc(f.recommendation || '');
                    break;
            }

            const fixBtns = code ? `
                <div class="fix-actions">
                    <button class="btn-fix" onclick="applyFix('${fid}', '${file}', ${f.line || 0})">✓ Apply fix</button>
                    <button class="btn-fix-outline" onclick="copyFix('${fid}')">Copy code</button>
                </div>
            ` : '';

            return `
                <div class="finding" id="${fid}">
                    <div class="finding-head" onclick="toggleFinding('${fid}')">
                        <div class="finding-main">
                            <div class="finding-status">${statusLabel}</div>
                            <div class="finding-title">${title}</div>
                        </div>
                        <div class="finding-right">
                            <span class="finding-file">${esc(file)}${line}</span>
                            <svg class="chevron" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8 11L3 6h10z"/>
                            </svg>
                        </div>
                    </div>
                    <div class="finding-body">
                        <div class="finding-desc">${body}</div>
                        ${code}
                        ${fixBtns}
                        <div class="fix-output" id="${fid}-fix"></div>
                    </div>
                </div>
            `;
        }).join('');
    });
}

// ── Finding accordion ────────────────────────────────────────────────────────

function toggleFinding(id) {
    document.getElementById(id).classList.toggle('open');
}

// ── Auto-fix actions ─────────────────────────────────────────────────────────

async function applyFix(fid, filePath, line) {
    const fixOutput = document.getElementById(fid + '-fix');
    const findingEl = document.getElementById(fid);
    const codeEl = findingEl.querySelector('.finding-code');
    const fixCode = codeEl ? codeEl.textContent : '';

    fixOutput.textContent = 'Applying fix to GitHub branch...';
    fixOutput.className = 'fix-output visible';
    fixOutput.style.color = 'var(--blue)';

    try {
        const resp = await apiFetch('/api/fix', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                repo: selectedRepo,
                pr_number: selectedPR,
                file: filePath,
                line: Number(line),
                fix: fixCode
            }),
        });
        const data = await resp.json();
        if (data.status === 'success') {
            fixOutput.textContent = '✓ ' + data.message;
            fixOutput.style.color = 'var(--green)';
        } else {
            fixOutput.textContent = '✗ ' + (data.error || 'Failed to apply fix');
            fixOutput.style.color = 'var(--red)';
        }
    } catch (e) {
        fixOutput.textContent = '✗ Network error: ' + e.message;
        fixOutput.style.color = 'var(--red)';
    }
}

function copyFix(fid) {
    const findingEl = document.getElementById(fid);
    const codeEl = findingEl.querySelector('.finding-code');
    if (!codeEl) return;
    navigator.clipboard.writeText(codeEl.textContent).then(() => {
        const btn = findingEl.querySelector('.btn-fix-outline');
        const orig = btn.textContent;
        btn.textContent = '✓ Copied';
        setTimeout(() => { btn.textContent = orig; }, 1500);
    });
}

// ── Action Buttons Setup ─────────────────────────────────────────────────────

function setupActions() {
    document.getElementById('btn-approve').addEventListener('click', approvePR);
    document.getElementById('btn-merge').addEventListener('click', mergePR);
}

// ── Approve PR ───────────────────────────────────────────────────────────────

async function approvePR() {
    if (!selectedRepo || !selectedPR) return;
    const statusEl = document.getElementById('action-status');
    const btn = document.getElementById('btn-approve');
    btn.disabled = true;
    statusEl.textContent = 'Approving...';
    statusEl.className = 'action-status';

    try {
        const resp = await apiFetch('/api/approve', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ repo: selectedRepo, pr_number: selectedPR }),
        });
        const data = await resp.json();
        if (data.error) {
            statusEl.textContent = '✗ ' + data.error;
            statusEl.className = 'action-status error';
        } else {
            statusEl.textContent = '✓ PR approved successfully';
            statusEl.className = 'action-status success';
        }
    } catch (e) {
        statusEl.textContent = '✗ ' + e.message;
        statusEl.className = 'action-status error';
    } finally {
        btn.disabled = false;
    }
}

// ── Merge PR (with conflict handling) ────────────────────────────────────────

async function mergePR() {
    if (!selectedRepo || !selectedPR) return;
    if (!confirm(`Merge PR #${selectedPR} into the base branch?`)) return;

    const statusEl = document.getElementById('action-status');
    const btn = document.getElementById('btn-merge');
    btn.disabled = true;
    statusEl.textContent = 'Checking mergeability...';
    statusEl.className = 'action-status';
    statusEl.style.whiteSpace = 'pre-line';

    try {
        const resp = await apiFetch('/api/merge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                repo: selectedRepo,
                pr_number: Number(selectedPR),
                merge_method: 'merge',
            }),
        });
        const data = await resp.json();

        if (data.error) {
            let msg = '✗ ' + data.error;
            if (data.conflict_files && data.conflict_files.length) {
                msg += '\n\nConflicting files:\n• ' + data.conflict_files.join('\n• ');
            }
            if (data.head && data.base) {
                msg += `\n\n${data.head} → ${data.base}`;
            }
            statusEl.textContent = msg;
            statusEl.className = 'action-status error';
        } else {
            const sha = (data.sha || '').slice(0, 7);
            statusEl.textContent = `✓ PR #${selectedPR} merged successfully` + (sha ? ` (${sha})` : '');
            statusEl.className = 'action-status success';
            btn.textContent = '✓ Merged';
            btn.disabled = true;
        }
    } catch (e) {
        statusEl.textContent = '✗ Network error: ' + e.message;
        statusEl.className = 'action-status error';
        btn.disabled = false;
    }
}

// ── Utils ────────────────────────────────────────────────────────────────────

function esc(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
