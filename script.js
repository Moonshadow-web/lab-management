// 生化免疫专业组速查工具 JavaScript 逻辑

// ============================================================
// 登录模块
// ============================================================

const LOGIN_USER = 'mhzyy';
const LOGIN_PASS = '123456';
const REMEMBER_KEY = 'lab_remember';
const SESSION_KEY  = 'lab_logged_in';

(function initLogin() {
    const mask = document.getElementById('login-mask');

    // 已在本次会话登录过 → 直接隐藏遮罩
    if (sessionStorage.getItem(SESSION_KEY) === '1') {
        mask.classList.add('hidden');
        setTimeout(() => mask.style.display = 'none', 400);
        return;
    }

    // 读取记住的账号密码
    const remembered = JSON.parse(localStorage.getItem(REMEMBER_KEY) || 'null');
    if (remembered) {
        document.getElementById('login-username').value = remembered.u || '';
        document.getElementById('login-password').value = remembered.p || '';
        document.getElementById('login-remember').checked = true;
    }
})();

function doLogin() {
    const u   = document.getElementById('login-username').value.trim();
    const p   = document.getElementById('login-password').value;
    const rem = document.getElementById('login-remember').checked;
    const err = document.getElementById('login-error');

    if (!u || !p) { err.textContent = '请输入账号和密码'; return; }
    if (u !== LOGIN_USER || p !== LOGIN_PASS) {
        err.textContent = '账号或密码错误，请重新输入';
        document.getElementById('login-password').value = '';
        return;
    }

    // 登录成功
    err.textContent = '';
    sessionStorage.setItem(SESSION_KEY, '1');

    if (rem) {
        localStorage.setItem(REMEMBER_KEY, JSON.stringify({ u, p }));
    } else {
        localStorage.removeItem(REMEMBER_KEY);
    }

    const mask = document.getElementById('login-mask');
    mask.classList.add('hidden');
    setTimeout(() => mask.style.display = 'none', 400);
}



// ============================================================
// 模糊搜索工具函数
// ============================================================

/**
 * 将搜索词拆分为多个关键词（支持空格、逗号、顿号分隔）
 * 返回去重后的非空词组
 */
function splitKeywords(term) {
    return term.toLowerCase()
        .split(/[\s,，、/]+/)
        .map(w => w.trim())
        .filter(w => w.length > 0);
}

/**
 * 构建每个项目的全文搜索字符串（把所有可搜字段拼在一起）
 */
function buildSearchText(item) {
    return [
        item.name || '',
        item.code || '',
        item.aliases || '',
        item.category || '',
        item.instrument || '',
        item.instrumentGroup || '',
        item.unit || '',
    ].join(' ').toLowerCase();
}

/**
 * 模糊匹配：所有关键词都必须在searchText中出现（AND逻辑）
 */
function fuzzyMatch(searchText, keywords) {
    return keywords.every(kw => searchText.includes(kw));
}

/**
 * 高亮文本中的关键词
 */
function highlight(text, keywords) {
    if (!text || !keywords || keywords.length === 0) return text;
    let result = text;
    keywords.forEach(kw => {
        if (!kw) return;
        const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const re = new RegExp(`(${escaped})`, 'gi');
        result = result.replace(re, '<mark>$1</mark>');
    });
    return result;
}

// 当前搜索关键词（供高亮用）
let currentKeywords = [];

// ============================================================
// 标签页切换
// ============================================================
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        this.classList.add('active');
        const tabId = this.getAttribute('data-tab');
        document.getElementById(tabId).classList.add('active');
        // 切换到说明书tab时自动展示全部
        if (tabId === 'manual') { searchManual(); }
        // 切换到文件检索tab时自动展示全部
        if (tabId === 'files')      { searchFiles();       }
        if (tabId === 'instrument') { searchInstruments(); }
    });
});

// ============================================================
// 搜索性能项目（模糊 + 分词 + 别名）
// ============================================================
function searchPerformance() {
    const rawTerm = document.getElementById('performance-search').value.trim();
    const category = document.getElementById('performance-category').value;
    const instrument = document.getElementById('performance-instrument').value;
    const group = document.getElementById('performance-group').value;

    currentKeywords = splitKeywords(rawTerm);

    let results = performanceData.filter(item => {
        const matchSearch = currentKeywords.length === 0 ||
            fuzzyMatch(buildSearchText(item), currentKeywords);

        const matchCategory = !category || item.category === category;
        const matchInstrument = !instrument || item.instrument === instrument;
        // 机台：item.instrumentGroup 可能是"③号机 / 急诊"这样的复合值
        // 只要包含所选机台关键词即可
        const matchGroup = !group ||
            (item.instrumentGroup && item.instrumentGroup.includes(group));

        return matchSearch && matchCategory && matchInstrument && matchGroup;
    });

    // 相关性排序：有搜索词时按匹配优先级排列
    if (currentKeywords.length > 0) {
        results = results.map(item => {
            const kws = currentKeywords;
            const codeLower = (item.code || '').toLowerCase();
            const nameLower = (item.name || '').toLowerCase();
            // 别名中的独立词组（按空格分割）
            const aliasWords = (item.aliases || '').toLowerCase().split(/\s+/);

            let score = 0;
            kws.forEach(kw => {
                // code 完整相等 ─ 最高优先
                if (codeLower === kw) score += 100;
                // code 起始匹配
                else if (codeLower.startsWith(kw)) score += 80;
                // code 包含
                else if (codeLower.includes(kw)) score += 60;

                // name 包含
                if (nameLower.includes(kw)) score += 40;

                // aliases 中某个独立词完整匹配（如 "ACE" 命中 aliases 里的 ACE 词）
                if (aliasWords.some(w => w === kw)) score += 50;
                // aliases 中某个独立词起始匹配
                else if (aliasWords.some(w => w.startsWith(kw))) score += 30;
            });
            return { item, score };
        }).sort((a, b) => b.score - a.score).map(x => x.item);
    }

    displayPerformanceResults(results);
}

