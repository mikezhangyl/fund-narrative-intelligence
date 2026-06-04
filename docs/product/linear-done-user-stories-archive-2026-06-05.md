# Linear Done User Stories Archive - 2026-06-05

## 归档范围

本文件归档 Linear 项目 `Fund Narrative Intelligence` 中截至 2026-06-05 拉取时仍未归档、状态为 `Done` 的 issue。虽然用户口径称为 user stories，Linear 中实际包含 `User Story`、`Epic`、`Task`、`Defect`、`Test` 等类型；为了清理完整性，本次全部纳入归档。

数据来源为 Linear MCP 查询：

```text
project = Fund Narrative Intelligence
state = Done
includeArchived = false
orderBy = createdAt
page_size = 20
```

本次共归档 `157` 条 Done issue。

## 删除状态

用户要求“归档后删除 Done US”。本次没有执行 Linear issue 删除或归档，因为当前可用 Linear 工具只暴露 issue 读取/更新，以及 comment、attachment、customer need、status update 等对象的删除能力，没有暴露 issue delete/archive 工具。

因此：

* 已完成：在 repo 中保存 Done issue 归档说明和完整清单。
* 未完成：Linear Done issue 删除/归档。
* 未执行替代操作：没有把 Done issue 改到其他状态，也没有删除评论或附件来冒充 issue 删除。

## 阶段笔记

### M19 - Narrative Source Deep Mining

这一批完成了叙事数据源深挖的 PM/ARCH 规划、轻量 lakehouse、source event/fact schema、合规和反爬风险模型、source quality、实体去重、crawler adapter、fresh digest、official disclosure、public web、community/social pilot、Tushare news live smoke，以及 FNI 消费 gateway source events 的边界。

关键结论：外部数据源接入归 `stock-data-gateway`；FNI 只消费 provider-neutral gateway contracts，并负责探针、报告、source quality 展示和 narrative digest 消费侧。

### M18 - Collaboration Governance & Release Readiness

完成协作交接、备份恢复、角色和 release handoff 规划。目标是让审查、交付和本地迁移不依赖聊天历史。

### M17 - Historical Replay & Evaluation Lab

完成历史 replay、稳定性评估、噪音评估、replay 输入和 run artifact 合同。明确这是系统质量评估，不是交易回测。

### M16 - Narrative Research Workbench

完成 narrative timeline、source-event search、evidence graph、比较视图、analyst notes/export 的 PM/ARCH 需求。

### M15 - Durable Workspace Persistence & Personalization

完成 workspace saved views、preferences、import/export、storage repository 和 migration-ready 边界。

### M14 - Interactive Product Shell & Release Packaging

完成本地产品壳、artifact browser、config preflight、one-command release、artifact manifest、route/data-source contract、demo/release checklist。

### M13 - Production Scale & Assisted Intelligence

完成生产可观测性、freshness/SLA、AI assisted summaries 的 citation/safety contract、feedback loop、access governance。AI 被限定为解释/摘要，不拥有 trust、score 或 promotion 状态。

### M12 - Portfolio & Fund Narrative Workspace

完成基金/组合叙事 dashboard、watchlists、exposure change alerts、radar-to-fund impact drilldown、workspace boundary 和 exposure snapshot API 合同。

### M11 - Evidence Intelligence & Narrative Quality

完成 evidence quality scorecard、structured extraction review、staleness/contradiction、source lineage、quality scoring、audit export 合同。

### M10 - Productized Narrative Operations

完成 live credential smoke、Narrative Radar UI、review workflow、scheduling、durable storage migration readiness、validation taxonomy、state machine 和 UI boundary。

### M9 - Narrative Radar Service

完成 Narrative Radar 的 PM/ARCH 边界、bubble API、heat/trend scoring、source drilldown、market confirmation boundary、score explainability、time-series model 和 trust/review 集成。

### M5-M8 - Release, Source Expansion, Fund Workflow, Governance

完成 baseline merge/release、live validation、structured news/announcement intake、fund narrative change report、reviewable fund report pack、governance audit、storage migration path 和 gateway change-request protocol。

### M1-M4 - Foundational FNI/Narrative Service Work

完成最早的 market data capability inventory、candidate detail、evidence drilldown、review workspace、trusted promotion workflow、source disclosure、developer handoff、API contract、append-only ledger、gateway boundary 和 acceptance harness。

## Done Issue 清单

