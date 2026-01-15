// InnoDB MVCC 可视化系统 JavaScript

const API_BASE = 'http://127.0.0.1:5001/api';

// 全局状态
let currentViewMode = 'normal'; // 'normal' 或 'split'
let systemState = null;
let selectedRowId = null; // 当前选中的行ID
let lastModifiedRows = new Set(); // 上次刷新时被修改的行集合

// 显示消息提示
function showMessage(message, type = 'info') {
    const messageEl = document.getElementById('message');
    messageEl.textContent = message;
    messageEl.className = `message ${type} show`;

    setTimeout(() => {
        messageEl.classList.remove('show');
    }, 3000);
}

// 开启新事务
async function beginTransaction() {
    const isolationLevel = document.getElementById('isolationLevel').value;

    try {
        const response = await fetch(`${API_BASE}/transaction/begin`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ isolation_level: isolationLevel })
        });

        const data = await response.json();
        showMessage(`事务 ${data.trx_id} 已开启`, 'success');
        refreshSystemState();
    } catch (error) {
        showMessage('开启事务失败: ' + error.message, 'error');
    }
}

// 提交事务
async function commitTransaction(trxId) {
    try {
        const response = await fetch(`${API_BASE}/transaction/commit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId })
        });

        const data = await response.json();
        if (data.success) {
            showMessage(`事务 ${trxId} 已提交`, 'success');
            refreshSystemState();
        } else {
            showMessage('提交事务失败', 'error');
        }
    } catch (error) {
        showMessage('提交事务失败: ' + error.message, 'error');
    }
}

// 回滚事务
async function rollbackTransaction(trxId) {
    try {
        const response = await fetch(`${API_BASE}/transaction/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId })
        });

        const data = await response.json();
        if (data.success) {
            showMessage(`事务 ${trxId} 已回滚`, 'info');
            refreshSystemState();
        } else {
            showMessage('回滚事务失败', 'error');
        }
    } catch (error) {
        showMessage('回滚事务失败: ' + error.message, 'error');
    }
}

// 插入数据
async function insertData() {
    const trxId = parseInt(document.getElementById('opTrxId').value);
    const dataStr = document.getElementById('opData').value;

    if (!trxId || !dataStr) {
        showMessage('请输入事务ID和数据', 'error');
        return;
    }

    try {
        const data = JSON.parse(dataStr);
        const response = await fetch(`${API_BASE}/data/insert`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId, data: data })
        });

        const result = await response.json();
        if (result.success) {
            showMessage(`数据已插入，行ID: ${result.row_id}`, 'success');
            refreshSystemState();
        } else {
            showMessage('插入失败: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('插入失败: ' + error.message, 'error');
    }
}

// 更新数据
async function updateData() {
    const trxId = parseInt(document.getElementById('opTrxId').value);
    const rowId = parseInt(document.getElementById('opRowId').value);
    const dataStr = document.getElementById('opData').value;

    if (!trxId || !rowId || !dataStr) {
        showMessage('请输入事务ID、行ID和数据', 'error');
        return;
    }

    try {
        const data = JSON.parse(dataStr);
        const response = await fetch(`${API_BASE}/data/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId, row_id: rowId, data: data })
        });

        const result = await response.json();
        if (result.success) {
            showMessage(`行 ${rowId} 已更新`, 'success');
            refreshSystemState();
        } else {
            showMessage('更新失败: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('更新失败: ' + error.message, 'error');
    }
}

// 删除数据
async function deleteData() {
    const trxId = parseInt(document.getElementById('opTrxId').value);
    const rowId = parseInt(document.getElementById('opRowId').value);

    if (!trxId || !rowId) {
        showMessage('请输入事务ID和行ID', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/data/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId, row_id: rowId })
        });

        const result = await response.json();
        if (result.success) {
            showMessage(`行 ${rowId} 已删除`, 'success');
            refreshSystemState();
        } else {
            showMessage('删除失败: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('删除失败: ' + error.message, 'error');
    }
}

// 读取数据
async function readData() {
    const trxId = parseInt(document.getElementById('opTrxId').value);
    const rowId = parseInt(document.getElementById('opRowId').value);

    if (!trxId || !rowId) {
        showMessage('请输入事务ID和行ID', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/data/read`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId, row_id: rowId })
        });

        const result = await response.json();
        if (result.success) {
            if (result.data) {
                showMessage(`读取成功: ${JSON.stringify(result.data)}`, 'success');
            } else {
                showMessage('该行数据对当前事务不可见', 'info');
            }
        } else {
            showMessage('读取失败: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('读取失败: ' + error.message, 'error');
    }
}

