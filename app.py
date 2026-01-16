"""
Flask Web服务器
提供REST API和Web界面
"""
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from mvcc_system import MVCCSystem

app = Flask(__name__)
CORS(app)

# 创建MVCC系统实例
mvcc_system = MVCCSystem()


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/transaction/begin', methods=['POST'])
def begin_transaction():
    """开启事务"""
    data = request.get_json() or {}
    isolation_level = data.get('isolation_level', 'READ_COMMITTED')
    result = mvcc_system.begin_transaction(isolation_level)
    return jsonify(result)


@app.route('/api/transaction/commit', methods=['POST'])
def commit_transaction():
    """提交事务"""
    data = request.get_json()
    trx_id = data.get('trx_id')
    result = mvcc_system.commit_transaction(trx_id)
    return jsonify(result)


@app.route('/api/transaction/rollback', methods=['POST'])
def rollback_transaction():
    """回滚事务"""
    data = request.get_json()
    trx_id = data.get('trx_id')
    result = mvcc_system.rollback_transaction(trx_id)
    return jsonify(result)


@app.route('/api/transaction/<int:trx_id>', methods=['GET'])
def get_transaction(trx_id):
    """获取事务信息"""
    result = mvcc_system.get_transaction_info(trx_id)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Transaction not found'}), 404


@app.route('/api/data/insert', methods=['POST'])
def insert_data():
    """插入数据"""
    data = request.get_json()
    trx_id = data.get('trx_id')
    row_data = data.get('data', {})
    result = mvcc_system.insert_data(trx_id, row_data)
    return jsonify(result)


@app.route('/api/data/update', methods=['POST'])
def update_data():
    """更新数据"""
    data = request.get_json()
    trx_id = data.get('trx_id')
    row_id = data.get('row_id')
    row_data = data.get('data', {})
    result = mvcc_system.update_data(trx_id, row_id, row_data)
    return jsonify(result)


@app.route('/api/data/delete', methods=['POST'])
def delete_data():
    """删除数据"""
    data = request.get_json()
    trx_id = data.get('trx_id')
    row_id = data.get('row_id')
    result = mvcc_system.delete_data(trx_id, row_id)
    return jsonify(result)


@app.route('/api/data/read', methods=['POST'])
def read_data():
    """读取数据"""
    data = request.get_json()
    trx_id = data.get('trx_id')
    row_id = data.get('row_id')
    result = mvcc_system.read_data(trx_id, row_id)
    return jsonify(result)


@app.route('/api/data/read_with_path', methods=['POST'])
def read_data_with_path():
    """读取数据并返回读取路径"""
    data = request.get_json()
    trx_id = data.get('trx_id')
    row_id = data.get('row_id')
    result = mvcc_system.read_data_with_path(trx_id, row_id)
    return jsonify(result)


@app.route('/api/row/<int:row_id>', methods=['GET'])
def get_row(row_id):
    """获取数据行信息"""
    result = mvcc_system.get_row_info(row_id)
    if result:
        return jsonify(result)
    return jsonify({'error': 'Row not found'}), 404


@app.route('/api/system/state', methods=['GET'])
def get_system_state():
    """获取系统状态"""
    result = mvcc_system.get_system_state()

    # 修正DB_ROLL_PTR的显示值
    # 内部实现：row.roll_pointer指向当前版本的Undo日志
    # 展示逻辑：DB_ROLL_PTR应该显示上一个版本的Undo日志
    for row in result['rows']:
        row['display_roll_pointer'] = _get_display_roll_pointer(row['row_id'], row['roll_pointer'])

    return jsonify(result)


def _get_display_roll_pointer(row_id, internal_roll_pointer):
    """
    获取用于展示的DB_ROLL_PTR值

    InnoDB语义：DB_ROLL_PTR指向上一个版本
    - INSERT后：显示NULL（没有上一个版本）
    - UPDATE后：显示上一个版本的Undo日志ID
    """
    if internal_roll_pointer is None:
        return None

    # 获取当前roll_pointer指向的Undo日志
    undo_log = mvcc_system.undo_log_manager.get_undo_log(internal_roll_pointer)
    if not undo_log:
        return None

    # 如果是INSERT类型，显示NULL（因为INSERT没有上一个版本）
    if undo_log.log_type.value == 'INSERT':
        return None

    # 如果是UPDATE/DELETE类型，显示Undo日志的roll_pointer（指向上一个版本）
    return undo_log.roll_pointer


@app.route('/api/system/reset', methods=['POST'])
def reset_system():
    """重置系统"""
    mvcc_system.reset()
    return jsonify({'success': True})


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
