# 第 8 课：Agent Tracing——用 Trace 与 Span 还原一次运行

前几课让排查助手能读日志、保存状态，并限制执行范围。现在假设它接到一次排查任务，却迟迟没有给出诊断。手里的记录是：

```text
第一次模型请求：1.2 秒，HTTP 200
读取服务日志：0.05 秒，成功
整次任务：等了三分钟，超时
```

模型和工具都拿出了成功回执，用户还没拿到结果。日志像在轮流给自己开无罪证明。

需要把这些记录接回同一次运行，找出等待发生在哪一步。上面的时间是教学数据，不是线上事故实测；本课另用一次临时文件读取，展示记录怎样产生。

## 1. Trace 与 Span：运行身份和步骤关系

先给整次排查一个编号，再给里面的步骤各自编号：

```text
Trace trace_42：排查订单接口
|
+-- Span run：整次 Agent 运行
    |
    +-- Span model_1：模型申请读取日志
    +-- Span read_1：工具读取服务日志
    +-- Span model_2：模型根据日志继续判断
```

**Trace** 把一次运行的相关步骤组织在一起；**Span** 描述其中一个有开始、结束和结果的步骤。[1] 本例按模型请求、工具执行划分，也可以按需要记录审批等待、远程请求或子任务。

Span 不等于一行日志。一次模型请求期间写了十条日志，仍然可以属于同一个 Span；发生重试时，才需要区分新的一次尝试。

第一次模型请求的简化记录可以是：

```json
{
  "trace_id": "trace_42",
  "span_id": "model_1",
  "parent_span_id": "run",
  "name": "model_call",
  "started_at_ms": 0,
  "ended_at_ms": 1200,
  "status": "ok"
}
```

`trace_id` 把相关记录归在一起，`span_id` 区分步骤，`parent_span_id` 指向父步骤。示例里的几个步骤都由整次 Agent 运行包住，所以父编号都是 run。编号和相对时间经过简化，不是标准协议的完整格式。

父子关系说明归属，不说明先后。先发生、后发生还是并行，要看时间；工具由哪次模型响应提出，还要结合 Tool Call。两个步骤有同一个父节点，不等于前一个调用了后一个。

同一 Trace 内的 Span 编号不能重复。配套单进程练习要求父节点先写入；分布式收集可能先收到子节点，需要等父记录到达后再连接，不能照搬这个限制。

## 2. Instrumentation：记录生命周期与耗时

给开头的步骤补上起止时间，等待位置就清楚了。下面仍是同一组教学数据，时间单位为毫秒：

| 步骤 | 开始 | 结束 | 耗时 | 记录的结果 |
| --- | --- | --- | --- | --- |
| model_1 | 0 | 1200 | 1200 | 请求正常返回 |
| read_1 | 1200 | 1250 | 50 | 日志读取成功 |
| model_2 | 1250 | 180000 | 178750 | 等待中耗尽任务期限 |

下一步应查第二次模型请求的超时记录、网络和服务状态，不必先重写读文件函数。这个表定位了调查范围，还不能单独证明是断网、服务拥堵，还是客户端处理出了问题。

这些字段要在实际动作发生时记录。在调用前后加上观测代码，叫 **Instrumentation（埋点）**。下面为一次读取准备新的 Span，并记录耗时：

```python
import tempfile
from pathlib import Path
from time import perf_counter

def read_observed(path, span):
    span["status"] = "running"
    span["started_at_ms"] = perf_counter() * 1000
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as error:
        span["status"] = "error"
        span["error_type"] = type(error).__name__
        raise
    else:
        span["status"] = "ok"
        return content
    finally:
        span["ended_at_ms"] = perf_counter() * 1000
        span["duration_ms"] = span["ended_at_ms"] - span["started_at_ms"]

with tempfile.TemporaryDirectory() as folder:
    path = Path(folder) / "service.log"
    path.write_text("order lookup failed", encoding="utf-8")
    span = {
        "trace_id": "trace_demo", "span_id": "read_1",
        "parent_span_id": "run", "name": "read_file",
    }
    print(read_observed(path, span))
    print(span["status"], span["duration_ms"] >= 0)
```

输出为：

```text
order lookup failed
ok True
```

先记 running，再读取；成功时返回原内容，失败时记下异常类型并用 `raise` 继续抛出。`finally` 在正常返回或异常退出这段代码时都会执行，用来补结束时间。计时器只测本机间隔，这里的读数不是日历时间，不能拿去与另一台机器直接对表。

这段代码只读临时假文件，省略了根 Span 的创建与保存。接入 Agent 时，应包住已有的受限工具，保留路径校验和 Sandbox，不能另开不受限的读入口。进程被强制终止时，finally 也可能来不及运行；留下未结束的 Span，只能说明记录不完整。

如果步骤并行，耗时不能直接相加。两项工作同时各跑一秒，用户可能只等一秒；整个任务耗时要看根 Span 的起止时间。

## 3. Outcome 与重试：关联结果和执行身份

刚才的 `status="ok"` 说明读取正常结束。假如文件里只有“没有找到订单”，工具照常返回，用户的排查目标却可能还没完成。

本书把两种结果分开记录：

```text
status  = ok       这次调用正常结束
outcome = failed   对应的业务目标没有完成
```

这是教学字段，不要求所有框架同名。业务结果需要依据任务要求和实际产物判断，不能看见 HTTP 200 就填 succeeded。尚不确定时应保留 unknown。