// 仪器切换时联动刷新机台下拉
function onInstrumentChange() {
    const instrument = document.getElementById('performance-instrument').value;
    updateGroupDropdown(instrument);
    searchPerformance();
}

// 搜索试剂存放（同时搜索发光定标品）
function searchReagent() {
    const searchTerm = document.getElementById('reagent-search').value.toLowerCase().trim();
    const location = document.getElementById('reagent-location').value;
    const status = document.getElementById('reagent-status').value;

    // 搜索试剂存放数据
    let reagentResults = reagentData.filter(item => {
        const matchSearch = !searchTerm ||
            item.name.toLowerCase().includes(searchTerm) ||
            item.catalogNumber.toLowerCase().includes(searchTerm) ||
            item.specification.toLowerCase().includes(searchTerm) ||
            item.manufacturer.toLowerCase().includes(searchTerm);

        const matchLocation = !location || item.location === location;
        const matchStatus = !status || item.status === status;

        return matchSearch && matchLocation && matchStatus;
    });
    displayReagentResults(reagentResults);

    // 同步搜索发光定标品数据（仅在有关键词时搜索）
    if (searchTerm) {
        const calibData = (typeof calibrationData !== 'undefined') ? calibrationData : [];
        const calibResults = calibData.filter(item =>
            item.name.toLowerCase().includes(searchTerm) ||
            item.code.toLowerCase().includes(searchTerm)
        );
        calibDisplayResults(calibResults);
    } else {
        // 无关键词时隐藏定标品区域
        document.getElementById('calib-section').style.display = 'none';
    }
}


/**
 * 构建说明书条目的全文搜索字符串（包含所有可检索字段）
 */
function buildManualSearchText(item) {
    return [
        item.name || '',
        item.aliases || '',
        item.brand || '',
        item.series || '',
        item.catalogNumber || '',
        item.method || '',
        item.category || '',
    ].join(' ').toLowerCase();
}

// 说明书模块当前关键词（供高亮用）
let manualKeywords = [];

// 搜索试剂说明书
function searchManual() {
    const raw = document.getElementById('manual-search').value;
    const brandFilter   = document.getElementById('manual-brand')    ? document.getElementById('manual-brand').value    : '';
    const categoryFilter = document.getElementById('manual-category') ? document.getElementById('manual-category').value : '';

    const kws = splitKeywords(raw);   // 复用项目查询的多关键词拆分
    manualKeywords = kws;

    let results = manualData.filter(item => {
        const searchText = buildManualSearchText(item);
        // 多关键词AND模糊匹配（复用fuzzyMatch）
        const matchSearch = kws.length === 0 || fuzzyMatch(searchText, kws);
        const matchBrand    = !brandFilter    || (item.brand || '').includes(brandFilter);
        const matchCategory = !categoryFilter || (item.category || '') === categoryFilter;
        return matchSearch && matchBrand && matchCategory;
    });

    // 相关性排序：关键词命中 name 或 aliases 权重更高
    if (kws.length > 0) {
        results.sort((a, b) => {
            const scoreItem = (item) => {
                let s = 0;
                const name = (item.name || '').toLowerCase();
                const als  = (item.aliases || '').toLowerCase();
                const cat  = (item.catalogNumber || '').toLowerCase();
                kws.forEach(kw => {
                    if (name.startsWith(kw))      s += 60;
                    else if (name.includes(kw))   s += 40;
                    if (als.split(' ').some(w => w === kw))         s += 50;
                    else if (als.split(' ').some(w => w.startsWith(kw))) s += 30;
                    if (cat.includes(kw))         s += 20;
                });
                return s;
            };
            return scoreItem(b) - scoreItem(a);
        });
    }

    displayManualResults(results);
}

/**
 * 构建文件条目的全文搜索字符串
 */
function buildFileSearchText(item) {
    return [
        item.name || '',
        item.code || '',
        item.keywords || '',
        item.description || '',
        item.category || '',
        item.type || '',
        item.author || '',
    ].join(' ').toLowerCase();
}

// 文件检索当前关键词（供高亮用）
let fileKeywords = [];

// ═══════════════════════════════════════════════════════════════
// 仪器设备查询模块
// ═══════════════════════════════════════════════════════════════

let instrumentKeywords = [];

function buildInstrumentSearchText(item) {
    return [
        item.name    || '',
        item.model   || '',
        item.brand   || '',
        item.category|| '',
        item.location|| '',
        item.serialNo|| '',
        item.deptNo  || '',
        item.owner   || '',
    ].join(' ').toLowerCase();
}

