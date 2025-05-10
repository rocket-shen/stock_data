### 需要创建一个股票筛选功能
获取业绩数据：perf_data = ak.stock_yjbb_em(date="20241231")

2025-05-10 def filter_stocks(roe, gross_margin, net_profit):函数，通过 净资产收益率，毛利，净利润筛选符合条件的股票数据
前端POST请求@app.route('/get_filtered_stocks', methods=['POST'])调用函数