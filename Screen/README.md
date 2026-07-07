# 标题摘要四步筛选（TAA Screen）

本目录整理自 `D:\work\AI-external\FT_screen\screenTAA.py`，用于根据文献标题和摘要进行四步纳入/排除判断。当前代码默认使用 `gpt-5.4`，输出格式对齐既有结果文件，例如：

```text
D:\work\AI-external\TAA\cataract2step3and4.csv
```

## 四步筛选逻辑

1. `Response1`：判断文章是否同时满足目标疾病方向和 AI 方法。
2. `Response2`：排除不符合纳入标准的文章类型或研究设计，例如综述、meta 分析、会议摘要、动物实验、基础研究、二次研究等。
3. `Response3`：判断主要任务是否属于疾病诊断、疾病分类、预后预测或风险预测，并排除 image quality assessment、segmentation-only、quantitative measurement-only、isolated sign detection、treatment planning、surgical assistance、image generation、dataset construction 等非目标任务；同时提取 `Disease_type` 与 `Main_task`。
4. `Response4`：判断研究是否直接使用原始医学影像或视频作为模型输入。

脚本会按旧流程自动跳步：

- Step 1 为 `False` 时，不继续 Step 2-4。
- Step 2 为 `False` 时，不继续 Step 3-4。
- Step 3 为 `False` 时，不继续 Step 4。

## 目录文件

- `title_abstract_screen.py`：主入口，读取 CSV/Excel，执行四步筛选并导出 CSV。
- `prompts.py`：四步筛选提示词，包含多个疾病方向的配置。
- `screening_client.py`：早期 Batch API 封装，目前主流程不依赖它。
- `requirements.txt`：依赖列表。

## 输入格式

输入可以是单个 `.csv`、`.xlsx`、`.xls` 文件，也可以是包含这些文件的文件夹。

必须包含标题和摘要列，列名支持以下写法：

- 标题列：`Title`、`TITLE` 或 `title`
- 摘要列：`Abstract`、`ABSTRACT` 或 `abstract`

## 使用方法

处理 cataract CSV，并输出类似 `cataract2step3and4.csv` 的结果：

```powershell
cd G:\ai-external\codes\Screen
python title_abstract_screen.py --input "D:\work\AI-external\TAA\cataract2.csv" --disease cataract
```

指定输出目录：

```powershell
python title_abstract_screen.py --input "D:\work\AI-external\TAA\cataract2.csv" --output-dir ".\outputs" --disease cataract
```

处理已完成 Step 1/2 的文件并从已有列继续，可使用：

```powershell
python title_abstract_screen.py --input "D:\work\AI-external\TAA\cataract2step1and2.csv" --disease cataract --resume
```

默认输出后缀是 `step3and4`。例如输入 `cataract2.csv`，默认输出为：

```text
cataract2step3and4.csv
```

如需改后缀：

```powershell
python title_abstract_screen.py --input ".\papers.csv" --output-suffix "screened"
```

## 疾病参数

`--disease` 支持：

- `cataract`
- `amd`
- `glaucoma`
- `drdme`
- `rop`
- `ocularsurface`
- `oculomics`

也可以用 `--disease-text` 自定义 Step 1 的疾病描述。

## Step 4 类型

`--step4-kind` 支持。当前默认值为 `video`，即允许原始医学影像或视频帧作为模型输入：

- `video`：默认，允许原始医学影像或视频帧输入，接近旧代码中的 `prompt_4_mh`。
- `standard`：只判断原始医学影像输入。
- `anterior`：前节影像场景，例如 AS-OCT、UBM、裂隙灯、前节照片、房角镜等。

## 输出列

结果 CSV 会保留原始列，并追加或更新以下列：

- `Response1`
- `Response1_decision`
- `Response1_confidence`
- `Response1_reason`
- `Response2`
- `Response2_decision`
- `Response2_confidence`
- `Response2_reason`
- `Response3`
- `Response3_decision`
- `Response3_confidence`
- `Response3_reason`
- `Disease_type`
- `Main_task`
- `Response4`
- `Response4_decision`
- `Response4_confidence`
- `Response4_reason`

## 当前步骤不处理的标准

以下标准不在本标题摘要 LLM 四步预筛代码中判断，按当前研究流程留给后续人工或全文阶段处理：

- 非英文文献。
- 无法获取全文的文献。

Supplementary Table 2 会在后期根据最终提示词另行更新。

## API Key

默认模型为 `gpt-5.4`，默认从环境变量 `OPENAI_API_KEY` 读取 API Key；脚本也会自动尝试加载 `G:\ai-external\codes\.env`。也可以指定其他模型或环境变量：

```powershell
python title_abstract_screen.py --input ".\papers.csv" --model "gpt-5.4" --api-key-env "OPENAI_API_KEY2"
```

## 依赖安装

```powershell
pip install -r requirements.txt
```

## 注意事项

- 运行脚本会逐行调用模型 API，可能产生费用。
- 当前流程只使用标题和摘要，不读取全文 PDF。
- 模型返回 JSON 解析失败时，对应步骤会写入 `parse_error`，错误信息保存在该步骤的 `reason` 列中。


