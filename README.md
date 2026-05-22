# 基于 SysML 模型的文档自动生成系统

本项目是面向课程综合设计题目开发的 B/S 架构系统，用于导入 SysML/UML/XMI/JSON 模型，解析模型元素与关系，并基于模板自动生成工程文档。系统参考 OpenMBEE MMS、View Editor、Model Development Kit、DocGen 等思路，采用轻量化前后端分离实现。

## 技术栈

- 前端：Vue 3、Vite、Pinia、Element Plus、Axios
- 后端：Python、FastAPI、SQLAlchemy、Pydantic
- 数据库：MySQL 8
- 文档导出：HTML、DOCX、PDF
- 认证方式：JWT

## 主要功能

- 用户注册、登录、JWT 鉴权
- 角色权限：管理员、编辑者、只读用户
- 项目管理
- SysML/XMI/XML/JSON 模型上传与解析
- 模型元素与模型关系展示
- 模型元素说明编辑
- 文档模板管理
- 基于模型和模板自动生成文档
- HTML、DOCX、PDF 导出
- 操作日志审计

## 项目结构

```text
sysml-docgen-system
|-- backend                 # FastAPI 后端
|   |-- app
|   |   |-- api             # 接口路由
|   |   |-- core            # 配置、数据库、安全模块
|   |   |-- models          # SQLAlchemy 数据模型
|   |   |-- schemas         # Pydantic 数据结构
|   |   `-- services        # 模型解析、文档生成、日志服务
|   |-- scripts            # 数据库初始化脚本
|   |-- .env.example       # 环境变量示例
|   |-- requirements.txt   # Python 依赖
|   `-- run.py             # 后端启动入口
|-- frontend                # Vue 前端
|   |-- src
|   |   |-- api             # 接口封装
|   |   |-- router          # 路由
|   |   |-- stores          # Pinia 状态
|   |   `-- views           # 页面组件
|   |-- package.json
|   `-- vite.config.ts
|-- docs
|   |-- sample-sysml-model.json
|   `-- omg-sysml-20230201-profile.xmi
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
mysql -uroot -pmysql -e "CREATE DATABASE IF NOT EXISTS sysml_docgen DEFAULT CHARACTER SET utf8mb4 DEFAULT COLLATE utf8mb4_unicode_ci;"
```

后端启动时会根据 SQLAlchemy 模型自动创建表。

每个开发者需要在本地创建 `backend/.env`，可以参考 `backend/.env.example`：

```env
DATABASE_URL=mysql+pymysql://root:mysql@127.0.0.1:3306/sysml_docgen?charset=utf8mb4
SECRET_KEY=change-this-secret-key
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

## 默认账号

如果本地数据库已经初始化过演示数据，可以使用：

```text
用户名：admin
密码：123456
```

如果没有账号，可以在登录页注册新用户。

## 演示流程

1. 登录系统。
2. 进入项目管理，创建一个项目。
3. 进入模型管理，选择项目并上传模型文件。
4. 可以使用 `docs/sample-sysml-model.json` 做小模型测试。
5. 可以使用 `docs/omg-sysml-20230201-profile.xmi` 做标准 SysML XMI 大模型测试。
6. 查看模型解析出的元素和关系。
7. 进入模板管理，创建默认模板。
8. 进入文档生成，选择项目、模型、模板并生成文档。
9. 在线预览文档。
10. 导出 HTML、DOCX 或 PDF。

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

## 说明

本项目中的 `docs/omg-sysml-20230201-profile.xmi` 来源于 OMG 官方 SysML 规范发布文件，用于验证系统对标准 XMI 文件的解析能力。由于该模型规模较大，HTML 导出保留完整内容，DOCX/PDF 导出采用摘要和部分明细，避免生成过程过慢。
