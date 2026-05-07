# Claude Code 会话检索指南

## 用途

当用户需要 PM 查看 Claude Code 的分析结论（性能诊断、代码审查、根因分析等），从 Claude Code 的本地会话日志中提取。

## 文件结构

```
~/.claude/
├── sessions/                    # 会话索引（sessionId → 元数据）
│   └── <pid>.json               # 单条会话元数据
├── projects/                    # 按工作目录组织的会话内容
│   └── <encoded-path>/          # cwd 路径的编码名（如 -mnt-c-Users-Administrator-Desktop）
│       ├── <sessionId>.jsonl    # 完整对话内容（JSONL，每行一个事件）
│       └── memory/              # Claude 自动积累的项目记忆
└── history.jsonl                # 全局历史索引
```

## 检索步骤

### 1. 找到用户关心的会话

```bash
# 查看所有会话元数据
cat ~/.claude/sessions/*.json | python3 -c "
import json, sys
for line in sys.stdin:
    l = line.strip()
    if not l: continue
    # 有些文件是单行完整 JSON，有些可能有多个记录
    try:
        data = json.loads(l) if l.startswith('{') else json.loads(l[l.index('{'):])
        print(f\"  [{data.get('sessionId','?')[:8]}...] cwd={data.get('cwd','?')}  started={data.get('startedAt','?')}  status={data.get('status','?')}  title={data.get('aiTitle','?')}\")
    except:
        pass
"
```

**关键字段**：
- `sessionId` — 标识该会话
- `cwd` — 工作目录（对应 projects/ 下的子目录）
- `startedAt` — 启动时间戳（毫秒）
- `status` — `idle` 表示已结束
- `aiTitle` — Claude 自动生成的会话标题
- `lastPrompt` — 最近的用户输入（最后一个 user 消息）

### 2. 定位会话内容文件

```bash
# 映射：cwd 路径 → projects/ 下的子目录名
# 路径中 / 替换为 -，: 替换为 -，. 替换为 -
# 例如 /mnt/c/Users/Administrator/Desktop → -mnt-c-Users-Administrator-Desktop

# 读取完整的会话内容
cat ~/.claude/projects/<encoded-path>/<sessionId>.jsonl
```

**注意**：文件可能很大（这篇会话 565 行 / 1.18MB）。用 `tail` 或按行范围读取。

### 3. 提取分析结论

结论通常在会话末尾的 assistant 消息中。JSONL 中每行是一个事件对象，关键的事件类型：

| 类型 | 说明 | 查找位置 |
|------|------|---------|
| `user` | 用户输入 | `message.content[0].text` 或 `tool_result` |
| `assistant` | AI 回复 | `message.content[?].type == "text"` 包含结论 |
| `system` | 系统事件 | `subtype == "away_summary"` 包含用户离开后的摘要 |
| `aiTitle` | 会话标题 | 元数据层，不在 JSONL 内 |

```bash
# 从 JSONL 提取最后的 AI 文本输出
python3 -c "
import json, sys

conclusions = []
with open('path/to/session.jsonl') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            event = json.loads(line)
            if event.get('type') == 'assistant':
                content = event.get('message', {}).get('content', [])
                for item in content:
                    if item.get('type') == 'text' and item.get('text'):
                        conclusions.append(('text', item['text']))
        except:
            pass

if conclusions:
    for t, c in conclusions:
        print(f'--- {t} ---')
        print(c[:2000])
else:
    print('No assistant text found')
"
```

### 4. 提取用户原始输入

```bash
# 获取用户最近一次输入（即诊断问题的 prompt）
python3 -c "
import json, sys

with open('path/to/session.jsonl') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            event = json.loads(line)
            if event.get('promptId'):
                print(json.dumps(event.get('message',{}).get('content',[]), ensure_ascii=False, indent=2)[:500])
        except:
            pass
"
```

### 5. 查找系统摘要（休眠时总结）

当会话因用户长时间离开而休眠时，Claude 会生成 `away_summary`：

```bash
grep 'away_summary' path/to/session.jsonl | python3 -c "
import json, sys
for line in sys.stdin:
    try:
        event = json.loads(line.strip())
        if event.get('subtype') == 'away_summary':
            print(event.get('content', ''))
    except:
        pass
"
```

## 快速命令（一站式提取）

```bash
# 参数：<sessionId>
function claude_session_summary() {
  local sid="$1"
  local file=$(find ~/.claude/projects -name "${sid}.jsonl" 2>/dev/null | head -1)
  if [ -z "$file" ]; then
    echo "Session $sid not found"
    return 1
  fi
  echo "=== 文件: $file ==="
  echo "=== 大小: $(wc -c < "$file") bytes, $(wc -l < "$file") lines ==="
  echo ""
  echo "=== 用户原始问题 ==="
  grep '"lastPrompt"' ~/.claude/sessions/*.json 2>/dev/null | grep -o '"lastPrompt":"[^"]*"' | head -3
  echo ""
  echo "=== 系统摘要 ==="
  grep 'away_summary' "$file" | python3 -c "
import json, sys
for line in sys.stdin:
    try:
        e = json.loads(line.strip())
        if e.get('subtype') == 'away_summary':
            print(e.get('content',''))
    except: pass
"
  echo ""
  echo "=== AI 结论（取最后 3 条） ==="
  python3 -c "
import json, sys
conclusions = []
with open('$file') as f:
    for line in f:
        line = line.strip()
        if not line: continue
        try:
            e = json.loads(line)
            if e.get('type') == 'assistant':
                for item in e.get('message',{}).get('content',[]):
                    if item.get('type') == 'text' and item.get('text'):
                        conclusions.append(item['text'])
        except: pass
for c in conclusions[-3:]:
    print(c)
    print('---')
"
}
```

## 注意事项

1. **文件可能很大**（1MB+），按行数范围读取，不要一次全部加载
2. **assistant 消息包含 thinking 和 text**：`type: "thinking"` 是内部思考过程，`type: "text"` 是输出给用户的结论
3. **工具调用结果**也包含在 JSONL 中（`tool_use_id` 标识），可以追溯 Claude 执行的具体命令
4. **会话可能处于进行中**（status=active），此时最后的消息可能不完整
5. Claude Code 和 Hermes 使用**不同的模型**（Claude 自身 vs Hermes 配置），分析结论的时效性取决于运行时间
