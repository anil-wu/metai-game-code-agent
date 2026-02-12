# work_space_manager_agent 评估报告

## 目标与范围
- 目标：评估 `create_work_space_manager_agent` 的描述、指令、工具与 Swagger 文档的合理性，并结合需求 1–8 给出改进建议。
- 范围：`phaser_agent` 下的 agent 定义、工具实现与 Swagger 文档。

## 需求清单（1–8）
1. 判断当前用户的项目 ID；无则创建项目信息  
2. 判断本地工作目录 `WORKSPACE_ROOT/userid/project_id` 是否存在；无则创建  
3. 基于 project_id 获取用户客户端软件工程信息  
4. 若无客户端软件工程信息则创建  
5. 若有客户端软件工程信息则更新  
6. 若有客户端软件工程信息但无工程版本信息则创建  
7. 无工程版本信息则下载客户端工程模板并解压；基于工程目录生成工程元数据文件  
8. 更新工程版本信息  

## 当前实现概览
- 智能体实现：`phaser_agent/agents/work_space_manager_agent.py`
- 描述与指令：`phaser_agent/agents_prompts.json` 与 `phaser_agent/agent_model_configs.json`
- 工具实现：`phaser_agent/tools/project.py`
- Swagger：`agents/swagger.json`

## 现状匹配评估
### 描述与指令
- 现有描述与指令只覆盖“管理 workspace、拉取/更新版本、拉取软件信息、创建远端项目”等高层目标。
- 缺少明确的“输入字段、决策分支、流程步骤、失败回退策略”，无法直接驱动 1–8 的完整流程。

### 工具覆盖
已提供工具：
- create_remote_project：创建远端项目  
- get_sandbox_workspace_info：获取项目与文件列表  
- get_user_project_software_info：获取项目软件与最新清单  
- pull_software_version：获取文件下载信息  
- update_software_version：文件版本回滚  

缺失能力：
- 查询/选择项目 ID（按 user 或 token）  
- 本地工作目录创建与校验  
- 创建客户端软件工程信息  
- 更新客户端软件工程信息  
- 创建工程版本信息  
- 下载模板与解压  
- 生成工程元数据文件  

## Swagger 合理性评估
已存在接口：
- 项目：GET/POST `/api/v1/projects`  
- 项目文件：GET `/api/v1/projects/{projectId}/files`  
- 软件工程：GET/POST `/api/v1/projects/{projectId}/softwares`  
- 软件清单：GET `/api/v1/projects/{projectId}/software_manifests`  
- 创建版本清单：POST `/api/v1/software-manifests`  
- 文件回滚：POST `/api/v1/files/{id}/rollback`  

缺口与不一致：
- 未发现“更新软件工程信息”的接口，需求第 5 步与 Swagger 不一致。  
- “更新工程版本信息”在 Swagger 中更符合“创建清单记录”或“回滚文件版本”，需要业务层明确定义。  

## 结论
当前 `create_work_space_manager_agent` 的描述、指令、工具配置与 Swagger 之间不完全匹配需求 1–8，无法形成完整闭环。现有实现更接近“远端项目与版本信息的只读/回滚能力”，而非“完整工作区与软件工程生命周期管理”。

## 改进建议
### 1) 需求与接口对齐
- 明确“更新客户端软件工程信息”的目标与接口；如无更新接口，需求应改为“创建或读取”。  
- 明确“工程版本信息”的定义：  
  - 若是“软件清单版本”，应使用 `POST /api/v1/software-manifests`  
  - 若是“文件版本”，则是 `files/{id}/rollback` 或下载某版本  

### 2) 工具补齐
建议新增或封装以下工具：
- list_projects / get_project_by_id：用于判断 project_id  
- ensure_workspace_dir：确保 `WORKSPACE_ROOT/userid/project_id` 本地目录  
- create_project_software：封装 `POST /api/v1/projects/{projectId}/softwares`  
- update_project_software：若后端支持，封装更新接口  
- create_software_manifest：封装 `POST /api/v1/software-manifests`  
- download_and_extract_template：下载文件并解压  
- generate_project_metadata：基于工程目录生成元数据文件  

### 3) 指令改造为可执行流程
建议在指令中明确：
- 输入参数：user_id、project_id（可空）、project_name、description、template_id、technology_stack  
- 决策分支：  
  - project_id 缺失 → 查询项目 → 无则创建  
  - 本地目录缺失 → 创建  
  - 无软件信息 → 创建；有 → 更新  
  - 无版本信息 → 下载模板、解压、生成元数据、创建清单记录  
  - 最后更新版本记录或状态  

### 4) 描述修订
描述需体现“本地工作区 + 软件工程信息 + 版本与模板同步”的职责，以便上层编排准确选择该 agent。