发生重试后，还要分清它们是不是在处理同一张申请。假设一项已经确认可安全重试的读取，第一次超时，第二次成功：

| 尝试 | tool_call_id | execution_id | span_id |
| --- | --- | --- | --- |
| 第一次 | call_read | exec_1 | span_1 |
| 第二次 | call_read | exec_2 | span_2 |

工具调用编号相同，执行编号和步骤编号不同，两次仍属于同一 Trace。每次尝试保留各自的时间与结果，不能用第二次成功覆盖第一次超时。

Trace 负责关联这些尝试，不负责批准重试。把上一课留下的几类记录放在一起看：

| 记录 | 主要回答什么 |
| --- | --- |
| Transcript | 用户、模型和工具说过什么，怎样继续对话？ |
| Ledger | 工具执行到了什么状态，恢复时有什么证据？ |
| Trace | 哪些步骤属于这次运行，时间花在哪，哪里出了错？ |

写报告后崩溃，Transcript 可能缺回执，Ledger 可能停在 running，Trace 也可能少了结束记录。是否重做仍按第 6 课的恢复规则，核对账本、幂等保护和实际文件；Trace 不能证明外部副作用恰好发生一次。

## 4. Exporter：记录怎样到达存储

刚才的示例只把 Span 放在内存字典里。程序结束，字典就没了；创建记录不等于保存记录。

常见的处理路径是：

```text
动作前后产生 Span
-> 缓存、筛选与处理
-> Exporter 发送
-> 本地文件或集中存储
-> 查询或绘制时间线
```

**Exporter（导出器）** 负责把记录送往配置的去向，可以是本地文件，也可以是远端收集服务。因此，项目目录没有 `trace.jsonl`，不能单独证明没有 Tracing。

核验版本的 OpenClaw 通过可选插件导出记录，需要相应诊断、插件与导出配置配合开启；记录可以送到集中收集服务，不一定保存在项目目录。[2] 一个界面能画时间线，也不意味着它一定使用标准 Trace：还要看背后的记录结构和关联方式。

Agent Loop 可以在关闭 Tracing 时运行。默认关闭或不导出，能把采集范围、存储位置和开销的选择留给部署者。多轮调用、重试和远程执行变多时，关联记录的价值才更明显。

如果一次读取和返回就能看清问题，我不会先搭观测平台。等日志无法说明“这是谁的哪一步、为什么卡住”，再补相应埋点和查询能力。

## 5. 数据治理：导出范围与尾部采样

服务日志、工具参数、异常消息和 HTTP Header 都可能带有秘密。只给 `content` 打码不够，凭据换个字段名就可能出门。

更稳妥的起点是只导出明确允许的字段：

```python
attributes = {
    "model": "example-model",
    "duration_ms": 1200,
    "authorization": "示例凭据",
}
allowed_names = {"model", "duration_ms"}

exported = {}
for name, value in attributes.items():
    if name in allowed_names:
        exported[name] = value

print(exported)
```

输出为 `{'model': 'example-model', 'duration_ms': 1200}`，原字典不变。白名单只管字段名，值仍要检查：允许任意文本或路径时，还需要限制内容、截断或遮盖。第 2 节只记录异常类型，就是避免直接把可能含路径、凭据的整段错误塞进观测数据。

这些检查应在发送前完成；本地文件和临时缓存也要限制访问与保留时间。保留故障证据，不等于可以完整复制用户材料。

记录量增加后，可以保留失败 Trace，抽样保留成功 Trace。任务刚开始时还不知道最终结果，需要先临时收集，再决定去留。这叫 **Tail Sampling（尾部采样）**。在开始时决定的 Head Sampling 能更早减少采集开销，却可能没选中后来失败的任务。

最小保留判断如下。`finished` 表示调用方已经确认这次运行结束且步骤收集齐全；`keep_success` 是外部传入的成功抽样结果：

```python
def should_keep(finished, spans, keep_success):
    if not finished:
        return None

    for span in spans:
        if span["status"] == "error":
            return True
        if span.get("outcome") in {"failed", "unknown"}:
            return True

    return keep_success

spans = [{"status": "ok", "outcome": "failed"}]
print(should_keep(True, spans, False))
```

输出为 `True`：调用正常结束，但业务失败，仍应保留。`None` 表示等待，不能当作 False 丢掉。并非每个子步骤都有 outcome，但根步骤应有本次任务的业务结论，缺乏依据时记 unknown。

这段判断不解决缓冲耗尽、晚到记录或进程崩溃。真实系统可能要等候一段时间再采样，也可能丢失部分记录；“错误全留”是策略目标，不是几行代码提供的绝对保证。

现在能沿同一 Trace 找到第二次模型请求，并进一步调查超时原因。下一课的 Evaluation 换一个问题：让不同版本做同一组任务，怎样判断它们是否真正完成要求、有没有退步？

## 资料与配套实验

1. [OpenTelemetry：Traces](https://opentelemetry.io/docs/concepts/signals/traces/)
2. [OpenClaw：已核验版本的 OpenTelemetry 配置](https://github.com/openclaw/openclaw/blob/64da06a78ffa98c5bb425cc79059d992260a4c76/docs/gateway/opentelemetry.md)
3. [配套实验与完整实现](../../exercises/lesson-08-tracing/README.md)
4. [固定源码、导出去向及项目对照](../../research/08-tracing-source-verification.md)
5. [候选代码检查](check_lesson_08.py)：`python -B experiments/reading-pilot/check_lesson_08.py`，检查教学片段和临时文件读取，不调用模型、不发送遥测。