// 提交指定事务
async function commitSpecificTransaction() {
    const trxId = parseInt(document.getElementById('opTrxId').value);

    if (!trxId) {
        showMessage('请输入事务ID', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/transaction/commit`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId })
        });

        const result = await response.json();
        if (result.success) {
            showMessage(`事务 ${trxId} 已提交`, 'success');
            refreshSystemState();
        } else {
            showMessage('提交事务失败: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('提交事务失败: ' + error.message, 'error');
    }
}

// 回滚指定事务
async function rollbackSpecificTransaction() {
    const trxId = parseInt(document.getElementById('opTrxId').value);

    if (!trxId) {
        showMessage('请输入事务ID', 'error');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/transaction/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ trx_id: trxId })
        });

        const result = await response.json();
        if (result.success) {
            showMessage(`事务 ${trxId} 已回滚`, 'info');
            refreshSystemState();
        } else {
            showMessage('回滚事务失败: ' + result.error, 'error');
        }
    } catch (error) {
        showMessage('回滚事务失败: ' + error.message, 'error');
    }
}

// 重置系统
async function resetSystem() {
    if (!confirm('确定要重置系统吗？所有数据将被清空。')) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/system/reset`, {
            method: 'POST'
        });

        const result = await response.json();
        if (result.success) {
            showMessage('系统已重置', 'success');
            refreshSystemState();
        }
    } catch (error) {
        showMessage('重置失败: ' + error.message, 'error');
    }
}

// 刷新系统状态
async function refreshSystemState() {
    try {
        const response = await fetch(`${API_BASE}/system/state`);
        const state = await response.json();

        // 收集当前所有被修改的行
        const currentModifiedRows = new Set();
        state.transactions.active.forEach(trx => {
            if (trx.modified_rows) {
                trx.modified_rows.forEach(rowId => currentModifiedRows.add(rowId));
            }
        });

        // 检查选中的行是否被修改
        let shouldRefreshVersionChain = false;
        if (selectedRowId !== null) {
            // 如果选中的行在本次刷新中被修改了（且上次没有被修改），则需要刷新版本链
            if (currentModifiedRows.has(selectedRowId) && !lastModifiedRows.has(selectedRowId)) {
                shouldRefreshVersionChain = true;
            }
        }

        // 更新上次修改的行集合
        lastModifiedRows = currentModifiedRows;

        systemState = state; // 保存全局状态

        renderActiveTransactions(state.transactions.active);
        renderCommittedTransactions(state.transactions.committed);
        renderDataRows(state.rows);
        renderUndoLogs(state.undo_logs);
        renderReadViews(state.transactions.active);

        // 只在选中行被修改时才刷新版本链
        if (shouldRefreshVersionChain && selectedRowId !== null) {
            showVersionChain(selectedRowId);
        }

        // 如果在分屏模式，更新分屏视图
        if (currentViewMode === 'split') {
            updateSplitViewSelects(state.transactions.active);
        }
    } catch (error) {
        console.error('刷新状态失败:', error);
    }
}