## 关键引用
- 智能体实现：`phaser_agent/agents/work_space_manager_agent.py`  
- 描述与指令：`phaser_agent/agents_prompts.json`、`phaser_agent/agent_model_configs.json`  
- 工具实现：`phaser_agent/tools/project.py`  
- Swagger：`agents/swagger.json`

## 任务计划（Agents & Service）
### 总体目标
- 让 `create_work_space_manager_agent` 可闭环完成需求 1–8（可重复执行且幂等）。
- 对齐“需求 ↔ 工具 ↔ Swagger ↔ 提示词/指令”，消除缺口与语义不一致。
- 统一口径：软件工程信息（software）创建后不更新；工程版本信息=软件清单版本（software_manifest）。

### Agents 端（phaser_agent）
#### P0：指令/描述改造为可执行流程
- 在 `agents_prompts.json` 中明确：输入字段、决策分支、失败回退策略与最终输出（project_id、workspace 路径、版本/清单标识等）。
- 在 `agent_model_configs.json` 中确保该 agent 能调用完成 1–8 所需的全部工具（最小权限、最小集合）。
- 在 `work_space_manager_agent.py` 中按“判断/创建项目 → 确保本地目录 → 获取/创建软件工程信息 → 获取/创建软件清单版本 → 下载模板最新版本并覆盖解压 → 生成 `software_manifest.json` → 写入清单记录”串起闭环流程。

#### P0：工具能力补齐与封装
- ✅ project_id 处理：已补齐 `list_projects` 工具（GET `/api/v1/projects`），支持在 project_id 缺失时取 latest_project_id。
- ✅ 本地工作区：已补齐 `ensure_workspace_dir` 工具，基于 `phaser_agent/config.py` 的 `WORKSPACE_ROOT`，确保 `WORKSPACE_ROOT/userid/project_id` 存在且可写。
- ✅ 软件工程信息（software）：已补齐 `ensure_project_software` 工具（GET 列表 → 不存在则 POST 创建）；不提供更新分支（创建后不允许更改）。
- 版本/清单（software_manifest）：封装“获取最新清单 → 不存在则创建清单”的工具，并以 `POST /api/v1/software-manifests` 落库。
- 模板：从表 `software_template` 按模板名 `2d_game_client_phaser` 取信息，并通过 service 封装的下载 API 拉取模板最新版本；technology_stack 默认 `game engine is phaser`。
- 元数据文件：生成 `software_manifest.json`，存放于对应软件工程目录下，结构对齐 `SparkX_Table_Design.08_Manifest_Example`。
- 鉴权：统一使用 user token 透传调用 service。

#### P1：可靠性与验收用例
- 幂等与恢复：重复运行覆盖解压模板并重建 `software_manifest.json`；中途失败可重试并继续；关键步骤具备可检测的完成标志（目录/清单/元数据）。
- 验收用例覆盖：从“无 project_id、无本地目录、无软件工程信息、无版本信息”的初始状态执行到可用工作区；以及“已有信息”的更新路径。

### Service 端（API/Swagger）
#### P0：接口缺口与语义对齐
- 软件工程信息（software）：不提供更新接口，Swagger 明确“读取或创建”的唯一通路与字段约束。
- 工程版本信息：统一为软件清单版本（software_manifest），Swagger 明确“查询最新清单/创建清单”的契约、返回字段与错误码。

#### P0：项目与权限/归属
- 确保项目查询接口支持“当前用户可见项目”的筛选与稳定排序，便于 agent 在 project_id 缺失时做确定性选择。
- 明确 project_id 获取规则：project_id 缺失时以“最新项目”为默认；允许同名项目；统一以 user token 鉴权。

#### P1：模板与下载链路契约化
- 为“客户端下载模板并解压”提供稳定的契约：
  - 统一获取下载地址与校验信息（如有），下载地址不设置过期；
  - Swagger 中补齐响应示例与错误码（权限不足、资源不存在、下载失败等）。

#### P1：契约回归与联调验证
- Swagger 更新后，补齐联调用例：agent 端以 Swagger 为唯一契约完成 1–8 的闭环调用。
- 关键接口补齐最小回归：创建项目、创建/读取软件工程信息、创建/读取清单、回滚/下载（若保留）在同一权限模型下可用。

### 交付验收（Definition of Done）
- agent 在“全空状态”与“部分已存在状态”两条路径均可完成需求 1–8，并输出一致的结果摘要。
- Swagger 中不存在与需求冲突/缺失的关键接口；“更新软件工程信息”“版本信息”两处语义清晰且可实现。
- 可重复执行：同一用户同一 project_id 多次执行不产生不可控副作用（目录结构、清单记录、元数据一致性）。
