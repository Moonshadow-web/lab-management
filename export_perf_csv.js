// export_perf_csv.js - 用Node.js导出performanceData为CSV
const fs = require('fs');
const path = require('path');

// 读取data.js
const dataPath = path.join('d:', 'workbuddyprojects', '网页版-生免速查工具', 'data.js');
let content = fs.readFileSync(dataPath, 'utf-8');

// 提取performanceData
const match = content.match(/const performanceData\s*=\s*(\[[\s\S]*?\n\]);/);
if (!match) {
    console.error('未找到performanceData');
    process.exit(1);
}

// 执行JS代码获取数组
const performanceData = eval(match[1]);

// 定义CSV列
const headers = ['id', 'name', 'method', 'instrument', 'linearRange', 'reportableRange', 
                 'calibrator', 'traceability', 'reference'];

// 生成CSV
function escapeCsv(val) {
    const s = String(val || '');
    if (s.includes(',') || s.includes('"') || s.includes('\n') || s.includes('\r')) {
        return '"' + s.replace(/"/g, '""') + '"';
    }
    return s;
}

let csv = '\uFEFF'; // BOM for UTF-8
csv += headers.map(escapeCsv).join(',') + '\n';

for (const item of performanceData) {
    const row = headers.map(h => escapeCsv(item[h] || ''));
    csv += row.join(',') + '\n';
}

const outputPath = path.join('C:', 'Users', '81526', 'Desktop', '项目性能查询数据.csv');
fs.writeFileSync(outputPath, csv, 'utf-8');
console.log(`已导出 ${performanceData.length} 条记录到 ${outputPath}`);
