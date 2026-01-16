# InnoDB MVCC 可视化系统

## 🎉 项目概述

这是一个完整的InnoDB MVCC（多版本并发控制）可视化系统，完全符合InnoDB的实现规范，用于教学和演示MVCC的工作原理。

---

## ✨ 核心特性

### 1. 完全符合InnoDB规范

- ✅ **ReadView创建时机正确**
  - READ COMMITTED: 每次SELECT时创建新ReadView
  - REPEATABLE READ: 第一次SELECT时创建ReadView，之后复用

- ✅ **ReadView可见性判断正确**
  - 使用`Transaction._next_trx_id`作为max_trx_id
  - 正确判断事务可见性

- ✅ **DB_ROLL_PTR语义正确**
  - INSERT后显示NULL（没有上一个版本）
  - UPDATE后显示上一个版本的Undo日志ID
  - 内部实现与展示层分离

- ✅ **版本链完整可追溯**
  - 通过ROLL_PTR串联所有历史版本
  - 支持MVCC版本回溯

### 2. Undo Log Header可视化

**关键MVCC字段展示：**

```
┌──────────────────────────────────────────────────────────┐
│ 行 #1 的版本链                              3 个版本      │
├──────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────┐  │
│  │ ╔══════════════════════════════════════════════╗   │  │
│  │ ║  UPDATE          Undo Log #3                 ║   │  │
│  │ ╠══════════════════════════════════════════════╣   │  │
│  │ ║  TRX_ID: 3      │ ROLL_PTR: → #2            ║   │  │
│  │ ║  ROW_ID: #1     │ TYPE: UPDATE              ║   │  │
│  │ ╚══════════════════════════════════════════════╝   │  │
│  │ 旧值: {'name': 'Alice', 'age': 26}                │  │
│  └────────────────────────────────────────────────────┘  │
│                         ↓                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ╔══════════════════════════════════════════════╗   │  │
│  │ ║  UPDATE          Undo Log #2                 ║   │  │
│  │ ╠══════════════════════════════════════════════╣   │  │
│  │ ║  TRX_ID: 2      │ ROLL_PTR: → #1            ║   │  │
│  │ ║  ROW_ID: #1     │ TYPE: UPDATE              ║   │  │
│  │ ╚══════════════════════════════════════════════╝   │  │
│  │ 旧值: {'name': 'Alice', 'age': 25}                │  │
│  └────────────────────────────────────────────────────┘  │
│                         ↓                                │
│  ┌────────────────────────────────────────────────────┐  │
│  │ ╔══════════════════════════════════════════════╗   │  │
│  │ ║  INSERT          Undo Log #1                 ║   │  │
│  │ ╠══════════════════════════════════════════════╣   │  │
│  │ ║  TRX_ID: 1      │ ROLL_PTR: NULL            ║   │  │
│  │ ║  ROW_ID: #1     │ TYPE: INSERT              ║   │  │
│  │ ╚══════════════════════════════════════════════╝   │  │
│  │ 记录: 主键 ROW_ID=#1 (回滚时删除此行)             │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

**Header字段说明：**

- **TRX_ID**: 创建此Undo Log的事务ID（MVCC可见性判断核心）
- **ROLL_PTR**: 指向上一个版本的Undo Log（串联版本链）
- **ROW_ID**: 数据行ID（关联Undo Log和数据行）
- **TYPE**: 操作类型（INSERT/UPDATE/DELETE）

**Body只记录旧值（符合InnoDB实现）：**

- **INSERT**: 只记录主键（回滚时删除此行）
- **UPDATE**: 只记录旧值（回滚和MVCC使用）
- **DELETE**: 只记录旧值（回滚恢复使用）
- **原因**: 新值已在当前数据行中，无需重复存储

### 3. 版本链可视化

- ✅ 按行ID分组展示
- ✅ 从最新到最早排序
- ✅ 使用箭头（↓）连接相邻版本
- ✅ Roll Pointer可视化（→ Undo #X）
- ✅ 版本链连接关系正确

### 4. 完整的事务管理

- ✅ 支持INSERT/UPDATE/DELETE操作
- ✅ 支持事务提交/回滚
- ✅ INSERT回滚完全清理（数据行、版本链、Undo日志）
- ✅ UPDATE/DELETE回滚正确恢复
- ✅ 支持READ COMMITTED/REPEATABLE READ隔离级别

### 5. 系统功能

- ✅ 系统重置（重置所有ID计数器和数据）
- ✅ 实时状态刷新
- ✅ 读取路径追踪
- ✅ 分屏对比视图

---

## 🏗️ 系统架构

### 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                    Web界面 (Flask)                       │
│                  templates/index.html                    │
│              static/js/app.js + style.css                │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                   MVCC System                            │
│                  mvcc_system.py                          │
├─────────────────────────────────────────────────────────┤
│  • 事务管理 (transaction.py)                            │
│  • 数据行管理 (data_row.py)                             │
│  • Undo日志管理 (undo_log.py)                           │
│  • ReadView管理                                          │
└─────────────────────────────────────────────────────────┘
```