function searchInstruments() {
    const raw            = document.getElementById('instrument-search').value;
    const categoryFilter = document.getElementById('instrument-category').value;
    const statusFilter   = document.getElementById('instrument-status').value;

    const kws = splitKeywords(raw);
    instrumentKeywords = kws;

    let results = instrumentData.filter(item => {
        const matchSearch   = kws.length === 0 || fuzzyMatch(buildInstrumentSearchText(item), kws);
        const matchCategory = !categoryFilter || item.category === categoryFilter;
        const matchStatus   = !statusFilter   || item.status   === statusFilter;
        return matchSearch && matchCategory && matchStatus;
    });

    // 相关性排序：名称或型号命中权重更高
    if (kws.length > 0) {
        results.sort((a, b) => {
            const score = item => {
                let s = 0;
                const name  = (item.name  || '').toLowerCase();
                const model = (item.model || '').toLowerCase();
                kws.forEach(kw => {
                    if (name.startsWith(kw))    s += 60;
                    else if (name.includes(kw)) s += 40;
                    if (model.includes(kw))     s += 20;
                });
                return s;
            };
            return score(b) - score(a);
        });
    }

    displayInstrumentResults(results);
}

function displayInstrumentResults(results) {
    const container = document.getElementById('instrument-results');
    const countEl   = document.getElementById('instrument-count');
    countEl.textContent = `共 ${results.length} 台设备`;

    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">未找到匹配的仪器设备，请调整查询条件</div>';
        return;
    }

    const kws = instrumentKeywords;

    const catColors = {
        '生化分析': '#e3f2fd',
        '化学发光': '#fce4ec',
        '凝血分析': '#fff8e1',
        '血气分析': '#e8f5e9',
        '特殊检测': '#f3e5f5',
        '质谱系统': '#e8eaf6',
        '离心机':   '#e0f7fa',
        '冰箱冷冻': '#e3f2fd',
        '辅助设备': '#f5f5f5',
    };

    const v = (val, kws) => val ? highlight(val, kws) : '<span style="color:#bbb;">—</span>';

    container.innerHTML = results.map(item => {
        const catBg     = catColors[item.category] || '#f5f5f5';
        const isRetired = item.status === '已停用';
        const statusBadge = isRetired
            ? '<span class="result-badge badge-danger">停用</span>'
            : '<span class="result-badge badge-success">在用</span>';

        return `
        <div class="result-item instrument-item${isRetired ? ' instrument-retired' : ''}">
            <div class="instrument-card-header">
                <div class="instrument-title-row">
                    <span class="result-title">${highlight(item.name, kws)}</span>
                    <span class="manual-cat-tag" style="background:${catBg};margin-left:8px;">${item.category}</span>
                </div>
                <div class="instrument-header-right">
                    ${statusBadge}
                    <button class="btn-view" onclick="openInstrumentFile(${item.id})" style="margin-left:8px;">查看设备表</button>
                </div>
            </div>
            <table class="instrument-info-table">
                <tbody>
                    <tr>
                        <td class="info-label">科室编号</td>
                        <td class="info-value">${v(item.deptNo, kws)}</td>
                        <td class="info-label">规格型号</td>
                        <td class="info-value">${v(item.model, kws)}</td>
                    </tr>
                    <tr>
                        <td class="info-label">生产厂家</td>
                        <td class="info-value">${v(item.brand, kws)}</td>
                        <td class="info-label">出厂编号</td>
                        <td class="info-value">${v(item.serialNo, kws)}</td>
                    </tr>
                    <tr>
                        <td class="info-label">购入日期</td>
                        <td class="info-value">${v(item.purchaseDate, kws)}</td>
                        <td class="info-label">启用日期</td>
                        <td class="info-value">${v(item.startDate, kws)}</td>
                    </tr>
                    <tr>
                        <td class="info-label">存放位置</td>
                        <td class="info-value">${v(item.location, kws)}</td>
                        <td class="info-label">设备负责人</td>
                        <td class="info-value">${v(item.owner, kws)}</td>
                    </tr>
                </tbody>
            </table>
        </div>`;
    }).join('');
}

function openInstrumentFile(id) {
    const item = instrumentData.find(r => r.id === id);
    if (!item || !item.filePath) { alert('未找到文件路径'); return; }
    const url = 'file:///' + item.filePath.replace(/\\/g, '/');
    window.open(url, '_blank');
}

// ═══════════════════════════════════════════════════════════════
// 文件检索模块
// ═══════════════════════════════════════════════════════════════

// 搜索文件

function searchFiles() {
    const raw = document.getElementById('file-search').value;
    const fileType     = document.getElementById('file-type').value;
    const fileCategory = document.getElementById('file-category') ? document.getElementById('file-category').value : '';

    const kws = splitKeywords(raw);
    fileKeywords = kws;

    let results = fileData.filter(item => {
        const searchText = buildFileSearchText(item);
        const matchSearch = kws.length === 0 || fuzzyMatch(searchText, kws);
        const matchType     = !fileType     || item.type === fileType;
        const matchCategory = !fileCategory || item.category === fileCategory;
        return matchSearch && matchType && matchCategory;
    });

    // 相关性排序：编号或名称完全匹配权重更高
    if (kws.length > 0) {
        results.sort((a, b) => {
            const score = (item) => {
                let s = 0;
                const name = (item.name || '').toLowerCase();
                const code = (item.code || '').toLowerCase();
                kws.forEach(kw => {
                    if (name.startsWith(kw))    s += 60;
                    else if (name.includes(kw)) s += 40;
                    if (code.includes(kw))      s += 30;
                });
                return s;
            };
            return score(b) - score(a);
        });
    }

    displayFileResults(results);
}

