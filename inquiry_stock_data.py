from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import os
import webbrowser
from stock_utils import (
    check_financial_directory,
    fetch_stock_data,
    process_stock_data,
    fetch_financial_report,
    generate_turnover_histogram,
    filter_stocks
)

app = Flask(__name__)
CORS(app, resources={r"/get_*": {"origins": ["http://localhost:5000"]}})

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_stock_data')
def get_stock_data():
    try:
        symbol = request.args.get('symbol').strip()
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        sort_column = request.args.get('sort_column', '换手率')
        sort_order = request.args.get('sort_order', 'desc')

        app.logger.info(f"处理请求: symbol={symbol}, start_date={start_date}, end_date={end_date}")

        if not symbol:
            return jsonify({'error': '股票代码不能为空'}), 400
        if not start_date or not end_date:
            return jsonify({'error': '起始日期和结束日期不能为空'}), 400
        if not (start_date.isdigit() and end_date.isdigit() and len(start_date) == 8 and len(end_date) == 8):
            return jsonify({'error': '日期格式错误，请使用 YYYYMMDD 格式'}), 400

        # 调用 fetch_stock_data 获取 df 和其他数据
        df, stock_name, filtered_dict, current_price = fetch_stock_data(symbol, start_date, end_date)
        # 调用 process_stock_data 使用 df 进行处理
        max_market_cap, min_market_cap, select_columns = process_stock_data(df, sort_column, sort_order)
        histogram_image = generate_turnover_histogram(df, stock_name)  # 生成直方图

        response = {
            'shape': list(df.shape),
            'table': select_columns.to_dict(orient='records'),
            'stock_name': stock_name,
            'max_market_cap': max_market_cap,
            'min_market_cap': min_market_cap,
            'filtered_dict':filtered_dict,
            'current_price':current_price,
            'histogram_image': histogram_image
        }
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 清除已有端点，防止重复注册
app.view_functions.pop('get_financial_report', None)
@app.route('/get_financial_report')
def get_financial_report():
    stock_code = request.args.get('symbol', '').strip()
    app.logger.info(f"请求财务报表: symbol={stock_code}")
    try:
        available_columns, data = fetch_financial_report(stock_code)
        response = {'table': data, 'columns': available_columns}
        return jsonify(response)
    except Exception as e:
        app.logger.error(f"获取财务报表失败: {str(e)}")
        return jsonify({'error': str(e)}), 404

@app.route('/get_filtered_stocks', methods=['POST'])
def api_filter_stocks():
    try:
        # 获取前端传递的筛选条件
        data = request.get_json()
        roe = float(data['roe'])
        gross_margin = float(data['gross_margin'])
        net_profit = float(data['net_profit'])

        app.logger.info(f"筛选股票: roe={roe}, gross_margin={gross_margin}, net_profit={net_profit}")

        # 调用 filter_stocks 函数
        result = filter_stocks(roe, gross_margin, net_profit)

        return jsonify(result), 200, {'Content-Type': 'application/json; charset=utf-8'}

    except KeyError as e:
        app.logger.error(f"缺少必要参数: {str(e)}")
        return jsonify({'error': f"缺少必要参数: {str(e)}"}), 400
    except ValueError as e:
        app.logger.error(f"参数格式错误: {str(e)}")
        return jsonify({'error': f"参数格式错误: {str(e)}"}), 400
    except Exception as e:
        app.logger.error(f"筛选股票失败: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 在应用启动时调用初始化
check_financial_directory()

if __name__ == '__main__':
    check_financial_directory()
    url = 'http://127.0.0.1:5000'
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        webbrowser.open(url)
    app.run(debug=True, host='0.0.0.0', port=5000)

    