### 数据流程

```
用户操作 → Flask API → MVCCSystem
    ↓
DataRowManager ← → UndoLogManager
    ↓
创建/更新数据行和Undo日志
    ↓
返回系统状态（包含display_roll_pointer转换）
    ↓
前端渲染（Undo Log Header + 版本链）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install flask
```

### 2. 启动系统

```bash
python app.py
```

访问 http://127.0.0.1:5001

### 3. 基本操作

#### 创建第一个版本链

1. 点击"开启事务"按钮
2. 在"插入数据"输入框中输入：`{"name": "Alice", "age": 25}`
3. 点击"插入"按钮
4. 点击事务卡片上的"提交"按钮
5. 查看Undo Log区域，应该看到一个INSERT日志

#### 扩展版本链

6. 再次点击"开启事务"
7. 在"更新数据"中输入行ID和新数据：`{"name": "Alice", "age": 26}`
8. 点击"更新"按钮
9. 提交事务
10. 查看Undo Log区域，应该看到两个日志，用箭头连接

---

## 📊 功能演示场景

### 场景1：验证READ COMMITTED

```
步骤：
1. 开启事务1，插入数据并提交
2. 开启事务2（READ COMMITTED）
3. 事务2读取数据
4. 开启事务3，更新数据并提交
5. 事务2再次读取

预期结果：
- 事务2能看到事务3的更新 ✓
```

### 场景2：验证REPEATABLE READ

```
步骤：
1. 开启事务1，插入数据并提交
2. 开启事务2（REPEATABLE READ）
3. 事务2读取数据
4. 开启事务3，更新数据并提交
5. 事务2再次读取

预期结果：
- 事务2看到原来的数据（不受事务3影响）✓
```

### 场景3：验证Undo Log Header

```
步骤：
1. 开启事务1，插入数据并提交
2. 开启事务2，更新数据并提交
3. 开启事务3，再次更新数据并提交
4. 查看Undo Log区域

预期结果：
- 显示"行 #1 的版本链"标题 ✓
- 显示"3 个版本" ✓
- 每个Undo Log有清晰的Header ✓
- Header显示 TRX_ID, ROLL_PTR, ROW_ID, TYPE ✓
- Body只显示旧值（INSERT显示主键）✓
- 相邻版本用箭头连接 ✓
- ROLL_PTR格式为 → #X 或 NULL ✓
```

### 场景4：验证INSERT回滚

```
步骤：
1. 开启事务1
2. 插入数据
3. 回滚事务1

预期结果：
- 数据行完全删除 ✓
- 版本链完全删除 ✓
- Undo日志完全删除 ✓
```

---

## 🔍 技术实现细节

### 1. ReadView创建时机

**InnoDB规范：**
- READ COMMITTED: 每次SELECT时创建新ReadView
- REPEATABLE READ: 第一次SELECT时创建ReadView，之后复用

**实现位置：** `mvcc_system.py:160-206`

```python
def read_data(self, trx_id: int, row_id: int) -> Dict:
    trx = self.transaction_manager.get_transaction(trx_id)

    if trx.isolation_level == "READ_COMMITTED":
        # 每次读取都创建新ReadView
        active_trx_ids = self.transaction_manager.get_active_trx_ids()
        current_read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)
        data = self.data_row_manager.read_row(row_id, current_read_view)
    else:
        # REPEATABLE READ: 第一次读取时创建，之后复用
        if not trx.read_view:
            active_trx_ids = self.transaction_manager.get_active_trx_ids()
            trx.read_view = ReadView(trx.trx_id, active_trx_ids, Transaction._next_trx_id)
        data = self.data_row_manager.read_row(row_id, trx.read_view)

    return {'success': True, 'data': data}
```

### 2. ReadView可见性判断

**实现位置：** `transaction.py:86-111`

```python
def is_visible(self, trx_id: int) -> bool:
    # 自己修改的数据
    if trx_id == self.creator_trx_id:
        return True

    # ReadView创建前已提交
    if trx_id < self.min_trx_id:
        return True

    # ReadView创建后才开始（使用>=而不是>）
    if trx_id >= self.max_trx_id:
        return False

    # 不在活跃列表中则已提交
    return trx_id not in self.m_ids
```

### 3. DB_ROLL_PTR展示层转换