// 显示性能项目结果（含关键词高亮）
function displayPerformanceResults(results) {
    const container = document.getElementById('performance-results');
    const countEl = document.getElementById('performance-count');
    countEl.textContent = `共 ${results.length} 条记录`;

    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">未找到匹配的项目，请调整查询条件</div>';
        return;
    }

    const kws = currentKeywords;

    container.innerHTML = results.map(item => {
        // 别名中去掉中文说明，只显示英文缩写部分（前几个token）
        const aliasTokens = (item.aliases || '').split(' ').filter(t => /^[A-Za-z0-9αβγ\-_\.\/\[\]]+$/.test(t));
        const aliasDisplay = aliasTokens.length ? aliasTokens.join(' / ') : '';

        return `
        <div class="result-item">
            <div class="result-header">
                <div>
                    <div class="result-title">
                        ${highlight(item.name, kws)}
                        <span class="result-code-inline">（${highlight(item.code, kws)}）</span>
                    </div>
                    <div class="result-code">
                        ${aliasDisplay ? `<span class="alias-tag">${highlight(aliasDisplay, kws)}</span>` : ''}
                        <span class="instrument-name">${item.instrument}</span>
                        ${item.instrumentGroup ? item.instrumentGroup.split(/\s*\/\s*/).map(g =>
                            `<span class="group-tag">${highlight(g.trim(), kws)}</span>`
                        ).join('') : ''}
                        ${item.detectionMethod ? `<span class="method-tag"><span class="method-tag-label">方法</span>${item.detectionMethod}</span>` : ''}
                        ${item.reagentBrand ? `<span class="brand-tag"><span class="brand-tag-label">品牌</span>${item.reagentBrand}</span>` : ''}
                    </div>
                </div>
                <span class="result-badge ${item.category === '生化' ? 'badge-success' : 'badge-primary'}">${item.category}</span>
            </div>
            <div class="result-body">
                <div class="result-grid">
                    <div class="result-field">
                        <span class="field-label">单位</span>
                        <span class="field-value">${item.unit}</span>
                    </div>
                    <div class="result-field">
                        <span class="field-label">稀释倍数</span>
                        <span class="field-value">${item.dilutionFold}</span>
                    </div>
                    <div class="result-field">
                        <span class="field-label">稀释液</span>
                        <span class="field-value">${item.diluent}</span>
                    </div>
                </div>
                <div class="result-field-full">
                    <span class="field-label">参考范围</span>
                    <span class="field-value ref-value">${highlight(item.reference, kws)}</span>
                </div>
                <div class="result-field-full">
                    <span class="field-label">线性范围</span>
                    <span class="field-value">${item.linearRange}</span>
                </div>
                <div class="result-field-full">
                    <span class="field-label">可报告范围</span>
                    <span class="field-value">${item.reportableRange}</span>
                </div>
                <div class="result-field-full">
                    <span class="field-label">校准品</span>
                    <span class="field-value">${item.calibrator || '—'}</span>
                </div>
                <div class="result-field-full">
                    <span class="field-label">溯源性</span>
                    <span class="field-value trace-value">${item.traceability || '—'}</span>
                </div>
                ${(item.interferenceHemolysis || item.interferenceBilirubin || item.interferenceLipemia) ? `
                <div class="result-interference-block">
                    <div class="result-interference-title">📊 抗干扰性能</div>
                    <div class="result-interference-grid">
                        <div class="result-interference-item">
                            <span class="interference-label hemolysis-label">🩸 溶血</span>
                            <span class="interference-value ${item.interferenceHemolysis === '受干扰' ? 'interference-warn' : ''}">${item.interferenceHemolysis || '—'}</span>
                        </div>
                        <div class="result-interference-item">
                            <span class="interference-label bilirubin-label">🟡 黄疸</span>
                            <span class="interference-value ${item.interferenceBilirubin === '受干扰' ? 'interference-warn' : ''}">${item.interferenceBilirubin || '—'}</span>
                        </div>
                        <div class="result-interference-item">
                            <span class="interference-label lipemia-label">🥛 脂血</span>
                            <span class="interference-value ${item.interferenceLipemia === '受干扰' ? 'interference-warn' : ''}">${(item.interferenceLipemia === '/' ? '不受干扰' : item.interferenceLipemia) || '—'}</span>
                        </div>
                    </div>
                </div>` : ''}
            </div>
            <div class="result-footer">
                <div class="result-meta">更新于：${item.lastUpdate}</div>
            </div>
        </div>`;
    }).join('');
}

