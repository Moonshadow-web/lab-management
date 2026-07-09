// 从项目根目录的 data.js 提取 performanceData / instrumentData / manualData 三个数组，输出 seed_data.json
// data.js 是含 DOM 代码的网页脚本，不能直接 require；且数组内部带有 // 行注释。
// 这里用语法感知扫描器：正确处理字符串/模板字符串（含 ${...}）与 //、/* */ 注释，
// 先定位数组匹配括号，再去除注释后 eval。
const fs = require('fs');
const path = require('path');

const srcPath = path.resolve(__dirname, '../../../data.js');
const src = fs.readFileSync(srcPath, 'utf-8');

// 在字符串/模板之外时跳过 // 与 /* */ 注释
function skipComment(src, i) {
  if (src[i] === '/' && src[i + 1] === '/') {
    while (i < src.length && src[i] !== '\n') i++;
    return i;
  }
  if (src[i] === '/' && src[i + 1] === '*') {
    i += 2;
    while (i < src.length && !(src[i] === '*' && src[i + 1] === '/')) i++;
    return i + 1;
  }
  return i;
}

// 定位 const NAME = [ 的匹配结束 ']'
function findArrayClose(src, name) {
  const re = new RegExp('const\\s+' + name + '\\s*=\\s*\\[', 'm');
  const m = src.match(re);
  if (!m) return -1;
  const open = m.index + m[0].length - 1; // 指向 '['
  let depth = 0;
  let inStr = null;
  let escape = false;
  let tpl = 0; // 模板字符串内 ${ } 嵌套深度
  for (let i = open; i < src.length; i++) {
    const c = src[i];
    if (inStr) {
      if (inStr === '`') {
        if (escape) { escape = false; continue; }
        if (c === '\\') { escape = true; continue; }
        if (tpl > 0) {
          if (c === '{') tpl++;
          else if (c === '}') tpl--;
          else if (c === '[') depth++;
          else if (c === ']') { depth--; if (depth === 0) return i; }
          continue;
        } else {
          if (c === '`') { inStr = null; continue; }
          if (c === '$' && src[i + 1] === '{') { tpl = 1; i++; continue; }
          continue;
        }
      } else {
        if (escape) { escape = false; continue; }
        if (c === '\\') { escape = true; continue; }
        if (c === inStr) { inStr = null; continue; }
        continue;
      }
    } else {
      const j = skipComment(src, i);
      if (j !== i) { i = j; continue; }
      if (c === '"' || c === "'") { inStr = c; continue; }
      if (c === '`') { inStr = '`'; continue; }
      if (c === '[') { depth++; continue; }
      if (c === ']') { depth--; if (depth === 0) return i; continue; }
    }
  }
  return -1;
}

// 去除注释（保留字符串/模板内原文）
function stripComments(s) {
  let out = '';
  let inStr = null;
  let escape = false;
  let tpl = 0;
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (inStr) {
      out += c;
      if (inStr === '`') {
        if (escape) { escape = false; continue; }
        if (c === '\\') { escape = true; continue; }
        if (tpl > 0) { if (c === '{') tpl++; else if (c === '}') tpl--; continue; }
        else { if (c === '`') { inStr = null; continue; } if (c === '$' && s[i + 1] === '{') { tpl = 1; i++; continue; } continue; }
      } else {
        if (escape) { escape = false; continue; }
        if (c === '\\') { escape = true; continue; }
        if (c === inStr) { inStr = null; continue; }
        continue;
      }
    } else {
      const j = skipComment(s, i);
      if (j !== i) { i = j; continue; }
      if (c === '"' || c === "'") { inStr = c; out += c; continue; }
      if (c === '`') { inStr = '`'; out += c; continue; }
      out += c;
    }
  }
  return out;
}

function extractArray(name) {
  const close = findArrayClose(src, name);
  if (close < 0) {
    console.error('未找到数组: ' + name);
    return [];
  }
  const re = new RegExp('const\\s+' + name + '\\s*=\\s*\\[', 'm');
  const mo = src.match(re);
  const openBracket = mo.index + mo[0].length - 1;
  const raw = src.slice(openBracket, close + 1); // 保留 [ 与 ]
  try {
    const fn = new Function('return (' + stripComments(raw) + ');');
    const arr = fn();
    return Array.isArray(arr) ? arr : [];
  } catch (e) {
    console.error('解析 ' + name + ' 失败: ' + e.message);
    return [];
  }
}

const result = {
  performanceData: extractArray('performanceData'),
  instrumentData: extractArray('instrumentData'),
  manualData: extractArray('manualData'),
};

const out = path.resolve(__dirname, 'seed_data.json');
fs.writeFileSync(out, JSON.stringify(result, null, 2), 'utf-8');
console.log(
  '已生成 seed_data.json ->', out,
  '\n  performanceData:', result.performanceData.length,
  '\n  instrumentData:', result.instrumentData.length,
  '\n  manualData:', result.manualData.length
);
