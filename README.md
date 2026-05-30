# 基于 SysML 模型的文档自动生成系统

本项目是面向课程综合设计题目开发的 B/S 架构系统，用于导入 SysML/UML/XMI/JSON 模型，解析模型元素与关系，并基于模板自动生成工程文档。系统参考 OpenMBEE MMS、View Editor、Model Development Kit、DocGen 等思路，采用轻量化前后端分离实现。

系统核心目标是把模型数据作为文档生成的单一可信源，实现模型导入、图形化查看、轻量编辑、版本追溯、模板渲染、文档导出和权限控制的一体化流程。

## 技术栈

- 前端：Vue 3、Vite、Pinia、Element Plus、Axios
- 后端：Python、FastAPI、SQLAlchemy、Pydantic
- 数据库：MySQL 8
- 文档导出：HTML、DOCX、PDF
- 模板引擎：Jinja2
- 认证方式：JWT
- 实验适配：OpenMBEE MMS 接口适配层、Jupyter Notebook 演示

## 主要功能

### 用户与权限

- 用户注册、登录、JWT 鉴权
- 角色权限：管理员、作者、读者
- 项目成员角色：负责人、编辑者、查看者
- 管理员可管理用户、项目和成员
- 作者可创建项目、导入模型、编辑模型、管理模板、生成文档
- 读者只能查看授权项目数据，不能执行新增、编辑、删除、导入、生成、回滚等写操作
- 项目负责人不能把系统读者提升为项目编辑者或负责人

### 项目管理

- 项目创建、编辑、删除
- 项目成员添加、移除、角色调整
- 项目列表按当前登录用户权限过滤
- 项目成员权限与系统角色联动校验

### 模型管理

- SysML/XMI/XML/JSON/UML/MMS 模型上传与解析
- 模型元素和模型关系展示
- 元素层级树导航
- 元素表格筛选与分页
- 图形化关系视图
- 图布局支持环形、分层、力导向
- 图视图支持节点点击、节点拖动、画布拖动、缩放、适配视图、返回概览
- 模型元素说明轻量编辑
- 模型关系新增、编辑、删除
- 模型编辑、元素编辑、关系编辑均会生成新的模型版本

### 版本管理

- 模型分支创建、重命名、删除
- 模型标签创建
- 模型回滚到指定标签或模型版本
- 模型版本对比
- 对比结果支持 CSV 和 HTML 导出
- 模板历史版本查看与回滚
- 回滚记录查询

### 模板与文档生成

- 文档模板创建、编辑、删除
- 默认模板生成
- Jinja2 模板预览
- 基于项目、模型版本和模板生成文档
- 在线预览生成文档
- HTML、DOCX、PDF 导出
- 文档生成历史查看和删除

### OpenMBEE 与 Jupyter

- OpenMBEE MMS 配置状态查看
- OpenMBEE MMS 接口目录展示
- 配置真实 MMS 后可测试连接、获取项目、获取分支
- 支持按根元素 ID 或搜索关键词从 MMS 导入为本地模型版本
- Jupyter Notebook 演示登录、上传模型、查看元素关系、生成文档和访问 OpenMBEE 适配接口

说明：本项目没有实现完整 Cameo/MagicDraw MDK 插件，当前提供的是 Jupyter 实验台和 OpenMBEE 接口适配层，便于后续接入真实 MMS 和外部建模工具。

## 项目结构

```text
sysml-docgen-system
|-- backend
|   |-- app
|   |   |-- api             # FastAPI 接口路由
|   |   |-- core            # 配置、数据库、安全模块
|   |   |-- models          # SQLAlchemy 数据模型
|   |   |-- schemas         # Pydantic 数据结构
|   |   `-- services        # 模型解析、文档生成、OpenMBEE、日志服务
|   |-- scripts
|   |   `-- init_db.sql     # 数据库创建脚本
|   |-- .env.example        # 环境变量示例
|   |-- requirements.txt    # Python 依赖
|   `-- run.py              # 后端启动入口
|-- frontend
|   |-- src
|   |   |-- api             # 接口封装
|   |   |-- router          # 路由
|   |   |-- stores          # Pinia 登录状态和权限状态
|   |   `-- views           # 页面组件
|   |-- package.json
|   `-- vite.config.ts
|-- docs
|   |-- sample-sysml-model.json
|   |-- test.xmi
|   |-- omg-sysml-20230201-profile.xmi
|   |-- jupyter-demo.md
|   `-- openmbee-interface-adapter.md
|-- notebooks
|   `-- sysml_docgen_openmbee_demo.ipynb
|-- scripts
|   |-- start_jupyter.ps1
|   `-- start_jupyter.cmd
|-- report.md              # 验收报告
`-- README.md
```

## 环境要求

- Python 3.11 或更高版本
- Node.js 18 或更高版本
- MySQL 8
- Git

## 数据库配置

默认数据库连接：

```text
mysql+pymysql://root:mysql@127.0.0.1:3306/sysml_docgen?charset=utf8mb4
```

创建数据库：

```powershell
mysql -uroot -pmysql < .\backend\scripts\init_db.sql
```

或者：

```powershell
mysql -uroot -pmysql -e "CREATE DATABASE IF NOT EXISTS sysml_docgen DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"
```

后端启动时会根据 SQLAlchemy 模型自动创建表。

每个开发者需要在本地创建 `backend/.env`，可以参考 `backend/.env.example`：

```env
DATABASE_URL=mysql+pymysql://root:mysql@127.0.0.1:3306/sysml_docgen?charset=utf8mb4
SECRET_KEY=change-this-secret-key
ACCESS_TOKEN_EXPIRE_MINUTES=480
UPLOAD_DIR=app/uploads
GENERATED_DIR=app/generated
OPENMBEE_MMS_URL=
OPENMBEE_MMS_TOKEN=
OPENMBEE_DOC_CONVERT_URL=
```

注意：`backend/.env` 包含本地数据库账号和密钥，不应提交到 Git。

## 后端启动

```powershell
cd .\backend
pip install -r requirements.txt
$env:PYTHONPATH=(Get-Location).Path
python run.py
```

后端默认地址：

```text
http://127.0.0.1:8000
```

健康检查：

```text
http://127.0.0.1:8000/health
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 前端启动