| ID | Title | Milestone / Area | Priority |
| --- | --- | --- | --- |
| MIK-250 | [FNI-CONSUMER][R13] Narrative source gateway consumer contract and probes | M19 - Narrative Source Deep Mining | Urgent |
| MIK-248 | [ARCH-R13] Search and vector index deferral plan | M19 - Narrative Source Deep Mining | High |
| MIK-245 | [ARCH-R13] Lightweight narrative lakehouse architecture spec | M19 - Narrative Source Deep Mining | Urgent |
| MIK-244 | [PM-R13] Lightweight lakehouse user scenarios and data classes | M19 - Narrative Source Deep Mining | Urgent |
| MIK-243 | [ARCH-R13] Narrative evidence storage model feasibility | M19 - Narrative Source Deep Mining | Urgent |
| MIK-242 | [PM-R13] China community and social source access investigation | M19 - Narrative Source Deep Mining | High |
| MIK-239 | [PM-R13] Tushare news permission and live data smoke | M19 - Narrative Source Deep Mining | Urgent |
| MIK-234 | [ARCH-P1][R13] Entity resolution and deduplication contract for narrative sources | M19 - Narrative Source Deep Mining | High |
| MIK-233 | [ARCH-P1][R13] Fresh narrative digest pipeline contract | M19 - Narrative Source Deep Mining | High |
| MIK-232 | [ARCH-P1][R13] Crawler adapter contract and robots/rate-limit policy | M19 - Narrative Source Deep Mining | High |
| MIK-231 | [ARCH-P0][R13] Source reliability, licensing, and anti-bot risk scoring | M19 - Narrative Source Deep Mining | Urgent |
| MIK-230 | [ARCH-P0][R13] Narrative source-event and fact schema v2 | M19 - Narrative Source Deep Mining | Urgent |
| MIK-229 | [ARCH-P0][R13] Source acquisition governance and compliance model | M19 - Narrative Source Deep Mining | Urgent |
| MIK-228 | [P0][PM-R13] Today's narrative monitoring digest requirement | M19 - Narrative Source Deep Mining | Urgent |
| MIK-227 | [P1][PM-R13] Community and social heat source pilot plan | M19 - Narrative Source Deep Mining | High |
| MIK-226 | [P1][PM-R13] Public web and industry media crawler pilot plan | M19 - Narrative Source Deep Mining | High |
| MIK-225 | [P0][PM-R13] Official disclosure and regulator source intake plan | M19 - Narrative Source Deep Mining | Urgent |
| MIK-223 | [P0][PM-R13] Narrative source acquisition decision matrix | M19 - Narrative Source Deep Mining | Urgent |
| MIK-222 | [ARCH-R13] Architecture requirement pack for narrative source deep mining | M19 - Narrative Source Deep Mining | Urgent |
| MIK-221 | [PM-R13] Product requirement pack for narrative source deep mining | M19 - Narrative Source Deep Mining | Urgent |
| MIK-200 | [ARCH-P1][R12] Release governance and operator handoff contract | M18 - Collaboration Governance & Release Readiness | Medium |
| MIK-199 | [ARCH-P1][R12] Backup restore archive schema | M18 - Collaboration Governance & Release Readiness | Medium |
| MIK-198 | [ARCH-P0][R12] Collaboration role and handoff model | M18 - Collaboration Governance & Release Readiness | High |
| MIK-197 | [P1][PM-R12] Operator onboarding and release notes | M18 - Collaboration Governance & Release Readiness | Medium |
| MIK-196 | [P1][PM-R12] Backup restore and portable release archive | M18 - Collaboration Governance & Release Readiness | Medium |
| MIK-195 | [P0][PM-R12] Collaborative review handoff workflow | M18 - Collaboration Governance & Release Readiness | High |
| MIK-194 | [ARCH-P1][R11] Replay job storage and artifact contract | M17 - Historical Replay & Evaluation Lab | Medium |
| MIK-193 | [ARCH-P1][R11] Evaluation metric schema without trading claims | M17 - Historical Replay & Evaluation Lab | Medium |
| MIK-192 | [ARCH-P0][R11] Replay input and run schema | M17 - Historical Replay & Evaluation Lab | High |
| MIK-191 | [P1][PM-R11] Alert usefulness and noise review | M17 - Historical Replay & Evaluation Lab | Medium |
| MIK-190 | [P1][PM-R11] Radar and quality stability evaluation | M17 - Historical Replay & Evaluation Lab | Medium |
| MIK-189 | [P0][PM-R11] Historical replay runner | M17 - Historical Replay & Evaluation Lab | High |
| MIK-188 | [ARCH-P1][R10] Analyst note and research export contract | M16 - Narrative Research Workbench | Medium |
| MIK-187 | [ARCH-P1][R10] Evidence graph and comparison model | M16 - Narrative Research Workbench | Medium |
| MIK-186 | [ARCH-P0][R10] Timeline and search API contract | M16 - Narrative Research Workbench | High |
| MIK-185 | [P1][PM-R10] Analyst notes and research export pack | M16 - Narrative Research Workbench | Medium |
| MIK-184 | [P1][PM-R10] Narrative comparison and evidence graph | M16 - Narrative Research Workbench | Medium |
| MIK-183 | [P0][PM-R10] Narrative timeline and source-event search | M16 - Narrative Research Workbench | High |
| MIK-182 | [ARCH-P1][R9] Workspace import/export manifest contract | M15 - Durable Workspace Persistence & Personalization | Medium |
| MIK-181 | [ARCH-P1][R9] Preference redaction and validation contract | M15 - Durable Workspace Persistence & Personalization | Medium |
| MIK-180 | [ARCH-P0][R9] Workspace persistence schema and repository contract | M15 - Durable Workspace Persistence & Personalization | High |
| MIK-179 | [P1][PM-R9] Workspace import and export package | M15 - Durable Workspace Persistence & Personalization | Medium |
| MIK-178 | [P1][PM-R9] User preferences and workflow defaults | M15 - Durable Workspace Persistence & Personalization | Medium |
| MIK-177 | [P0][PM-R9] Persistent workspace store and saved views | M15 - Durable Workspace Persistence & Personalization | High |
| MIK-176 | [ARCH-R12] Architecture requirement pack for collaboration governance and release readiness | M18 - Collaboration Governance & Release Readiness | High |
| MIK-175 | [PM-R12] Product requirement pack for collaboration governance and release readiness | M18 - Collaboration Governance & Release Readiness | High |
| MIK-174 | [ARCH-R11] Architecture requirement pack for historical replay and evaluation lab | M17 - Historical Replay & Evaluation Lab | High |
| MIK-173 | [PM-R11] Product requirement pack for historical replay and evaluation lab | M17 - Historical Replay & Evaluation Lab | High |
| MIK-172 | [ARCH-R10] Architecture requirement pack for narrative research workbench | M16 - Narrative Research Workbench | High |
| MIK-171 | [PM-R10] Product requirement pack for narrative research workbench | M16 - Narrative Research Workbench | High |
| MIK-170 | [ARCH-R9] Architecture requirement pack for durable workspace persistence and personalization | M15 - Durable Workspace Persistence & Personalization | High |
| MIK-169 | [PM-R9] Product requirement pack for durable workspace persistence and personalization | M15 - Durable Workspace Persistence & Personalization | High |
| MIK-168 | [ARCH-P1][R8] Product shell acceptance and demo checklist | M14 - Interactive Product Shell & Release Packaging | High |
| MIK-167 | [ARCH-P1][R8] Local release orchestration and verification contract | M14 - Interactive Product Shell & Release Packaging | Urgent |
| MIK-166 | [ARCH-P0][R8] Artifact index and manifest contract | M14 - Interactive Product Shell & Release Packaging | Urgent |
| MIK-165 | [ARCH-P0][R8] Product shell route and data-source contract | M14 - Interactive Product Shell & Release Packaging | Urgent |
| MIK-164 | [P1][PM-R8] One-command local release package | M14 - Interactive Product Shell & Release Packaging | High |
| MIK-163 | [P1][PM-R8] Operational control panel and config preflight | M14 - Interactive Product Shell & Release Packaging | Urgent |
| MIK-162 | [P0][PM-R8] Artifact browser and run history | M14 - Interactive Product Shell & Release Packaging | High |
| MIK-161 | [P0][PM-R8] Integrated local product shell navigation | M14 - Interactive Product Shell & Release Packaging | High |
| MIK-160 | [ARCH-R8] Architecture requirement pack for interactive product shell and release packaging | M14 - Interactive Product Shell & Release Packaging | High |
| MIK-159 | [PM-R8] Product requirement pack for interactive product shell and release packaging | M14 - Interactive Product Shell & Release Packaging | High |
| MIK-158 | [ARCH-P1][R7] Feedback and access governance model | M13 - Production Scale & Assisted Intelligence | Medium |
| MIK-157 | [ARCH-P1][R7] AI assistance safety and citation contract | M13 - Production Scale & Assisted Intelligence | Medium |
| MIK-156 | [ARCH-P0][R7] Data freshness and SLA schema | M13 - Production Scale & Assisted Intelligence | High |
| MIK-155 | [ARCH-P0][R7] Observability and runbook contract | M13 - Production Scale & Assisted Intelligence | High |
| MIK-154 | [P1][PM-R7] User feedback loop for narrative quality | M13 - Production Scale & Assisted Intelligence | Medium |
| MIK-153 | [P1][PM-R7] AI-assisted narrative and evidence summaries with citations | M13 - Production Scale & Assisted Intelligence | Medium |
| MIK-152 | [P0][PM-R7] Data freshness and SLA monitoring | M13 - Production Scale & Assisted Intelligence | High |
| MIK-151 | [P0][PM-R7] Production readiness dashboard and runbooks | M13 - Production Scale & Assisted Intelligence | High |
| MIK-150 | [ARCH-P1][R6] Cross-service workspace boundary contract | M12 - Portfolio & Fund Narrative Workspace | Medium |
| MIK-149 | [ARCH-P1][R6] Alert rule engine contract | M12 - Portfolio & Fund Narrative Workspace | Medium |
| MIK-148 | [ARCH-P0][R6] Narrative exposure snapshot and comparison API | M12 - Portfolio & Fund Narrative Workspace | High |
| MIK-147 | [ARCH-P0][R6] Workspace entity and watchlist data model | M12 - Portfolio & Fund Narrative Workspace | High |
| MIK-146 | [P1][PM-R6] Radar-to-fund impact drill-down | M12 - Portfolio & Fund Narrative Workspace | Medium |
| MIK-145 | [P1][PM-R6] Narrative exposure change alerts | M12 - Portfolio & Fund Narrative Workspace | Medium |
| MIK-144 | [P0][PM-R6] Watchlists and saved fund sets | M12 - Portfolio & Fund Narrative Workspace | High |
| MIK-143 | [P0][PM-R6] Fund and portfolio narrative dashboard | M12 - Portfolio & Fund Narrative Workspace | High |
| MIK-142 | [ARCH-P1][R5] Narrative quality audit API and export contract | M11 - Evidence Intelligence & Narrative Quality | Medium |
| MIK-141 | [ARCH-P1][R5] Contradiction and staleness model | M11 - Evidence Intelligence & Narrative Quality | Medium |
| MIK-140 | [ARCH-P0][R5] Source lineage and reliability model | M11 - Evidence Intelligence & Narrative Quality | High |
| MIK-139 | [ARCH-P0][R5] Evidence quality schema and scoring contract | M11 - Evidence Intelligence & Narrative Quality | High |
| MIK-138 | [P1][PM-R5] Narrative quality audit workspace | M11 - Evidence Intelligence & Narrative Quality | Medium |
| MIK-137 | [P1][PM-R5] Contradiction and stale narrative detection | M11 - Evidence Intelligence & Narrative Quality | Medium |
| MIK-136 | [P0][PM-R5] Structured event extraction quality review | M11 - Evidence Intelligence & Narrative Quality | High |
| MIK-135 | [P0][PM-R5] Evidence quality scorecard | M11 - Evidence Intelligence & Narrative Quality | High |
| MIK-134 | [ARCH-R7] Architecture requirement pack for production scale and assisted intelligence | M13 - Production Scale & Assisted Intelligence | High |
| MIK-133 | [PM-R7] Product requirement pack for production scale and assisted intelligence | M13 - Production Scale & Assisted Intelligence | High |
| MIK-132 | [ARCH-R6] Architecture requirement pack for portfolio and fund narrative workspace | M12 - Portfolio & Fund Narrative Workspace | High |
| MIK-131 | [PM-R6] Product requirement pack for portfolio and fund narrative workspace | M12 - Portfolio & Fund Narrative Workspace | High |
| MIK-130 | [ARCH-R5] Architecture requirement pack for evidence intelligence and narrative quality | M11 - Evidence Intelligence & Narrative Quality | High |
| MIK-129 | [PM-R5] Product requirement pack for evidence intelligence and narrative quality | M11 - Evidence Intelligence & Narrative Quality | High |
| MIK-97 | [ARCH-P0][R4] Review and promotion workflow state machine | M10 - Productized Narrative Operations | High |
| MIK-96 | [ARCH-P1][R4] Durable store migration schema for narrative lifecycle | M10 - Productized Narrative Operations | Medium |
| MIK-95 | [ARCH-P1][R4] Scheduling job model and run ledger | M10 - Productized Narrative Operations | Medium |
| MIK-94 | [ARCH-P0][R4] Narrative Radar UI contract and frontend boundary | M10 - Productized Narrative Operations | High |
| MIK-93 | [ARCH-P0][R4] Live validation taxonomy and credential-safe diagnostics | M10 - Productized Narrative Operations | High |
| MIK-92 | [P0][PM-R4] Complete review workflow for evidence drill-down and trust promotion | M10 - Productized Narrative Operations | High |
| MIK-91 | [P1][PM-R4] Persistent database migration readiness | M10 - Productized Narrative Operations | Medium |
| MIK-90 | [P1][PM-R4] Operational scheduling for source intake and radar scoring | M10 - Productized Narrative Operations | Medium |
| MIK-89 | [P0][PM-R4] Narrative Radar UI as service product surface | M10 - Productized Narrative Operations | High |
| MIK-88 | [P0][PM-R4] Live provider credential smoke dashboard | M10 - Productized Narrative Operations | High |
| MIK-87 | [ARCH-R4] Architecture requirement pack for productized narrative operations | M10 - Productized Narrative Operations | High |
| MIK-86 | [PM-R4] Product requirement pack for productized narrative operations | M10 - Productized Narrative Operations | High |
| MIK-85 | [ARCH-P1][R3] Radar state and review integration | M9 - Narrative Radar Service | Medium |
| MIK-84 | [ARCH-P1][R3] Bubble chart data contract | M9 - Narrative Radar Service | Medium |
| MIK-83 | [ARCH-P1][R3] Market confirmation adapter boundary | M9 - Narrative Radar Service | Medium |
| MIK-82 | [ARCH-P0][R3] Radar source-signal time-series model | M9 - Narrative Radar Service | High |
| MIK-81 | [ARCH-P0][R3] Radar score schema and explainability contract | M9 - Narrative Radar Service | High |
| MIK-80 | [ARCH-P0][R3] Narrative Radar ownership and service API boundary | M9 - Narrative Radar Service | High |
| MIK-79 | [P2][PM-R3] AI narrative explanation as optional evidence summary | M9 - Narrative Radar Service | Low |
| MIK-78 | [P1][PM-R3] Narrative Radar service preview surface | M9 - Narrative Radar Service | Medium |
| MIK-77 | [P1][PM-R3] Radar drill-down from bubble to evidence and review state | M9 - Narrative Radar Service | Medium |
| MIK-76 | [P0][PM-R3] Structured source mining into candidate narratives | M9 - Narrative Radar Service | High |
| MIK-75 | [P0][PM-R3] Narrative heat and trend scoring | M9 - Narrative Radar Service | High |
| MIK-74 | [P0][PM-R3] Narrative Radar bubble data API | M9 - Narrative Radar Service | High |
| MIK-73 | [P1][PM-R3] Bubble chart client contract | M9 - Narrative Radar Service | Medium |
| MIK-72 | [P1][PM-R3] Narrative Radar source drill-down | M9 - Narrative Radar Service | Medium |
| MIK-71 | [P0][PM-R3] Narrative heat and trend scoring | M9 - Narrative Radar Service | High |
| MIK-70 | [P0][PM-R3] Narrative Radar bubble data API | M9 - Narrative Radar Service | High |
| MIK-69 | [ARCH-R3] Architecture requirement pack for Narrative Radar Service | Narrative Radar Service | High |
| MIK-68 | [PM-R3] Product requirement pack for Narrative Radar Service | Narrative Radar Service | High |
| MIK-67 | [ARCH-P1][R2] Gateway change-request protocol for new narrative sources | M6 - Narrative Source Expansion | Medium |
| MIK-66 | [ARCH-P1][R2] Governance audit schema and export contract | M8 - Durable Operations & Governance | Medium |
| MIK-65 | [ARCH-P1][R2] Fund report artifact contract | M7 - Fund Intelligence Workflows | Medium |
| MIK-64 | [ARCH-P1][R2] Durable Narrative Service storage migration path | M8 - Durable Operations & Governance | Medium |
| MIK-63 | [ARCH-P0][R2] Source event schema for news and announcements | M6 - Narrative Source Expansion | High |
| MIK-62 | [ARCH-P0][R2] Live validation probe taxonomy | M5 - Release & Live Validation | High |
| MIK-61 | [ARCH-P0][R2] Release baseline and merge protocol | M5 - Release & Live Validation | Urgent |
| MIK-60 | [ARCH-R2] Architecture requirement pack for live intelligence workflows | Live Intelligence Workflows | High |
| MIK-59 | [P1][PM-R2] Narrative governance audit export | M8 - Durable Operations & Governance | Medium |
| MIK-58 | [P1][PM-R2] Reviewable fund report pack | M7 - Fund Intelligence Workflows | Medium |
| MIK-57 | [P0][PM-R2] Fund narrative change monitor report | M7 - Fund Intelligence Workflows | High |
| MIK-56 | [P1][PM-R2] Announcement-to-evidence mapping intake | M6 - Narrative Source Expansion | Medium |
| MIK-55 | [P0][PM-R2] Structured news-to-candidate narrative intake | M6 - Narrative Source Expansion | High |
| MIK-54 | [P0][PM-R2] Live validation dashboard for gateway and Narrative Service | M5 - Release & Live Validation | High |
| MIK-53 | [P0][PM-R2] Merge accepted FNI branch and publish release baseline | M5 - Release & Live Validation | Urgent |
| MIK-52 | [PM-R2] Product requirement pack for live intelligence workflows | Live Intelligence Workflows | High |
| MIK-51 | [Defect][PM/ARCH] Fix review workspace direct CLI invocation | M2 - Reviewable Narrative Workflow | High |
| MIK-49 | [ARCH-P1] Narrative trust state machine | M3 - Trust Governance & Evidence | Medium |
| MIK-48 | [ARCH-P1] Candidate and evidence identity model | M2 - Reviewable Narrative Workflow | High |
| MIK-47 | [ARCH-P1] Observability and operational diagnostics model | M4 - Reports & Developer Handoff | Medium |
| MIK-46 | [ARCH-P1] Acceptance harness and CI gate for service contracts | M4 - Reports & Developer Handoff | Medium |
| MIK-45 | [ARCH-P0] Gateway-owned market data boundary | M1 - Can-Do Data & Service Foundation | High |
| MIK-44 | [ARCH-P0] Trusted promotion transaction boundary | M3 - Trust Governance & Evidence | High |
| MIK-43 | [ARCH-P0] Durable append-only ledger design for narrative review | M2 - Reviewable Narrative Workflow | High |
| MIK-42 | [ARCH-P0] Narrative Service API contract and versioning rules | M1 - Can-Do Data & Service Foundation | High |
| MIK-41 | [P1][PM] Developer-ready implementation handoff format | M4 - Reports & Developer Handoff | Medium |
| MIK-40 | [P1][PM] News and announcement candidate intake via gateway/service contracts | M2 - Reviewable Narrative Workflow | Medium |
| MIK-39 | [P0][PM] Trusted promotion workflow with explicit gates | M3 - Trust Governance & Evidence | High |
| MIK-38 | [P1][PM] Human review workspace MVP | M2 - Reviewable Narrative Workflow | Medium |
| MIK-37 | [P1][PM] Service-backed report source disclosure | M4 - Reports & Developer Handoff | Medium |
| MIK-36 | [P0][PM] Market data capability inventory report | M1 - Can-Do Data & Service Foundation | High |
| MIK-35 | [P0][PM] Evidence pack detail and source drill-down | M2 - Reviewable Narrative Workflow | High |
| MIK-34 | [P0][PM] Candidate narrative detail view | M2 - Reviewable Narrative Workflow | High |
| MIK-33 | [ARCH] Architecture requirement pack for FNI platform | Foundational Architecture | High |
| MIK-32 | [PM] Product requirement pack for FNI roadmap | Foundational Product | High |

## 后续清理建议

如果后续 Linear 连接器开放 issue archive/delete 工具，建议按以下顺序执行：

1. 先再次查询 `state=Done, includeArchived=false`，确认是否仍为这 157 条或有新增 Done。
2. 对已在本文件归档且不需要保留在活跃 Linear 看板的 issue 执行 archive/delete。
3. 执行后重新查询 Done 未归档数量，追加一条 cleanup verification 记录到本文件或新文件。

不要用“改状态到 Canceled/Backlog”代替删除；那会污染真实需求历史。