**实现位置：** `app.py:132-153`

```python
def _get_display_roll_pointer(row_id, internal_roll_pointer):
    """
    获取用于展示的DB_ROLL_PTR值

    InnoDB语义：DB_ROLL_PTR指向上一个版本
    - INSERT后：显示NULL（没有上一个版本）
    - UPDATE后：显示上一个版本的Undo日志ID
    """
    if internal_roll_pointer is None:
        return None

    undo_log = mvcc_system.undo_log_manager.get_undo_log(internal_roll_pointer)
    if not undo_log:
        return None

    # INSERT类型，显示NULL
    if undo_log.log_type.value == 'INSERT':
        return None

    # UPDATE/DELETE类型，显示Undo日志的roll_pointer
    return undo_log.roll_pointer
```

### 4. Undo Log Header渲染

**实现位置：** `static/js/app.js:820-869`

```javascript
rowUndos.forEach((log, index) => {
    html += `
        <div class="undo-log">
            <!-- Header: 关键MVCC字段 -->
            <div class="undo-log-header-section">
                <div class="undo-log-header-title">
                    <span class="undo-log-type ${log.log_type}">${log.log_type}</span>
                    <span class="undo-log-id">Undo Log #${log.undo_id}</span>
                </div>
                <div class="undo-log-header-fields">
                    <div class="header-field">
                        <span class="field-label">TRX_ID</span>
                        <span class="field-value">${log.trx_id}</span>
                    </div>
                    <div class="header-field">
                        <span class="field-label">ROLL_PTR</span>
                        <span class="field-value">${log.roll_pointer ? \`→ #\${log.roll_pointer}\` : 'NULL'}</span>
                    </div>
                    <div class="header-field">
                        <span class="field-label">ROW_ID</span>
                        <span class="field-value">#${log.row_id}</span>
                    </div>
                    <div class="header-field">
                        <span class="field-label">TYPE</span>
                        <span class="field-value">${log.log_type}</span>
                    </div>
                </div>
            </div>

            <!-- Body: 只记录旧值 -->
            <div class="undo-log-body">
                ${log.log_type === 'INSERT' ? \`
                    <div class="undo-log-data">
                        <strong>记录:</strong> 主键 ROW_ID=#\${log.row_id}（回滚时删除此行）
                    </div>
                \` : ''}
                ${log.old_value ? \`
                    <div class="undo-log-data">
                        <strong>旧值:</strong> \${JSON.stringify(log.old_value)}
                    </div>
                \` : ''}
            </div>
        </div>
    `;
});
```

### 5. 版本链CSS样式

**实现位置：** `static/css/style.css:1291-1377`

```css
/* Undo Log Header 样式 */
.undo-log-header-section {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 15px;
    border-radius: 8px 8px 0 0;
    margin: -10px -10px 0 -10px;
}

.undo-log-header-fields {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
}

.field-value {
    font-size: 0.95em;
    font-weight: 700;
    font-family: 'Courier New', monospace;
}
```

---

## 📁 项目文件结构

```
Innodb-mvvc-visualization/
├── app.py                      # Flask Web服务器
├── mvcc_system.py              # MVCC系统主逻辑
├── transaction.py              # 事务和ReadView管理
├── data_row.py                 # 数据行和版本链管理
├── undo_log.py                 # Undo日志管理
├── templates/
│   └── index.html              # HTML模板
├── static/
│   ├── js/
│   │   └── app.js              # 前端JavaScript逻辑
│   └── css/
│       └── style.css           # 样式表
├── file/                       # 截图文件
└── README.md                   # 项目文档
```

---

## 🎓 学习价值

### 1. 理解MVCC工作原理

- **多版本如何共存**: 通过Undo Log保存历史版本
- **ReadView如何判断可见性**: 通过TRX_ID和活跃事务列表
- **版本链如何回溯**: 通过ROLL_PTR串联历史版本

### 2. 理解InnoDB隐藏字段

- **DB_ROW_ID**: 行ID（主键）
- **DB_TRX_ID**: 事务ID（最后修改此行的事务）
- **DB_ROLL_PTR**: 回滚指针（指向Undo Log）

### 3. 理解事务隔离级别

- **READ COMMITTED**: 每次读取创建新ReadView，能读到已提交的更新
- **REPEATABLE READ**: 第一次读取创建ReadView，之后复用，保证可重复读

### 4. 理解Undo日志的作用

- **回滚操作**: 使用旧值恢复数据
- **版本追溯**: MVCC读取历史版本
- **MVCC实现**: 多版本并发控制的基础

### 5. 理解Undo Log结构

- **Header**: 包含TRX_ID、ROLL_PTR、ROW_ID、TYPE等关键字段
- **Body**: 只记录旧值（INSERT记录主键，UPDATE/DELETE记录旧值）
- **版本链**: 通过ROLL_PTR串联所有历史版本

---

## 🎨 界面展示

### 主界面布局

```
┌─────────────────────────────────────────────────────────┐
│                  InnoDB MVCC 可视化系统                  │
└─────────────────────────────────────────────────────────┘