// 显示试剂存放结果
function displayReagentResults(results) {
    const container = document.getElementById('reagent-results');
    const countEl = document.getElementById('reagent-count');
    countEl.textContent = `共 ${results.length} 条记录`;

    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">未找到匹配的试剂，请调整查询条件</div>';
        return;
    }

    const statusClass = {
        '正常': 'normal',
        '临期': 'warning',
        '过期': 'danger'
    };

    const badgeClass = {
        '正常': 'badge-success',
        '临期': 'badge-warning',
        '过期': 'badge-danger'
    };

    container.innerHTML = results.map(item => `
        <div class="result-item ${statusClass[item.status]}">
            <div class="result-header">
                <div>
                    <div class="result-title">${item.name}</div>
                    <div class="result-code">货号: ${item.catalogNumber} | 规格: ${item.specification}</div>
                </div>
                <span class="result-badge ${badgeClass[item.status]}">${item.status}</span>
            </div>
            <div class="result-body">
                <p><strong>生产厂家:</strong> ${item.manufacturer}</p>
                <p><strong>存放位置:</strong> ${item.location} | <strong>保存温度:</strong> ${item.temperature}</p>
                <p><strong>库存数量:</strong> ${item.quantity} | <strong>批号:</strong> ${item.batchNumber}</p>
                <p><strong>有效期:</strong> ${item.expiryDate}</p>
            </div>
            <div class="result-footer">
                <div class="result-meta">更新于: ${item.lastUpdate}</div>
                <div class="result-actions">
                    <button class="btn-view" onclick="viewReagentDetails(${item.id})">查看详情</button>
                </div>
            </div>
        </div>
    `).join('');
}

// 显示试剂说明书结果
function displayManualResults(results) {
    const container = document.getElementById('manual-results');
    const countEl = document.getElementById('manual-count');
    countEl.textContent = `共 ${results.length} 条记录`;

    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">未找到匹配的说明书，请调整查询条件</div>';
        return;
    }

    const categoryColors = {
        '肝功能': '#e8f5e9', '肾功能': '#e3f2fd', '血脂': '#fff8e1', '电解质': '#f3e5f5',
        '心肌酶': '#fce4e4', '心血管': '#fce4e4', '炎症': '#fff3e0', '甲状腺': '#e0f7fa',
        '生殖': '#fce4ec', '骨代谢': '#efebe9', '贫血': '#e8eaf6', '糖代谢': '#f9fbe7',
        '胰腺功能': '#e0f2f1', '微量元素': '#ede7f6', '特种蛋白': '#e8f5e9',
        '代谢': '#e3f2fd', '耗材': '#f5f5f5', '脓毒症': '#fce4e4',
        '肾早损': '#e3f2fd', '其他生化': '#f5f5f5',
    };

    const kws = manualKeywords;

    container.innerHTML = results.map(item => {
        const catColor = categoryColors[item.category] || '#f5f5f5';

        // 提取英文别名中被关键词命中的词，用于展示
        const aliasTokens = (item.aliases || '').split(/\s+/).filter(t => t);
        const hitAliases = kws.length > 0
            ? aliasTokens.filter(t => kws.some(kw => t.toLowerCase().startsWith(kw.toLowerCase())))
            : [];

        return `
        <div class="result-item manual-item">
            <div class="result-header">
                <div style="flex:1;min-width:0;">
                    <div class="result-title">${highlight(item.name, kws)}</div>
                    <div class="result-code" style="flex-wrap:wrap;gap:4px;">
                        <span class="instrument-name">${item.brand}</span>
                        ${item.series ? `<span class="group-tag">${item.series}</span>` : ''}
                        <span class="method-tag"><span class="method-tag-label">方法</span>${highlight(item.method || '—', kws)}</span>
                        <span class="manual-cat-tag" style="background:${catColor}">${item.category || '—'}</span>
                        ${hitAliases.length ? `<span class="alias-tag manual-alias-tag">${hitAliases.map(a => highlight(a, kws)).join(' / ')}</span>` : ''}
                    </div>
                </div>
                <span class="result-badge badge-primary">PDF</span>
            </div>
            <div class="result-body" style="padding:6px 0 2px;">
                <span class="manual-catalog">货号：${highlight(item.catalogNumber, kws)}</span>
            </div>
            <div class="result-footer">
                <div class="result-meta">收录于：${item.uploadDate}</div>
                <div class="result-actions">
                    <button class="btn-view" onclick="viewManual(${item.id})">打开PDF</button>
                    <button class="btn-download" onclick="downloadManual(${item.id})">下载</button>
                </div>
            </div>
        </div>`;
    }).join('');
}

// 显示文件检索结果
function displayFileResults(results) {
    const container = document.getElementById('file-results');
    const countEl = document.getElementById('file-count');
    countEl.textContent = `共 ${results.length} 条记录`;

    if (results.length === 0) {
        container.innerHTML = '<div class="no-data">未找到匹配的文件，请调整查询条件</div>';
        return;
    }

    const kws = fileKeywords;

    const typeColors = {
        'SOP':    'badge-primary',
        '记录表格': 'badge-success',
        '质控':   'badge-warning',
        '培训':   'badge-success',
        '其他':   'badge-danger'
    };

    const fmtColors = {
        'DOCX': '#e3f2fd', 'DOC': '#e3f2fd',
        'XLSX': '#e8f5e9', 'XLS': '#e8f5e9',
        'PDF':  '#fce4e4',
    };

    const catColors = {
        '通用作业指导书': '#e3f2fd',
        '项目作业指导书': '#e8eaf6',
        '仪器作业指导书': '#e8f5e9',
        '质量管理':   '#fce4e4',
        '记录表格':   '#f5f5f5',
    };

    container.innerHTML = results.map(item => {
        const fmtBg  = fmtColors[item.format]  || '#f5f5f5';
        const catBg  = catColors[item.category] || '#f5f5f5';
        return `
        <div class="result-item file-item">
            <div class="result-header">
                <div style="flex:1;min-width:0;">
                    <div class="result-title">${highlight(item.name, kws)}</div>
                    <div class="result-code" style="flex-wrap:wrap;gap:4px;margin-top:3px;">
                        ${item.code ? `<span class="alias-tag" style="font-family:monospace;">${highlight(item.code, kws)}</span>` : ''}
                        <span class="manual-cat-tag" style="background:${catBg}">${item.category}</span>
                        <span class="manual-cat-tag" style="background:${fmtBg};color:#555;">${item.format}</span>
                        <span class="manual-catalog" style="color:#888;">${item.fileSize}</span>
                    </div>
                </div>
                <span class="result-badge ${typeColors[item.type] || 'badge-primary'}">${item.type}</span>
            </div>
            <div class="result-body" style="padding:4px 0 2px;">
                <span class="manual-catalog">${highlight(item.description, kws)}</span>
            </div>
            <div class="result-footer">
                <div class="result-meta">版本：${item.version} &nbsp;|&nbsp; 收录于：${item.uploadDate}</div>
                <div class="result-actions">
                    <button class="btn-view"     onclick="viewFile(${item.id})">打开文件</button>
                    <button class="btn-download" onclick="downloadFile(${item.id})">下载</button>
                </div>
            </div>
        </div>`;
    }).join('');
}

