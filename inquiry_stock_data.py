from flask import Flask, request, jsonify, render_template
import os
import akshare as ak
import pandas as pd
import numpy as np
from flask_cors import CORS
from datetime import datetime
import logging
import webbrowser

app = Flask(__name__)
CORS(app, resources={r"/get_*": {"origins": ["http://localhost:5000"]}})

BASE_DIR = os.path.dirname(__file__)
SAVE_DIRECTORY = os.path.join(BASE_DIR, 'financial_reports')  # 更新为项目相对路径
stock_dict_a = np.load(os.path.join(BASE_DIR, 'stock_dict_a.npy'), allow_pickle=True).item()


def check_financial_directory():
    if not os.path.exists(SAVE_DIRECTORY):
        app.logger.error(f"财务报表文件夹不存在: {SAVE_DIRECTORY}")
        raise FileNotFoundError(f"财务报表文件夹不存在: {SAVE_DIRECTORY}")

@app.route('/')
def index():
    return render_template('index.html')

def fetch_stock_data(symbol, start_date, end_date):
    stock_name = stock_dict_a.get(symbol, '未知证券')
    app.logger.info(f"获取股票名称: {stock_name}")
    df = ak.stock_zh_a_hist(symbol=symbol, period='daily', start_date=start_date, end_date=end_date, adjust='')
    app.logger.info(f"获取股票数据: {df.shape}")

    stock_df = ak.stock_individual_info_em(symbol=symbol)
    needed_items = ['总股本', '流通股', '总市值']
    filtered_df = stock_df[stock_df['item'].isin(needed_items)]
    filtered_df = filtered_df.copy()
    filtered_df['value'] = filtered_df['value'] / 100000000
    filtered_dict = dict(zip(filtered_df['item'], filtered_df['value']))
    current_price = filtered_dict['总市值'] / filtered_dict['总股本']

    df['市值（亿）'] = np.where(df['换手率'] > 0, (df['成交额'] / df['换手率'] / 1000000).round(2), np.nan)
    df['日期'] = pd.to_datetime(df['日期']).dt.strftime('%Y/%m/%d')

    return df, stock_name, filtered_dict, current_price

def process_stock_data(df, sort_column, sort_order):
    max_market_cap = df.loc[df['市值（亿）'].idxmax(), ['日期', '市值（亿）']].to_dict()
    min_market_cap = df.loc[df['市值（亿）'].idxmin(), ['日期', '市值（亿）']].to_dict()

    ascending = sort_order == 'asc'
    top_50 = df.sort_values(by=sort_column, ascending=ascending).head(50)
    select_columns = top_50[['日期', '开盘', '收盘', '最高', '最低', '涨跌幅', '成交量', '换手率', '市值（亿）']].sort_values(by='日期', ascending=True)

    return max_market_cap, min_market_cap, select_columns

def fetch_financial_report(stock_code):
    file_names = [os.path.join(SAVE_DIRECTORY, f"业绩报表_{year}1231.csv") for year in range(2020, 2025)]
    results = []
    for file_name in file_names:
        if os.path.exists(file_name):
            try:
                df = pd.read_csv(file_name, encoding="utf_8_sig", dtype={'股票代码': str})
                if "股票代码" in df.columns:
                    df["股票代码"] = df["股票代码"].astype(str).str.strip()
                    stock_data = df[df["股票代码"] == stock_code]
                    if not stock_data.empty:
                        date_part = os.path.basename(file_name).split("_")[1].split(".")[0]
                        stock_data = stock_data.assign(报告期=date_part)
                        results.append(stock_data)
            except Exception as e:
                app.logger.error(f"读取文件 {file_name} 出错: {str(e)}")
                raise Exception(f"读取文件 {file_name} 出错: {str(e)}")
        else:
            app.logger.warning(f"文件 {file_name} 不存在")
    if not results:
        raise Exception(f"未找到股票代码 {stock_code} 的业绩数据")
    # 合并所有年份的数据
    perf_df = pd.concat(results, ignore_index=True)
    selected_columns = ['报告期', '营业总收入-营业总收入', '净利润-净利润', '每股收益', '每股净资产', '每股经营现金流量', '销售毛利率', '净资产收益率']
    available_columns = [col for col in selected_columns if col in perf_df.columns]
    data = perf_df[available_columns].to_dict(orient='records')

    return available_columns, data



@app.route('/get_stock_data')
def get_stock_data_route():
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

        response = {
            'shape': list(df.shape),
            'table': select_columns.to_dict(orient='records'),
            'stock_name': stock_name,
            'max_market_cap': max_market_cap,
            'min_market_cap': min_market_cap,
            'filtered_dict':filtered_dict,
            'current_price':current_price
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

    
# 在应用启动时调用初始化
check_financial_directory()

if __name__ == '__main__':
    url = 'http://127.0.0.1:5000'
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        webbrowser.open(url)
    app.run(debug=True, host='0.0.0.0', port=5000)

    