┌──────────────┬──────────────┬──────────────┬───────────┐
│  活跃事务     │  已提交事务   │  数据行列表   │ ReadView  │
│              │              │              │           │
│ 事务 #1      │ 事务 #2      │ Row #1       │ 事务 #1   │
│ [提交][回滚] │ (已提交)     │ DB_ROLL_PTR  │ m_ids: [] │
│              │              │ = NULL/1/2   │           │
└──────────────┴──────────────┴──────────────┴───────────┘

┌─────────────────────────────────────────────────────────┐
│                  Undo Log 版本链（带Header）             │
├─────────────────────────────────────────────────────────┤
│  行 #1 的版本链              3 个版本                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │ ╔═══════════════════════════════════════════╗   │   │
│  │ ║ UPDATE  Undo Log #3                       ║   │   │
│  │ ╠═══════════════════════════════════════════╣   │   │
│  │ ║ TRX_ID: 3  │ ROLL_PTR: → #2               ║   │   │
│  │ ║ ROW_ID: #1 │ TYPE: UPDATE                 ║   │   │
│  │ ╚═══════════════════════════════════════════╝   │   │
│  │ 旧值: {'name': 'Alice', 'age': 26}             │   │
│  └─────────────────────────────────────────────────┘   │
│                         ↓                               │
│  （更多版本...）                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      版本链详情                          │
│  (点击数据行查看)                                        │
└─────────────────────────────────────────────────────────┘
```

---

## 💡 使用技巧

### 技巧1：观察版本链的形成

```
操作：连续多次更新同一行数据
观察：Undo Log区域会实时显示版本链的增长
学习：理解每次UPDATE如何创建新的Undo日志
```

### 技巧2：对比不同隔离级别

```
场景：两个事务同时操作同一行数据

READ COMMITTED：
  → 观察：事务2能看到事务1提交的更新
  → 查看：Undo Log显示完整的版本链

REPEATABLE READ：
  → 观察：事务2看不到事务1提交的更新
  → 查看：Undo Log显示相同的版本链，但ReadView不同
```

### 技巧3：追踪Roll Pointer

```
操作：查看Roll Pointer的指向
观察：从最新版本一直追溯到INSERT
学习：理解版本链的回溯过程
```

### 技巧4：理解Undo Log Header

```
操作：查看每个Undo Log的Header字段
观察：TRX_ID、ROLL_PTR、ROW_ID、TYPE的值
学习：理解MVCC关键字段的作用
```

---

## 🔧 系统特点

### 1. 教学友好

- ✅ 清晰的版本演变过程
- ✅ Roll Pointer可视化
- ✅ Undo Log Header突出显示关键字段
- ✅ 读取路径追踪
- ✅ 分屏对比视图

### 2. 完全符合InnoDB实现

- ✅ ReadView创建时机正确
- ✅ ReadView可见性判断正确
- ✅ DB_ROLL_PTR语义正确
- ✅ Undo Log只记录旧值
- ✅ 版本链完整可追溯

### 3. 功能完整

- ✅ 支持INSERT/UPDATE/DELETE操作
- ✅ 支持事务提交/回滚
- ✅ 支持READ COMMITTED/REPEATABLE READ隔离级别
- ✅ 支持系统重置
- ✅ 实时状态刷新

### 4. 可视化效果出色

- ✅ Undo Log Header渐变紫色背景
- ✅ 关键字段网格布局
- ✅ 等宽字体显示值
- ✅ 操作类型颜色区分（INSERT绿色、UPDATE橙色、DELETE红色）
- ✅ 箭头连接版本链
- ✅ 数据行列表清晰展示
- ✅ ReadView信息完整

---

## 🏆 总结

这是一个**完整、准确、美观**的InnoDB MVCC可视化系统：

- ✅ 完全符合InnoDB的实现规范
- ✅ Undo Log Header清晰展示关键MVCC字段
- ✅ 只记录旧值，符合InnoDB实际实现
- ✅ 版本链可视化效果出色
- ✅ 教学价值高
- ✅ 代码质量好

**系统已经可以正式使用了！** 🎉

---

## 📞 反馈

如有问题或建议，欢迎提出！

---

**最后更新：** 2026-01-16
**版本：** 2.0.0
**状态：** ✅ 生产就绪