// 打开文件（本地路径）
function viewFile(id) {
    const item = fileData.find(r => r.id === id);
    if (!item || !item.filePath) { alert('未找到该文件'); return; }
    const url = 'file:///' + item.filePath.replace(/\\/g, '/');
    window.open(url, '_blank');
}

// 下载文件
function downloadFile(id) {
    const item = fileData.find(r => r.id === id);
    if (!item || !item.filePath) { alert('未找到该文件'); return; }
    const url = 'file:///' + item.filePath.replace(/\\/g, '/');
    const a = document.createElement('a');
    a.href = url;
    a.download = item.filePath.split('/').pop();
    a.click();
}

function viewReagentDetails(id) {
    const item = reagentData.find(r => r.id === id);
    if (item) {
        alert(`查看详情：\n\n试剂：${item.name}\n货号：${item.catalogNumber}\n存放位置：${item.location}\n库存：${item.quantity}\n\n详情展示功能可根据需要进一步开发`);
    }
}

// 文件预览和下载功能
function viewManual(id) {
    const item = manualData.find(r => r.id === id);
    if (!item || !item.pdfPath) { alert('未找到该说明书文件'); return; }
    // 先用 fetch 检测文件是否存在，再决定是否打开
    fetch(item.pdfPath, { method: 'HEAD' })
        .then(res => {
            if (res.ok) {
                window.open(item.pdfPath, '_blank');
            } else {
                alert('该说明书文件暂未上传，请联系管理员补充。\n\n文件名：' + item.pdfPath.split('/').pop());
            }
        })
        .catch(() => {
            // 网络无法 HEAD 请求时直接尝试打开
            window.open(item.pdfPath, '_blank');
        });
}

function downloadManual(id) {
    const item = manualData.find(r => r.id === id);
    if (!item || !item.pdfPath) { alert('未找到该说明书文件'); return; }
    fetch(item.pdfPath, { method: 'HEAD' })
        .then(res => {
            if (res.ok) {
                const a = document.createElement('a');
                a.href = item.pdfPath;
                a.download = item.pdfPath.split('/').pop();
                a.click();
            } else {
                alert('该说明书文件暂未上传，请联系管理员补充。\n\n文件名：' + item.pdfPath.split('/').pop());
            }
        })
        .catch(() => {
            const a = document.createElement('a');
            a.href = item.pdfPath;
            a.download = item.pdfPath.split('/').pop();
            a.click();
        });
}


// 添加回车搜索功能
document.querySelectorAll('.search-box input').forEach(input => {
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            const btn = this.parentElement.querySelector('.search-btn');
            if (btn) btn.click();
        }
    });
});

// ============================================================
// 发光项目定标信息模块
// ============================================================

function searchCalibration() {
    // 兼容旧入口：从试剂搜索框取词
    const kw = (document.getElementById('reagent-search').value || '').trim().toLowerCase();
    if (!kw) { alert('请在搜索框输入关键词'); return; }
    const data = (typeof calibrationData !== 'undefined') ? calibrationData : [];
    const results = data.filter(item =>
        item.name.toLowerCase().includes(kw) ||
        item.code.toLowerCase().includes(kw)
    );
    calibDisplayResults(results);
}

function calibShowAll() {
    const data = (typeof calibrationData !== 'undefined') ? calibrationData : [];
    calibDisplayResults(data);
}

