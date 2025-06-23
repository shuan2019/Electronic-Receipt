from flask import Flask, render_template, request, redirect, url_for, flash
import json
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
DATA_FILE = 'receipts.json'
HISTORY_FILE = 'history.json'

def load_receipts():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_receipts(receipts):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(receipts, f, ensure_ascii=False, indent=2)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return {'payers': [], 'recipients': [], 'items': []}
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def num_to_chinese_upper(num):
    units = ['元', '拾', '佰', '仟', '万', '拾', '佰', '仟', '亿']
    nums = '零壹贰叁肆伍陆柒捌玖'
    str_num = '%.2f' % float(num)
    integer, fraction = str_num.split('.')
    integer = integer[::-1]
    result = []
    for i, n in enumerate(integer):
        result.append(nums[int(n)] + (units[i] if int(n) != 0 else ''))
    result = ''.join(result[::-1]).replace('零元', '元').replace('零万', '万').replace('零亿', '亿')
    result = result.replace('零零', '零').replace('零零', '零')
    if result.startswith('元'):
        result = '零' + result
    if fraction == '00':
        result += '整'
    else:
        jiao = nums[int(fraction[0])] + '角' if fraction[0] != '0' else ''
        fen = nums[int(fraction[1])] + '分' if fraction[1] != '0' else ''
        result += jiao + fen
    return result

app.jinja_env.filters['to_chinese_upper'] = num_to_chinese_upper

@app.template_filter('today')
def today_filter(s):
    return datetime.now().strftime('%Y-%m-%d')

@app.route('/', methods=['GET', 'POST'])
def index():
    history = load_history()
    if request.method == 'POST':
        payer = request.form['payer']
        recipient = request.form.get('recipient', '')
        payee = request.form.get('payee', '')
        accountant = request.form.get('accountant', '')
        amount = request.form.get('amount', type=float)
        date = request.form['date']
        items = []
        names = request.form.getlist('item_name')
        units = request.form.getlist('item_unit')
        qtys = request.form.getlist('item_qty')
        prices = request.form.getlist('item_price')
        amounts = request.form.getlist('item_amount')
        remarks = request.form.getlist('item_remark')
        for i in range(len(names)):
            if names[i].strip() == '':
                continue
            items.append({
                'name': names[i],
                'unit': units[i],
                'qty': qtys[i],
                'price': prices[i],
                'amount': amounts[i],
                'remark': remarks[i]
            })
        if not payer or not date or not items:
            flash('所有字段均为必填，且至少有一项明细！')
            return redirect(url_for('index'))
        total_amount = sum([float(item['amount']) for item in items])
        receipts = load_receipts()
        new_id = receipts[-1]['id'] + 1 if receipts else 1
        receipt = {
            'id': new_id,
            'payer': payer,
            'recipient': recipient,
            'payee': payee,
            'accountant': accountant,
            'amount': total_amount,
            'date': date,
            'items': items,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        receipts.append(receipt)
        save_receipts(receipts)
        # 保存历史数据
        if payer and payer not in history['payers']:
            history['payers'].append(payer)
        if recipient and recipient not in history['recipients']:
            history['recipients'].append(recipient)
        if payee and payee not in history.get('payees', []):
            history.setdefault('payees', []).append(payee)
        if accountant and accountant not in history.get('accountants', []):
            history.setdefault('accountants', []).append(accountant)
        for item in items:
            exist = any(h['name'] == item['name'] and h['unit'] == item['unit'] and h['price'] == item['price'] for h in history['items'])
            if item['name'] and not exist:
                history['items'].append({'name': item['name'], 'unit': item['unit'], 'price': item['price']})
        save_history(history)
        return redirect(url_for('preview', receipt_id=receipt['id']))
    return render_template('index.html', history=history)

@app.route('/preview/<int:receipt_id>')
def preview(receipt_id):
    receipts = load_receipts()
    receipt = next((r for r in receipts if r['id'] == receipt_id), None)
    if not receipt:
        flash('未找到该收据')
        return redirect(url_for('index'))
    
    # 分页逻辑
    items_per_page = 5
    total_items = len(receipt['items'])
    total_pages = (total_items + items_per_page - 1) // items_per_page
    
    # 获取当前页参数，默认为第1页
    current_page = request.args.get('page', 1, type=int)
    if current_page < 1:
        current_page = 1
    elif current_page > total_pages:
        current_page = total_pages
    
    # 计算当前页的项目
    start_index = (current_page - 1) * items_per_page
    end_index = start_index + items_per_page
    current_items = receipt['items'][start_index:end_index]
    
    # 为项目添加序号
    for i, item in enumerate(current_items):
        item['display_index'] = start_index + i + 1
    
    return render_template('preview.html', 
                         receipt=receipt, 
                         current_items=current_items,
                         current_page=current_page,
                         total_pages=total_pages,
                         total_items=total_items)

@app.route('/history')
def history():
    receipts = load_receipts()
    receipts = sorted(receipts, key=lambda r: r['created_at'], reverse=True)
    return render_template('history.html', receipts=receipts)

@app.route('/delete_receipt/<int:receipt_id>', methods=['POST'])
def delete_receipt(receipt_id):
    receipts = load_receipts()
    receipt_to_delete = next((r for r in receipts if r['id'] == receipt_id), None)
    
    if receipt_to_delete:
        receipts.remove(receipt_to_delete)
        save_receipts(receipts)
        flash(f'收据 ID:{receipt_id} 已被成功删除。', 'success')
    else:
        flash(f'未找到要删除的收据 ID:{receipt_id}。', 'danger')
        
    return redirect(url_for('history'))

if __name__ == '__main__':
    app.run(debug=True) 