// 渲染活跃事务列表
function renderActiveTransactions(transactions) {
    const container = document.getElementById('activeTransactions');

    if (transactions.length === 0) {
        container.innerHTML = '<p style="color: #718096; text-align: center;">暂无活跃事务</p>';
        return;
    }

    container.innerHTML = transactions.map(trx => {
        const operations = trx.operations || [];
        const modifiedRows = trx.modified_rows || [];
        const readView = trx.read_view;

        return `
            <div class="transaction-item-enhanced active">
                <div class="transaction-header">
                    <span class="transaction-id">事务 #${trx.trx_id}</span>
                    <span class="transaction-status status-active">${trx.status}</span>
                </div>

                <div class="transaction-info">
                    <div class="info-row">
                        <span class="info-label">隔离级别:</span>
                        <span class="info-value">${trx.isolation_level}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">开始时间:</span>
                        <span class="info-value">${new Date(trx.start_time).toLocaleString()}</span>
                    </div>
                </div>

                <!-- ReadView Details -->
                ${readView ? `
                    <div class="transaction-readview">
                        <div class="readview-title">📖 ReadView</div>
                        <div class="readview-compact">
                            <span>活跃事务: [${readView.m_ids.join(', ')}]</span>
                            <span>范围: ${readView.min_trx_id} - ${readView.max_trx_id}</span>
                        </div>
                    </div>
                ` : ''}

                <!-- Operation History with Data -->
                ${operations.length > 0 ? `
                    <div class="transaction-operations">
                        <div class="operations-title">📝 操作历史 (${operations.length})</div>
                        <div class="operations-list">
                            ${operations.slice(-5).map(op => `
                                <div class="operation-item op-${op.type}">
                                    <div class="op-header">
                                        <span class="op-type">${op.type}</span>
                                        <span class="op-row">行#${op.row_id}</span>
                                        <span class="op-time">${new Date(op.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                    ${op.details && Object.keys(op.details).length > 0 ? `
                                        <div class="op-data">
                                            ${JSON.stringify(op.details, null, 2)}
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                            ${operations.length > 5 ? `<div class="operations-more">...还有 ${operations.length - 5} 条</div>` : ''}
                        </div>
                    </div>
                ` : ''}

                <!-- Modified Rows -->
                ${modifiedRows.length > 0 ? `
                    <div class="transaction-modified">
                        <div class="modified-title">✏️ 修改的数据行</div>
                        <div class="modified-rows">
                            ${modifiedRows.map(rowId => `<span class="modified-row-badge">#${rowId}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}

                <div class="transaction-actions">
                    <button class="btn btn-info" onclick="commitTransaction(${trx.trx_id})">提交</button>
                    <button class="btn btn-danger" onclick="rollbackTransaction(${trx.trx_id})">回滚</button>
                </div>
            </div>
        `;
    }).join('');
}

// 渲染已提交事务列表
function renderCommittedTransactions(transactions) {
    const container = document.getElementById('committedTransactions');

    if (transactions.length === 0) {
        container.innerHTML = '<p style="color: #718096; text-align: center;">暂无已提交事务</p>';
        return;
    }

    container.innerHTML = transactions.slice(-10).reverse().map(trx => {
        const operations = trx.operations || [];
        const modifiedRows = trx.modified_rows || [];

        return `
            <div class="transaction-item-enhanced committed">
                <div class="transaction-header">
                    <span class="transaction-id">事务 #${trx.trx_id}</span>
                    <span class="transaction-status status-committed">${trx.status}</span>
                </div>

                <div class="transaction-info">
                    <div class="info-row">
                        <span class="info-label">开始时间:</span>
                        <span class="info-value">${new Date(trx.start_time).toLocaleString()}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">提交时间:</span>
                        <span class="info-value">${new Date(trx.commit_time).toLocaleString()}</span>
                    </div>
                </div>

                <!-- Operation Details with Data -->
                ${operations.length > 0 ? `
                    <div class="transaction-operations">
                        <div class="operations-title">📝 操作详情 (${operations.length})</div>
                        <div class="operations-list">
                            ${operations.map(op => `
                                <div class="operation-item op-${op.type}">
                                    <div class="op-header">
                                        <span class="op-type">${op.type}</span>
                                        <span class="op-row">行#${op.row_id}</span>
                                        <span class="op-time">${new Date(op.timestamp).toLocaleTimeString()}</span>
                                    </div>
                                    ${op.details && Object.keys(op.details).length > 0 ? `
                                        <div class="op-data">
                                            ${JSON.stringify(op.details, null, 2)}
                                        </div>
                                    ` : ''}
                                </div>
                            `).join('')}
                        </div>
                    </div>
                ` : ''}

                <!-- Modified Rows -->
                ${modifiedRows.length > 0 ? `
                    <div class="transaction-modified">
                        <div class="modified-title">✏️ 修改的数据行</div>
                        <div class="modified-rows">
                            ${modifiedRows.map(rowId => `<span class="modified-row-badge">#${rowId}</span>`).join('')}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

// 渲染数据行列表
function renderDataRows(rows) {
    const container = document.getElementById('dataRows');

    if (rows.length === 0) {
        container.innerHTML = '<p style="color: #718096; text-align: center;">暂无数据行</p>';
        return;
    }

    // 提取所有用户数据的键
    const userDataKeys = new Set();
    rows.forEach(row => {
        Object.keys(row.data).forEach(key => userDataKeys.add(key));
    });
    const dataColumns = Array.from(userDataKeys);

    // 构建表格HTML
    let tableHTML = `
        <div class="data-table-container">
            <table class="data-table">
                <thead>
                    <tr>
                        <th class="innodb-col">DB_ROW_ID</th>
                        <th class="innodb-col">DB_TRX_ID</th>
                        <th class="innodb-col">DB_ROLL_PTR</th>
                        ${dataColumns.map(col => `<th class="user-col">${col}</th>`).join('')}
                        <th class="status-col">状态</th>
                    </tr>
                </thead>
                <tbody>
                    ${rows.map(row => `
                        <tr class="data-table-row ${row.deleted ? 'deleted-row' : ''}"
                            onclick="showVersionChain(${row.row_id})"
                            title="点击查看版本链">
                            <td class="innodb-value">${row.row_id}</td>
                            <td class="innodb-value ${row.trx_id ? '' : 'null-value'}">${row.trx_id || 'NULL'}</td>
                            <td class="innodb-value ${row.roll_pointer ? '' : 'null-value'}">${row.roll_pointer || 'NULL'}</td>
                            ${dataColumns.map(col => `
                                <td class="user-value">${row.data[col] !== undefined ? JSON.stringify(row.data[col]) : 'NULL'}</td>
                            `).join('')}
                            <td class="status-value ${row.deleted ? 'deleted-status' : 'active-status'}">
                                ${row.deleted ? '已删除' : '正常'}
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;

    container.innerHTML = tableHTML;
}

// 渲染Undo日志
function renderUndoLogs(undoLogs) {
    const container = document.getElementById('undoLogs');

    if (undoLogs.length === 0) {
        container.innerHTML = '<p style="color: #718096; text-align: center;">暂无Undo日志</p>';
        return;
    }

    container.innerHTML = undoLogs.slice(-20).reverse().map(log => `
        <div class="undo-log">
            <div class="undo-log-header">
                <span class="undo-log-type ${log.log_type}">${log.log_type}</span>
                <span style="font-size: 0.85em; color: #718096;">Undo #${log.undo_id}</span>
            </div>
            <div class="undo-log-info">
                <div>事务ID: ${log.trx_id}</div>
                <div>行ID: ${log.row_id}</div>
                <div>Roll Pointer: ${log.roll_pointer || 'NULL'}</div>
            </div>
            ${log.old_value ? `
                <div class="undo-log-data">
                    <strong>旧值:</strong> ${JSON.stringify(log.old_value)}
                </div>
            ` : ''}
            ${log.new_value ? `
                <div class="undo-log-data">
                    <strong>新值:</strong> ${JSON.stringify(log.new_value)}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// 渲染ReadView
function renderReadViews(transactions) {
    const container = document.getElementById('readViews');

    const transactionsWithReadView = transactions.filter(trx => trx.read_view);

    if (transactionsWithReadView.length === 0) {
        container.innerHTML = '<p style="color: #718096; text-align: center;">暂无ReadView</p>';
        return;
    }

    container.innerHTML = transactionsWithReadView.map(trx => `
        <div class="read-view">
            <div class="read-view-header">事务 #${trx.trx_id} 的 ReadView</div>
            <div class="read-view-info">
                <div><strong>创建者:</strong> ${trx.read_view.creator_trx_id}</div>
                <div><strong>活跃事务列表 (m_ids):</strong> [${trx.read_view.m_ids.join(', ')}]</div>
                <div><strong>最小事务ID:</strong> ${trx.read_view.min_trx_id}</div>
                <div><strong>最大事务ID:</strong> ${trx.read_view.max_trx_id}</div>
                <div><strong>创建时间:</strong> ${new Date(trx.read_view.create_time).toLocaleString()}</div>
            </div>
        </div>
    `).join('');
}

// 渲染版本链
function renderVersionChains(versionChains) {
    const container = document.getElementById('versionChain');

    if (Object.keys(versionChains).length === 0) {
        container.innerHTML = '<p style="color: #718096; text-align: center;">点击数据行查看版本链</p>';
        return;
    }

    // 显示第一个版本链作为示例
    const firstRowId = Object.keys(versionChains)[0];
    showVersionChain(parseInt(firstRowId));
}

// 显示特定行的版本链
async function showVersionChain(rowId) {
    try {
        // 记录当前选中的行ID
        selectedRowId = rowId;

        const response = await fetch(`${API_BASE}/row/${rowId}`);
        const data = await response.json();

        if (!data || !data.version_chain) {
            return;
        }

        const container = document.getElementById('versionChain');
        const versions = data.version_chain.versions;
        const undoChain = data.undo_chain || [];

        // 构建 undo log 查找映射
        const undoMap = {};
        undoChain.forEach(undo => {
            undoMap[undo.undo_id] = undo;
        });

        // 反转版本数组，使最新的版本显示在最上面
        const reversedVersions = [...versions].reverse();

        container.innerHTML = `
            <h3 style="margin-bottom: 15px; color: #667eea;">行 #${rowId} 的版本链</h3>
            <div class="version-chain-info">
                <span>📊 总版本数: ${versions.length}</span>
                <span>🔗 Undo日志数: ${undoChain.length}</span>
            </div>

            <div class="version-chain-container">
                ${reversedVersions.map((version, index) => {
                    const undoLog = version.undo_id ? undoMap[version.undo_id] : null;
                    const hasNext = index < reversedVersions.length - 1;
                    // 版本序号：越新的版本序号越大（现在最新的在最上面）
                    const versionNumber = versions.length - index;

                    return `
                        <div class="version-node-enhanced">
                            <!-- Version Header -->
                            <div class="version-header-enhanced">
                                <div class="version-badge">版本 ${versionNumber}</div>
                                <span class="version-trx">事务 #${version.trx_id}</span>
                                <span class="version-time">${new Date(version.timestamp).toLocaleString()}</span>
                            </div>

                            <!-- Data Content -->
                            <div class="version-data-section">
                                <div class="version-data-label">数据内容:</div>
                                <div class="version-data">${JSON.stringify(version.data, null, 2)}</div>
                            </div>

                            <!-- Pointer Information -->
                            ${undoLog ? `
                                <div class="version-pointer-section">
                                    <div class="pointer-info-grid">
                                        <div class="pointer-item">
                                            <span class="pointer-label">🔑 Undo Log ID:</span>
                                            <span class="pointer-value">${undoLog.undo_id}</span>
                                        </div>
                                        <div class="pointer-item">
                                            <span class="pointer-label">📝 操作类型:</span>
                                            <span class="pointer-value undo-type-${undoLog.log_type}">${undoLog.log_type}</span>
                                        </div>
                                        ${undoLog.roll_pointer ? `
                                            <div class="pointer-item highlight">
                                                <span class="pointer-label">⬅️ DB_ROLL_PTR:</span>
                                                <span class="pointer-value roll-ptr">${undoLog.roll_pointer}</span>
                                            </div>
                                            <div class="pointer-description">
                                                指向 Undo Log #${undoLog.roll_pointer} (上一个版本)
                                            </div>
                                        ` : `
                                            <div class="pointer-item">
                                                <span class="pointer-label">⬅️ DB_ROLL_PTR:</span>
                                                <span class="pointer-value null-ptr">NULL</span>
                                            </div>
                                            <div class="pointer-description">
                                                这是最早的版本，无前驱
                                            </div>
                                        `}
                                    </div>
                                </div>
                            ` : ''}

                            <!-- Arrow Connector -->
                            ${hasNext ? `
                                <div class="version-arrow-connector">
                                    <div class="arrow-line"></div>
                                    <div class="arrow-head">▼</div>
                                    <div class="arrow-label">
                                        ${undoLog && undoLog.roll_pointer ?
                                            `通过 roll_pointer 指向历史版本` :
                                            '版本链连接'}
                                    </div>
                                </div>
                            ` : `
                                <div class="version-chain-end">
                                    <div class="end-marker">⬛</div>
                                    <div class="end-label">版本链末端</div>
                                </div>
                            `}
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    } catch (error) {
        console.error('获取版本链失败:', error);
    }
}

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    refreshSystemState();

    // 每3秒自动刷新一次
    setInterval(refreshSystemState, 3000);
});

// ==================== 分屏对比视图功能 ====================

// 切换视图模式
function toggleViewMode() {
    const mainContent = document.getElementById('mainContent');
    const splitViewContainer = document.getElementById('splitViewContainer');
    const viewModeText = document.getElementById('viewModeText');

    if (currentViewMode === 'normal') {
        // 切换到分屏模式
        mainContent.style.display = 'none';
        splitViewContainer.style.display = 'block';
        viewModeText.textContent = '切换到普通模式';
        currentViewMode = 'split';

        // 初始化分屏视图
        if (systemState) {
            updateSplitViewSelects(systemState.transactions.active);
        }
    } else {
        // 切换到普通模式
        mainContent.style.display = 'grid';
        splitViewContainer.style.display = 'none';
        viewModeText.textContent = '切换到分屏对比模式';
        currentViewMode = 'normal';
    }
}

// 更新分屏视图的事务选择器
function updateSplitViewSelects(activeTransactions) {
    const select1 = document.getElementById('splitTrx1');
    const select2 = document.getElementById('splitTrx2');

    if (!select1 || !select2) return;

    const options = activeTransactions.map(trx =>
        `<option value="${trx.trx_id}">事务 #${trx.trx_id} (${trx.isolation_level})</option>`
    ).join('');

    select1.innerHTML = options || '<option value="">无活跃事务</option>';
    select2.innerHTML = options || '<option value="">无活跃事务</option>';

    // 默认选择前两个事务
    if (activeTransactions.length >= 2) {
        select1.value = activeTransactions[0].trx_id;
        select2.value = activeTransactions[1].trx_id;
        refreshSplitView();
    } else if (activeTransactions.length === 1) {
        select1.value = activeTransactions[0].trx_id;
        select2.value = activeTransactions[0].trx_id;
        refreshSplitView();
    }
}

// 刷新分屏对比视图
async function refreshSplitView() {
    const trx1Id = parseInt(document.getElementById('splitTrx1').value);
    const trx2Id = parseInt(document.getElementById('splitTrx2').value);

    if (!trx1Id || !trx2Id) {
        showMessage('请选择要对比的事务', 'info');
        return;
    }

    try {
        // 获取两个事务的信息
        const [trx1Response, trx2Response] = await Promise.all([
            fetch(`${API_BASE}/transaction/${trx1Id}`),
            fetch(`${API_BASE}/transaction/${trx2Id}`)
        ]);

        const trx1 = await trx1Response.json();
        const trx2 = await trx2Response.json();

        // 更新标题
        document.getElementById('splitTrx1Title').textContent = `事务 #${trx1.trx_id} 的视角`;
        document.getElementById('splitTrx2Title').textContent = `事务 #${trx2.trx_id} 的视角`;

        // 渲染ReadView
        renderSplitReadView('splitTrx1ReadView', trx1.read_view);
        renderSplitReadView('splitTrx2ReadView', trx2.read_view);

        // 渲染可见数据
        await renderSplitData('splitTrx1Data', trx1);
        await renderSplitData('splitTrx2Data', trx2);

        showMessage('分屏视图已更新', 'success');
    } catch (error) {
        showMessage('刷新分屏视图失败: ' + error.message, 'error');
    }
}

// 渲染分屏视图的ReadView
function renderSplitReadView(containerId, readView) {
    const container = document.getElementById(containerId);

    if (!readView) {
        container.innerHTML = '<p style="color: #718096;">该事务没有ReadView</p>';
        return;
    }

    container.innerHTML = `
        <div><strong>创建者事务ID:</strong> ${readView.creator_trx_id}</div>
        <div><strong>活跃事务列表 (m_ids):</strong> [${readView.m_ids.join(', ')}]</div>
        <div><strong>最小事务ID:</strong> ${readView.min_trx_id}</div>
        <div><strong>最大事务ID:</strong> ${readView.max_trx_id}</div>
        <div><strong>创建时间:</strong> ${new Date(readView.create_time).toLocaleString()}</div>
    `;
}

// 渲染分屏视图的数据
async function renderSplitData(containerId, transaction) {
    const container = document.getElementById(containerId);

    if (!systemState || !systemState.rows || systemState.rows.length === 0) {
        container.innerHTML = '<p style="color: #718096;">暂无数据行</p>';
        return;
    }

    // 对每个数据行，检查该事务是否能看到
    const dataHtml = await Promise.all(systemState.rows.map(async row => {
        let visible = false;
        let visibleData = null;

        // 调用API检查可见性
        try {
            const response = await fetch(`${API_BASE}/data/read`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ trx_id: transaction.trx_id, row_id: row.row_id })
            });
            const result = await response.json();
            visible = result.success && result.data !== null;
            visibleData = result.data;
        } catch (error) {
            console.error('检查可见性失败:', error);
        }

        return `
            <div class="split-data-row ${visible ? '' : 'invisible'}">
                <!-- InnoDB隐藏字段 -->
                <div class="innodb-hidden-fields">
                    <div class="innodb-hidden-fields-title">InnoDB 隐藏字段</div>
                    <div class="hidden-field">
                        <span class="hidden-field-label">DB_ROW_ID</span>
                        <span class="hidden-field-value">${row.row_id}</span>
                    </div>
                    <div class="hidden-field">
                        <span class="hidden-field-label">DB_TRX_ID</span>
                        <span class="hidden-field-value">${row.trx_id || 'NULL'}</span>
                    </div>
                    <div class="hidden-field">
                        <span class="hidden-field-label">DB_ROLL_PTR</span>
                        <span class="hidden-field-value">${row.roll_pointer || 'NULL'}</span>
                    </div>
                </div>

                <!-- 数据内容 -->
                <div class="user-data-title">${visible ? '可见数据:' : '不可见 (显示当前版本)'}</div>
                <div class="user-data">${JSON.stringify(visible ? visibleData : row.data, null, 2)}</div>

                ${!visible ? '<div style="margin-top: 8px; color: #c53030; font-size: 0.9em;">💡 根据ReadView规则，该数据对当前事务不可见</div>' : ''}
            </div>
        `;
    }));

    container.innerHTML = dataHtml.join('');
}

