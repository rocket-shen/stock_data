let originalData = [];
let currentSort = { column: null, order: null };
let lastStockCode = null;
let cachedFinancialData = null;

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'text-red-500 mt-2';
    errorDiv.textContent = message;
    document.querySelector('.container').prepend(errorDiv);
    setTimeout(() => errorDiv.remove(), 5000);
}

// 更新 formatNumber 函数，支持千分符和两位小数
function formatNumber(value) {
    if (value == null || value === '' || isNaN(value)) {
        return '';
    }
    // 转换为数字，保留两位小数，添加千分符
    return Number(value).toLocaleString('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

async function fetchStockData() {
    const stockCode = document.getElementById('stockCode').value.trim();
    const startDate = document.getElementById('startDate').value.trim();
    const endDate = document.getElementById('endDate').value.trim();
    const sortColumn = document.getElementById('sortColumn').value;
    const sortOrder = document.getElementById('sortOrder').value;

    console.log('输入:', { stockCode, startDate, endDate, sortColumn, sortOrder });

    if (!stockCode) {
        showError('请输入证券代码。');
        return;
    }
    if (!startDate || !endDate) {
        showError('请输入起始日期和结束日期 (格式:YYYYMMDD)');
        return;
    }

    try {
        console.log('发送请求:', `/get_stock_data?symbol=${stockCode}&start_date=${startDate}&end_date=${endDate}&sort_column=${sortColumn}&sort_order=${sortOrder}`);
        const response = await fetch(`/get_stock_data?symbol=${stockCode}&start_date=${startDate}&end_date=${endDate}&sort_column=${sortColumn}&sort_order=${sortOrder}`);
        console.log('响应状态:', response.status);
        const data = await response.json();
        console.log('响应数据:', data);

        if (data.error) {
            showError(data.error);
            return;
        }

        originalData = data.table;
        document.getElementById('stockName').innerHTML = `<p><strong>股票名称:<span class="text-red-500">${data.stock_name}</span></strong></p>`;
        document.getElementById('dataInfo').innerHTML = `<p><strong>交易日:<span class="text-red-500">${data.shape[0]}</span>天</strong></p>`;
        document.getElementById('marketCapInfo').innerHTML = `
            <p><strong>最高市值:</strong><span class="text-red-500"> ${data.max_market_cap['市值（亿）']}</span> 亿 (日期: ${data.max_market_cap['日期']})</p>
            <p><strong>最低市值:</strong><span class="text-green-500"> ${data.min_market_cap['市值（亿）']}</span> 亿 (日期: ${data.min_market_cap['日期']})</p>
        `;
        document.getElementById('financialExtra').innerHTML=`<span class="text-red-500">股本：${formatNumber(data.filtered_dict['总股本'])}亿&nbsp;&nbsp;流通股本：${formatNumber(data.filtered_dict['流通股'])}亿</span><br>
        <span class="text-red-500">市值：${formatNumber(data.filtered_dict['总市值'])}亿&nbsp;&nbsp;&nbsp;现价：${formatNumber(data.current_price)}元</span>`;

        applyFilters();
        document.getElementById('stockTable').classList.remove('hidden');

        let financialData = cachedFinancialData;
        if (stockCode !== lastStockCode) {
            console.log('请求财务报表:', stockCode);
            const financialResponse = await fetch(`/get_financial_report?symbol=${stockCode}`);
            financialData = await financialResponse.json();
            cachedFinancialData = financialData;
            lastStockCode = stockCode;
        }

        if (financialData.error) {
            showError(financialData.error);
            return;
        }

        const financialTable = financialData.table;
        const financialHeaders = financialData.columns; // 使用后端返回的列顺序
        const financialHeaderRow = document.getElementById('financialHeader');
        const financialBody = document.getElementById('financialBody');
        financialHeaderRow.innerHTML = '';
        financialBody.innerHTML = '';

        if (financialTable.length === 0) {
            document.getElementById('financialContainer').classList.add('hidden');
            return;
        }
        // 定义需要格式化的列
        const numericColumns = [
            '营业总收入-营业总收入', '净利润-净利润', '每股收益',
            '每股净资产', '每股经营现金流量', '销售毛利率', '净资产收益率'
        ];
        // 渲染表头
        financialHeaders.forEach(header => {
            const th = document.createElement('th');
            th.className = 'p-2 border';
            th.textContent = header;
            financialHeaderRow.appendChild(th);
        });
        // 渲染表格内容
        financialTable.forEach(row => {
            const tr = document.createElement('tr');
            tr.innerHTML = financialHeaders.map(h => {
                const value = numericColumns.includes(h) ? formatNumber(row[h]) : (row[h] ?? '');
                return `<td class="p-2 border text-center">${value}</td>`;
            }).join('');
            financialBody.appendChild(tr);
        });

        document.getElementById('financialContainer').classList.remove('hidden');
    } catch (error) {
        console.error('请求失败:', error);
        showError('获取数据失败: ' + error.message);
    }
}

function renderTable(data) {
    const tableBody = document.getElementById('tableBody');
    tableBody.innerHTML = '';
    data.forEach(row => {
        const tr = document.createElement('tr');
        tr.classList.add('hover:bg-blue-300');
        tr.innerHTML = `
            <td class="p-2 border">${row['日期']}</td>
            <td class="p-2 border">${row['开盘']}</td>
            <td class="p-2 border">${row['收盘']}</td>
            <td class="p-2 border">${row['最高']}</td>
            <td class="p-2 border">${row['最低']}</td>
            <td class="p-2 border">${row['涨跌幅']}</td>
            <td class="p-2 border">${formatNumber(row['成交量'])}</td>
            <td class="p-2 border">${row['换手率']}</td>
            <td class="p-2 border">${formatNumber(row['市值（亿）'])}</td>
        `;
        tableBody.appendChild(tr);
    });
}

document.querySelectorAll('.sort-btn').forEach(button => {
    button.addEventListener('click', () => {
        const column = button.getAttribute('data-column');
        const order = button.getAttribute('data-order');
        currentSort = { column, order };
        document.querySelectorAll('.sort-btn').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');
        applyFilters();
    });
});

document.getElementById('sortColumn').addEventListener('change', () => {});
document.getElementById('sortOrder').addEventListener('change', () => {});

document.getElementById('fetchData').addEventListener('click', () => {
    console.log('查询数据按钮被点击');
    fetchStockData();
});

document.getElementById('stockCode').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.keyCode === 13) {
        console.log('回车触发查询');
        fetchStockData();
    }
});

function applyFilters() {
    let filteredData = [...originalData];
    filteredData.sort((a, b) => {
        if (currentSort.column === '日期') {
            const dateA = new Date(a[currentSort.column]);
            const dateB = new Date(b[currentSort.column]);
            return currentSort.order === 'asc' ? dateA - dateB : dateB - dateA;
        }
        const valueA = parseFloat(a[currentSort.column]) || 0;
        const valueB = parseFloat(b[currentSort.column]) || 0;
        return currentSort.order === 'asc' ? valueA - valueB : valueB - valueA;
    });
    renderTable(filteredData);
}