```powershell
cd .\frontend
npm install
npm run dev
```

前端默认地址：

```text
http://127.0.0.1:5173
```

生产构建检查：

```powershell
npm run build
```

## 默认账号

如果本地数据库已经初始化过演示数据，可以使用：

```text
用户名：admin
密码：123456
```

如果没有账号，可以在登录页注册新用户。注册时可选择管理员、作者、读者角色；验收时建议使用管理员账号创建项目和演示数据，再注册读者账号验证只读权限。

## 演示流程

1. 登录系统。
2. 进入“项目管理”，创建一个项目。
3. 可在项目成员中添加作者或读者用户，验证成员权限。
4. 进入“模型管理”，选择项目并上传模型文件。
5. 推荐使用 `docs/sample-sysml-model.json` 做小模型测试。
6. 可使用 `docs/test.xmi` 或 `docs/omg-sysml-20230201-profile.xmi` 做 XMI 解析测试。
7. 点击模型列表中的模型，查看元素表格、层级树和图形化关系视图。
8. 在图视图中切换布局，测试节点点击、节点拖动、画布拖动、缩放和适配。
9. 编辑模型说明、元素说明或关系，验证系统生成新的模型版本。
10. 使用模型版本对比查看新增、删除、变更元素和关系差异。
11. 创建模型分支和标签，执行版本回滚，查看回滚记录。
12. 进入“模板管理”，创建默认模板或自定义模板。
13. 预览模板并保存，查看模板历史版本。
14. 进入“文档生成”，选择项目、模型版本、模板并生成文档。
15. 在线预览文档，并导出 HTML、DOCX 或 PDF。
16. 使用读者账号登录，确认只能查看和导出，不能执行写操作。

## OpenMBEE MMS 适配

当前系统提供轻量级 OpenMBEE MMS 接口适配层。入口位于：

```text
模型管理 -> 模型导入来源 -> OpenMBEE MMS
```

未配置真实 MMS 时，系统仍可展示接口目录。配置真实 MMS 后，可使用测试连接、获取项目、获取分支和导入模型功能。

配置项位于 `backend/.env`：

```env
OPENMBEE_MMS_URL=http://127.0.0.1:8080
OPENMBEE_MMS_TOKEN=
OPENMBEE_DOC_CONVERT_URL=http://127.0.0.1:8080
```

本系统暴露的适配接口包括：

```text
GET  /api/openmbee/config
GET  /api/openmbee/mms/endpoints
GET  /api/openmbee/mms/version
GET  /api/openmbee/mms/projects
GET  /api/openmbee/mms/projects/{project_id}/refs
GET  /api/openmbee/mms/projects/{project_id}/refs/{ref_id}/elements/{element_id}
GET  /api/openmbee/mms/projects/{project_id}/refs/{ref_id}/search
POST /api/openmbee/mms/import
```

## Jupyter 实验台

项目提供 Notebook 演示环境，用于从脚本侧调用系统接口。

在项目根目录执行：

```powershell
.\scripts\start_jupyter.ps1
```

打开：

```text
http://127.0.0.1:8888/lab/tree/notebooks/sysml_docgen_openmbee_demo.ipynb
```

Notebook 使用相对路径访问当前项目下的 `docs/sample-sysml-model.json`，演示内容包括：

- 调用 `/health` 验证后端运行状态
- 登录系统接口
- 读取项目、模型、模板、文档数据
- 展示 OpenMBEE 适配接口目录
- 上传示例模型
- 查看模型元素和关系
- 使用模板生成文档

## 重要文件

- `report.md`：验收报告和完整演示步骤。
- `docs/sample-sysml-model.json`：推荐验收用小模型。
- `docs/test.xmi`：XMI 测试模型。
- `docs/omg-sysml-20230201-profile.xmi`：标准 SysML 大模型测试。
- `docs/jupyter-demo.md`：Jupyter 演示说明。
- `docs/openmbee-interface-adapter.md`：OpenMBEE 适配说明。

## Git 协作建议

团队开发不建议直接推送到 `main` 分支。推荐流程：

```powershell
git checkout main
git pull
git checkout -b feature/your-feature-name
```

开发完成后：

```powershell
git add .
git commit -m "Describe your change"
git push -u origin feature/your-feature-name
```

然后在 GitHub 创建 Pull Request，代码检查后再合并到 `main`。

常见分支命名：

```text
feature/model-upload
feature/document-template
feature/user-permission
fix/export-download
docs/readme
```

## 不应提交的文件

以下文件或目录已通过 `.gitignore` 排除：

```text
frontend/node_modules/
frontend/dist/
logs/
.chrome-profile/
.chrome-demo-profile/
backend/.env
backend/app/uploads/
backend/app/generated/
__pycache__/
```