function calibDisplayResults(results) {
    const sectionEl = document.getElementById('calib-section');
    const emptyEl   = document.getElementById('calib-empty');
    const wrapEl    = document.getElementById('calib-results-wrap');
    const listEl    = document.getElementById('calib-results');
    const countEl   = document.getElementById('calib-count');

    // 显示定标品区域
    sectionEl.style.display = 'block';

    if (results.length === 0) {
        emptyEl.style.display = 'block';
        wrapEl.style.display  = 'none';
        return;
    }

    emptyEl.style.display = 'none';
    wrapEl.style.display  = 'block';
    countEl.textContent   = `共 ${results.length} 条记录`;

    listEl.innerHTML = results.map(item => `
        <div class="calib-card">
            <div class="calib-card-title">${item.name}</div>
            <div class="calib-card-grid">
                <div class="calib-card-row"><span class="calib-card-label">分类</span><span class="calib-card-value">${item.type}</span></div>
                <div class="calib-card-row"><span class="calib-card-label">规格</span><span class="calib-card-value">${item.spec}</span></div>
                <div class="calib-card-row"><span class="calib-card-label">保存温度</span><span class="calib-card-value calib-temp">${item.storeTemp} °C</span></div>
                <div class="calib-card-row"><span class="calib-card-label">效期</span><span class="calib-card-value">${item.validity}</span></div>
                <div class="calib-card-row"><span class="calib-card-label">开瓶后储存</span><span class="calib-card-value calib-temp">${item.openStoreTemp} °C</span></div>
                <div class="calib-card-row"><span class="calib-card-label">开瓶后稳定期</span><span class="calib-card-value">${item.openStability}</span></div>
                <div class="calib-card-row"><span class="calib-card-label">复溶</span><span class="calib-card-value">${item.reconstitution}</span></div>
                ${item.note ? `<div class="calib-card-row calib-card-row--full"><span class="calib-card-label">备注</span><span class="calib-card-value calib-note">${item.note}</span></div>` : ''}
            </div>
        </div>
    `).join('');
}


// ============================================================
// 标本采集手册模块
// ============================================================

// 同义词映射（与原手册保持一致）
const specimenSynonyms = {
    '丙肝': '丙型肝炎', '乙肝': '乙型肝炎', '甲肝': '甲型肝炎', '戊肝': '戊型肝炎',
    '甲功': '甲状腺功能', '肾功': '肾功能', '肝功': '肝功能',
    '血常规': '血细胞分析', '尿常规': '尿液分析',
    '乙肝三系': '乙肝五项', '乙肝两对半': '乙肝五项',
    'hcv': '丙型肝炎', 'hbv': '乙型肝炎', 'hiv': '艾滋病', 'tp': '梅毒',
    'crp': 'c反应蛋白', 'afp': '甲胎蛋白', 'cea': '癌胚抗原',
    'psa': '前列腺特异性抗原', 'saa': '血清淀粉样蛋白a', 'pct': '降钙素原',
    'wbc': '白细胞', 'rbc': '红细胞', 'hgb': '血红蛋白', 'plt': '血小板',
    'alt': '丙氨酸转氨酶', 'ast': '天冬氨酸转氨酶', 'alb': '白蛋白',
    'bun': '尿素氮', 'cr': '肌酐', 'ua': '尿酸', 'glu': '血糖',
    'tsh': '促甲状腺激素', 'ft3': '游离三碘甲状腺原氨酸', 'ft4': '游离甲状腺素',
    'ca125': '糖类抗原125', 'ca199': '糖类抗原199',
    'hba1c': '糖化血红蛋白', 'bnp': '脑钠肽', 'ctni': '肌钙蛋白i'
};

let specimenCurrentItem = null;

// 初始化标本采集手册搜索输入框回车事件
(function initSpecimenInput() {
    const input = document.getElementById('specimen-search');
    if (input) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') searchSpecimen();
        });
    }
})();

// 搜索
function searchSpecimen() {
    const input = document.getElementById('specimen-search');
    const keyword = (input.value || '').trim();
    if (!keyword) {
        alert('请输入搜索关键词');
        return;
    }
    const results = specimenSearchData(keyword);
    specimenDisplayResults(results);
}

// 搜索数据逻辑
function specimenSearchData(keyword) {
    const normalizeText = (text) => {
        if (!text) return '';
        return text.toLowerCase().replace(/[^\u4e00-\u9fa5a-z0-9]/g, '').replace(/\s+/g, '');
    };
    const normalizedKey = normalizeText(keyword);
    const expandKeyword = (key) => {
        let expandedKey = key;
        if (specimenSynonyms[key]) expandedKey = specimenSynonyms[key];
        for (const [short, full] of Object.entries(specimenSynonyms)) {
            if (key.includes(short)) expandedKey = expandedKey.replace(short, full);
        }
        return expandedKey;
    };
    const expandedKeys = [normalizedKey, expandKeyword(normalizedKey)];
    const data = (typeof examData !== 'undefined') ? examData : [];
    return data.filter(item => {
        const name = normalizeText(item.name || '');
        const code = normalizeText(item.code || '');
        const items = normalizeText((item.items || []).join(' '));
        return expandedKeys.some(key => name.includes(key) || code.includes(key) || items.includes(key));
    });
}

// 显示全部
function specimenShowAll() {
    const data = (typeof examData !== 'undefined') ? examData : [];
    specimenDisplayResults(data);
}

// 显示组合项目
function specimenShowCombos() {
    const data = (typeof examData !== 'undefined') ? examData : [];
    specimenDisplayResults(data.filter(item => item.type === '组合'));
}

// 显示单项项目
function specimenShowSingles() {
    const data = (typeof examData !== 'undefined') ? examData : [];
    specimenDisplayResults(data.filter(item => item.type === '单项'));
}

// 渲染结果列表
function specimenDisplayResults(results) {
    const tipsEl    = document.getElementById('specimen-tips');
    const emptyEl   = document.getElementById('specimen-empty');
    const wrapEl    = document.getElementById('specimen-results-wrap');
    const listEl    = document.getElementById('specimen-results');
    const countEl   = document.getElementById('specimen-count');

    tipsEl.style.display = 'none';

    if (results.length === 0) {
        wrapEl.style.display  = 'none';
        emptyEl.style.display = 'flex';
        return;
    }

    emptyEl.style.display = 'none';
    wrapEl.style.display  = 'block';
    countEl.textContent   = `共 ${results.length} 条记录`;

    listEl.innerHTML = results.map(item => `
        <div class="specimen-result-item" onclick="specimenShowDetail(${item.id})">
            <div class="specimen-result-name">${item.name}</div>
            <div class="specimen-result-info">
                <span class="specimen-result-code">${item.code}</span>
                <span class="specimen-result-price">¥${item.price}</span>
            </div>
            ${item.items && item.items.length > 0
                ? `<div class="specimen-result-type"><span class="specimen-item-count">包含 ${item.items.length} 项</span></div>`
                : ''}
        </div>
    `).join('');
}

// 显示详情弹窗
function specimenShowDetail(id) {
    const data = (typeof examData !== 'undefined') ? examData : [];
    specimenCurrentItem = data.find(item => item.id === id);
    if (!specimenCurrentItem) { alert('未找到该项目'); return; }

    const item = specimenCurrentItem;
    const modal     = document.getElementById('specimenModal');
    const titleEl   = document.getElementById('specimenModalTitle');
    const bodyEl    = document.getElementById('specimenModalBody');

    titleEl.textContent = item.name;

    bodyEl.innerHTML = `
        <div class="sp-card">
            <div class="sp-card-header">
                <span class="sp-card-title">${item.name}</span>
            </div>
            <div class="sp-info-row">
                <span class="sp-label">简码</span>
                <span class="sp-value sp-code">${item.code}</span>
            </div>
            <div class="sp-info-row">
                <span class="sp-label">价格</span>
                <span class="sp-value sp-price">¥${item.price}</span>
            </div>
            ${item.category ? `
            <div class="sp-info-row">
                <span class="sp-label">类别</span>
                <span class="sp-value">${item.category}</span>
            </div>` : ''}
        </div>

        ${(item.specimen || item.deliveryTime || item.receiptTime || item.reportTime) ? `
        <div class="sp-card">
            <div class="sp-card-header">
                <span class="sp-card-title">标本信息</span>
            </div>
            ${item.specimen ? `<div class="sp-info-row"><span class="sp-label">标本及容器</span><span class="sp-value">${item.specimen}</span></div>` : ''}
            ${item.deliveryTime ? `<div class="sp-info-row"><span class="sp-label">送达实验室时间</span><span class="sp-value">${item.deliveryTime}</span></div>` : ''}
            ${item.receiptTime ? `<div class="sp-info-row"><span class="sp-label">接收标本时间</span><span class="sp-value">${item.receiptTime}</span></div>` : ''}
            ${item.reportTime ? `<div class="sp-info-row"><span class="sp-label">出报告时间</span><span class="sp-value">${item.reportTime}</span></div>` : ''}
        </div>` : ''}

        ${(item.items && item.items.length > 0) ? `
        <div class="sp-card">
            <div class="sp-card-header">
                <span class="sp-card-title">包含项目</span>
                <span class="sp-item-count-badge">${item.items.length} 项</span>
            </div>
            <div class="sp-items-list">
                ${item.items.map((subItem, index) => `
                    <div class="sp-item-row">
                        <div class="sp-item-index">${index + 1}</div>
                        <div class="sp-item-name">${subItem}</div>
                    </div>
                `).join('')}
            </div>
        </div>` : ''}

        <div class="sp-actions">
            <button class="sp-btn-primary" onclick="specimenCopyAll()">📋 复制全部信息</button>
            <button class="sp-btn-secondary" onclick="specimenCloseModal()">✕ 关闭</button>
        </div>

        <div class="sp-disclaimer-card">
            <div class="sp-disclaimer-title">⚠️ 温馨提示</div>
            <div class="sp-disclaimer-text">本信息仅供参考，具体检验要求请以医院实际为准。如需确诊和治疗，请遵医嘱。</div>
        </div>
    `;

    modal.style.display = 'flex';
}

// 关闭弹窗
function specimenCloseModal() {
    document.getElementById('specimenModal').style.display = 'none';
}

// 复制全部信息
function specimenCopyAll() {
    if (!specimenCurrentItem) return;
    const item = specimenCurrentItem;
    const text = [
        `项目名称：${item.name}`,
        `录入简码：${item.code}`,
        `价格：¥${item.price}`,
        `类别：${item.category || '无'}`,
        `标本及容器：${item.specimen || '无'}`,
        `送达实验室时间：${item.deliveryTime || '无'}`,
        `接收标本时间：${item.receiptTime || '无'}`,
        `出报告时间：${item.reportTime || '无'}`
    ].join('\n');

    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => alert('复制成功！')).catch(() => specimenFallbackCopy(text));
    } else {
        specimenFallbackCopy(text);
    }
}

function specimenFallbackCopy(text) {
    const ta = document.createElement('textarea');
    ta.value = text;
    document.body.appendChild(ta);
    ta.select();
    document.execCommand('copy');
    document.body.removeChild(ta);
    alert('复制成功！');
}

// 点击弹窗背景关闭
document.getElementById('specimenModal').addEventListener('click', function(e) {
    if (e.target === this) specimenCloseModal();
});
